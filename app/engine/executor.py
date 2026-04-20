"""Copy-then-verify-then-delete execution of a planned move list.

Supports both Flatten mode (PlannedMove.category == "") and Dynamic Grouping
mode (category is a cluster label). Uses a size-prefilter: files with
unique sizes skip hashing on the first pass and only hash if a size-peer
appears at reservation time.
"""

from __future__ import annotations

import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from app.config import DUPLICATES_DIR
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
    """Thread-safe unique-filename + hash-dedup registry.

    The ledger serves two purposes:
      1. Guarantee each destination filename is reserved atomically across
         threads so two concurrent workers cannot settle on the same name.
      2. Dedupe by digest within a destination folder: if a file with an
         identical tagged digest was already placed there, the second caller
         is told where the first landed.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hashes: dict[tuple[Path, str], Path] = {}
        self._names: dict[Path, set[str]] = {}

    def reserve(
        self,
        category_dir: Path,
        base_name: str,
        digest: str,
    ) -> tuple[str, Optional[Path]]:
        with self._lock:
            dedup_key = (category_dir, digest)
            existing = self._hashes.get(dedup_key)
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
            self._hashes[dedup_key] = final_path
            return candidate, None

    @staticmethod
    def _refresh_existing(category_dir: Path, names: set[str]) -> None:
        if not category_dir.exists():
            return
        try:
            for entry in os.scandir(category_dir):
                if entry.is_file(follow_symlinks=False):
                    names.add(entry.name)
        except (PermissionError, FileNotFoundError, OSError):
            pass


def _is_cancelled(cancel_cb: Optional[Callable[[], bool]]) -> bool:
    return cancel_cb is not None and cancel_cb()


def _build_basename(plan: PlannedMove) -> str:
    stamp = extract_timestamp(plan.item.source_path)
    return f"{format_timestamp(stamp)}_{plan.item.source_path.name}"


def _resolve_category_dir(destination_root: Path, category: str) -> Path:
    if not category:
        return destination_root
    return destination_root / category


def _process_one(
    plan: PlannedMove,
    destination_root: Path,
    ledger: _ReservationLedger,
    size_peers: set[int],
    log: LogCb,
) -> PlannedMove:
    try:
        category_dir = _resolve_category_dir(destination_root, plan.category)
        category_dir.mkdir(parents=True, exist_ok=True)

        size = plan.item.size_bytes
        if size in size_peers:
            digest = file_digest(plan.item.source_path)
        else:
            digest = f"size-unique:{size}:{plan.item.source_path}"
        plan.hash_digest = digest

        base_name = _build_basename(plan)
        final_name, dup_of = ledger.reserve(category_dir, base_name, digest)

        if dup_of is not None:
            dup_dir = destination_root / DUPLICATES_DIR
            if plan.category:
                dup_dir = dup_dir / plan.category
            dup_dir.mkdir(parents=True, exist_ok=True)
            dup_final, _ = ledger.reserve(
                dup_dir, base_name, f"dup:{digest}:{plan.item.source_path}"
            )
            dup_target = dup_dir / dup_final
            shutil.copy2(plan.item.source_path, dup_target)
            _verify_and_remove(plan.item.source_path, dup_target, digest, size)
            plan.dest_filename = dup_final
            plan.dest_path = dup_target
            plan.status = "duplicate"
            plan.message = f"Exact duplicate of {dup_of.name}; isolated to Duplicates/"
            log(f"[DUPLICATE] {plan.item.source_path} -> {dup_target}")
            return plan

        target = category_dir / final_name
        shutil.copy2(plan.item.source_path, target)
        _verify_and_remove(plan.item.source_path, target, digest, size)
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
    except Exception as exc:
        plan.status = "error"
        plan.message = f"{type(exc).__name__}: {exc}"
        log(f"[ERROR]     {plan.item.source_path}: {plan.message}")
    return plan


def _verify_and_remove(
    source: Path, target: Path, expected_digest: str, source_size: int
) -> None:
    """Verify target integrity, then delete source FILE only.

    We intentionally never delete source directories — even if empty. Empty
    folders are left in place until the user inspects the run; this matches
    the "copy-then-move with human-verifiable side effects" invariant.
    """
    if expected_digest.startswith("size-unique:"):
        try:
            if target.stat().st_size != source_size:
                target.unlink(missing_ok=True)
                raise IOError(
                    f"Size verification failed for {target}: "
                    f"expected {source_size} bytes"
                )
        except FileNotFoundError:
            raise IOError(f"Verification failed: target vanished ({target})")
    else:
        actual = file_digest(target)
        if actual != expected_digest:
            target.unlink(missing_ok=True)
            raise IOError(
                f"Hash verification failed for {target}: "
                f"expected {expected_digest}, got {actual}"
            )

    try:
        os.remove(source)
    except OSError:
        pass


def _build_size_peer_set(plan: list[PlannedMove]) -> set[int]:
    """Return the set of file sizes that appear on ≥ 2 items.

    Files with unique sizes are mathematically guaranteed not to be
    duplicates of any other file in the batch and can skip the hash step
    (we still verify the copy by size).
    """
    sizes: dict[int, int] = {}
    for p in plan:
        sizes[p.item.size_bytes] = sizes.get(p.item.size_bytes, 0) + 1
    return {sz for sz, n in sizes.items() if n >= 2}


def execute_plan(
    plan: list[PlannedMove],
    destination_root: Path,
    *,
    max_workers: int | None = None,
    file_done_cb: FileDoneCb | None = None,
    log_cb: LogCb | None = None,
    cancel_cb: Optional[Callable[[], bool]] = None,
) -> ExecutionStats:
    stats = ExecutionStats(total=len(plan))
    destination_root.mkdir(parents=True, exist_ok=True)

    ledger = _ReservationLedger()
    log = log_cb or (lambda _m: None)
    emit_done = file_done_cb or (lambda _p: None)
    size_peers = _build_size_peer_set(plan)

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
            fut = pool.submit(
                _process_one, p, destination_root, ledger, size_peers, log
            )
            futures[fut] = p

        for fut in as_completed(futures):
            p = futures[fut]
            try:
                result = fut.result()
            except Exception as exc:
                p.status = "error"
                p.message = f"{type(exc).__name__}: {exc}"
                result = p
            if _is_cancelled(cancel_cb) and result.status == "pending":
                result.status = "skipped"
                result.message = "Cancelled mid-run"
            stats.record(result.status)
            emit_done(result)

    return stats
