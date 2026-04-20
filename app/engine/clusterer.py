"""Dynamic folder-name clustering via rapidfuzz + single-linkage union-find.

Algorithmically equivalent to PolyFuzz's RapidFuzz grouping mode, without the
transformer dependency. Pure rapidfuzz + pure-Python union-find.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from rapidfuzz import fuzz

from app.config import SIMILARITY_THRESHOLD


_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


@dataclass
class Cluster:
    id: int
    label: str
    members: list[str]
    file_count: int
    avg_internal_similarity: float = 0.0


def normalize(name: str) -> str:
    return _NORMALIZE_RE.sub(" ", name.lower()).strip()


class _UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, i: int) -> int:
        root = i
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[i] != root:
            self.parent[i], i = root, self.parent[i]
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1


def _pick_label(
    members: list[str], similarity: dict[tuple[int, int], float]
) -> tuple[str, float]:
    """Pick the medoid member (highest mean similarity to peers).

    Ties break on the shorter, alphabetically-first string. Returns
    (label, average_internal_similarity).
    """
    if len(members) == 1:
        return members[0], 100.0

    def mean_to_peers(i: int) -> float:
        total = 0.0
        n = 0
        for j in range(len(members)):
            if i == j:
                continue
            key = (min(i, j), max(i, j))
            total += similarity.get(key, 0.0)
            n += 1
        return total / n if n else 0.0

    scores = [(mean_to_peers(i), -len(members[i]), members[i]) for i in range(len(members))]
    scores.sort(reverse=True)
    top_score = scores[0][0]
    return scores[0][2], top_score


def cluster_folders(
    folder_counts: Iterable[tuple[str, int]],
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[Cluster]:
    """Cluster unique folder names by pairwise token_sort_ratio ≥ threshold.

    Input: iterable of (folder_name, file_count) pairs.
    Output: list[Cluster] sorted by descending file_count then label.
    """
    counts: dict[str, int] = {}
    for folder, count in folder_counts:
        counts[folder] = counts.get(folder, 0) + count

    folders = list(counts.keys())
    n = len(folders)
    if n == 0:
        return []

    normalized = [normalize(f) for f in folders]
    uf = _UnionFind(n)
    sim: dict[tuple[int, int], float] = {}

    for i in range(n):
        for j in range(i + 1, n):
            a, b = normalized[i], normalized[j]
            if not a or not b:
                score = 0.0
            else:
                score = float(fuzz.token_sort_ratio(a, b))
            sim[(i, j)] = score
            if score >= threshold:
                uf.union(i, j)

    groups: dict[int, list[int]] = {}
    for idx in range(n):
        groups.setdefault(uf.find(idx), []).append(idx)

    clusters: list[Cluster] = []
    for cluster_id, (_root, indices) in enumerate(sorted(groups.items()), start=1):
        members = [folders[i] for i in indices]
        local_sim: dict[tuple[int, int], float] = {}
        for local_a, global_a in enumerate(indices):
            for local_b, global_b in enumerate(indices):
                if local_a >= local_b:
                    continue
                key_global = (min(global_a, global_b), max(global_a, global_b))
                local_sim[(local_a, local_b)] = sim.get(key_global, 0.0)
        label, avg_sim = _pick_label(members, local_sim)
        total_files = sum(counts[m] for m in members)
        clusters.append(
            Cluster(
                id=cluster_id,
                label=label,
                members=sorted(members, key=str.lower),
                file_count=total_files,
                avg_internal_similarity=round(avg_sim, 2),
            )
        )

    clusters.sort(key=lambda c: (-c.file_count, c.label.lower()))
    for new_id, cluster in enumerate(clusters, start=1):
        cluster.id = new_id
    return clusters


def recluster(
    folder_counts: Iterable[tuple[str, int]], threshold: float
) -> list[Cluster]:
    """Public re-cluster helper (alias kept for readability at the call site)."""
    return cluster_folders(folder_counts, threshold=threshold)


def merge_clusters(
    clusters: list[Cluster], ids_to_merge: list[int], new_label: str | None = None
) -> list[Cluster]:
    """Merge clusters by id. Label defaults to the first cluster's label."""
    if len(ids_to_merge) < 2:
        return list(clusters)
    targets = [c for c in clusters if c.id in ids_to_merge]
    if len(targets) < 2:
        return list(clusters)
    survivors = [c for c in clusters if c.id not in ids_to_merge]
    merged_members: list[str] = []
    for c in targets:
        merged_members.extend(c.members)
    merged = Cluster(
        id=min(ids_to_merge),
        label=new_label or targets[0].label,
        members=sorted(set(merged_members), key=str.lower),
        file_count=sum(c.file_count for c in targets),
        avg_internal_similarity=0.0,
    )
    survivors.append(merged)
    survivors.sort(key=lambda c: (-c.file_count, c.label.lower()))
    for new_id, cluster in enumerate(survivors, start=1):
        cluster.id = new_id
    return survivors
