"""Copy-then-verify-then-delete execution of a planned move list."""

from __future__ import annotations

import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from app.categories import DUPLICATES_DIR
from app.engine.exif import extract_timestamp, format_timestamp
from app.engine.hasher import file_digest
from app.engine.planner import PlannedMove


FileDoneCb = Callable[[PlannedMove], None]
LogCb = Callable[[str], None]


@dataclass
class ExecutionStats:
    total: int = 0
    moved: int = 0
    duplicates: int = 0
    collisions_renamed: int = 0
    errors: int = 0
    skipped: int = 0

    def record(self, status: str) -> None:
        if status == "moved":
            self.moved += 1
        elif status == "duplicate":
            self.duplicates += 1
        elif status == "collision_renamed":
            self.collisions_renamed += 1
            self.moved += 1
        elif status == "error":
            self.errors += 1
        elif status == "skipped":
            self.skipped += 1


class _ReservationLedger:
    """Thread-safe registry of filenames + hashes already assigned per category.

    Needed because multiple workers may resolve collisions for files that map
    to the same destination folder concurrently. Each entry reserves a final
    filename atomically so two threads can never settle on the same name.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hashes: dict[str, Path] = {}
        self._names: dict[Path, set[str]] = {}

    def reserve(
        self,
        category_dir: Path,
        base_name: str,
        digest: str,
    ) -> tuple[str, Optional[Path]]:
        """Claim a unique destination filename for a (category, base_name).

        Returns:
          (final_name, duplicate_of_path)
        If duplicate_of_path is not None, the caller should treat this file
        as a duplicate of that existing destination and skip the copy.
        """
        with self._lock:
            existing = self._hashes.get(digest)
            if existing is not None:
                return base_name, existing

            names = self._names.setdefault(category_dir, set())
            self._refresh_existing(category_dir, names)

            candidate = base_name
            if candidate in names or (category_dir / candidate).exists():
                stem, ext = os.path.splitext(base_name)
                i = 1
                while True:
                    candidate = f"{stem}_{i}{ext}"
                    if candidate not in names and not (category_dir / candidate).exists():
                        break
                    i += 1
            names.add(candidate)
            final_path = category_dir / candidate
            self._hashes[digest] = final_path
            return candidate, None

    @staticmethod
    def _refresh_existing(category_dir: Path, names: set[str]) -> None:
        if not category_dir.exists():
            return
        try:
            for entry in os.scandir(category_dir):
                if entry.is_file(follow_symlinks=False):
                    names.add(entry.name)
        except (PermissionError, FileNotFoundError):
            pass


def _is_cancelled(cancel_cb: Optional[Callable[[], bool]]) -> bool:
    return cancel_cb is not None and cancel_cb()


def _build_basename(plan: PlannedMove) -> str:
    stamp = extract_timestamp(plan.item.source_path)
    return f"{format_timestamp(stamp)}_{plan.item.source_path.name}"


def _process_one(
    plan: PlannedMove,
    destination_root: Path,
    ledger: _ReservationLedger,
    log: LogCb,
) -> PlannedMove:
    try:
        digest = file_digest(plan.item.source_path)
        plan.hash_digest = digest

        category_dir = destination_root / plan.category
        category_dir.mkdir(parents=True, exist_ok=True)

        base_name = _build_basename(plan)
        final_name, dup_of = ledger.reserve(category_dir, base_name, digest)

        if dup_of is not None:
            dup_dir = destination_root / DUPLICATES_DIR / plan.category
            dup_dir.mkdir(parents=True, exist_ok=True)
            dup_final, _ = ledger.reserve(
                dup_dir, base_name, f"dup:{digest}:{plan.item.source_path}"
            )
            dup_target = dup_dir / dup_final
            shutil.copy2(plan.item.source_path, dup_target)
            _verify_and_remove(plan.item.source_path, dup_target, digest)
            plan.dest_filename = dup_final
            plan.dest_path = dup_target
            plan.status = "duplicate"
            plan.message = f"Exact duplicate of {dup_of.name}; isolated to Duplicates/"
            log(f"[DUPLICATE] {plan.item.source_path} -> {dup_target}")
            return plan

        target = category_dir / final_name
        shutil.copy2(plan.item.source_path, target)
        _verify_and_remove(plan.item.source_path, target, digest)
        plan.dest_filename = final_name
        plan.dest_path = target
        if final_name != base_name:
            plan.status = "collision_renamed"
            plan.message = f"Name collided; renamed to {final_name}"
            log(f"[RENAMED]   {plan.item.source_path} -> {target}")
        else:
            plan.status = "moved"
            plan.message = "Moved successfully"
            log(f"[MOVED]     {plan.item.source_path} -> {target}")
    except Exception as exc:  # pragma: no cover - defensive
        plan.status = "error"
        plan.message = f"{type(exc).__name__}: {exc}"
        log(f"[ERROR]     {plan.item.source_path}: {plan.message}")
    return plan


def _verify_and_remove(source: Path, target: Path, expected_digest: str) -> None:
    actual = file_digest(target)
    if actual != expected_digest:
        try:
            target.unlink(missing_ok=True)
        finally:
            raise IOError(
                f"Verification failed for {target}: "
                f"expected {expected_digest}, got {actual}"
            )
    try:
        os.remove(source)
    except OSError:
        pass


def execute_plan(
    plan: list[PlannedMove],
    destination_root: Path,
    *,
    max_workers: int | None = None,
    file_done_cb: FileDoneCb | None = None,
    log_cb: LogCb | None = None,
    cancel_cb: Optional[Callable[[], bool]] = None,
) -> ExecutionStats:
    """Execute the plan. Returns aggregate stats. Thread-safe & cancellable."""
    stats = ExecutionStats(total=len(plan))
    destination_root.mkdir(parents=True, exist_ok=True)

    ledger = _ReservationLedger()
    log = log_cb or (lambda _m: None)
    emit_done = file_done_cb or (lambda _p: None)

    if max_workers is None:
        cpu = os.cpu_count() or 2
        max_workers = min(8, max(2, cpu * 2))

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {}
        for p in plan:
            if _is_cancelled(cancel_cb):
                p.status = "skipped"
                p.message = "Cancelled before start"
                stats.record(p.status)
                emit_done(p)
                continue
            fut = pool.submit(_process_one, p, destination_root, ledger, log)
            futures[fut] = p

        for fut in as_completed(futures):
            p = futures[fut]
            if _is_cancelled(cancel_cb) and p.status == "pending":
                p.status = "skipped"
                p.message = "Cancelled mid-run"
            try:
                result = fut.result()
            except Exception as exc:  # pragma: no cover
                p.status = "error"
                p.message = f"{type(exc).__name__}: {exc}"
                result = p
            stats.record(result.status)
            emit_done(result)

    return stats
