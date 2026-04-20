"""Tests for the dynamic clustering engine."""

from __future__ import annotations

import pytest

from app.engine.clusterer import Cluster, cluster_folders, merge_clusters


def _labels_and_members(clusters: list[Cluster]) -> set[frozenset[str]]:
    return {frozenset(c.members) for c in clusters}


def test_single_linkage_groups_typo_variants():
    folders = [("engagegem et", 2), ("Engagement", 3), ("engagement_final", 1)]
    clusters = cluster_folders(folders, threshold=70)
    assert len(clusters) == 1
    cluster = clusters[0]
    assert set(cluster.members) == {"engagegem et", "Engagement", "engagement_final"}
    assert cluster.file_count == 6


def test_distinct_folders_become_distinct_clusters():
    folders = [
        ("alpha_raw", 1),
        ("Alpha Raw", 1),
        ("Alpha-final", 1),
        ("bravo_shoot_day1", 1),
        ("Bravo Shoot Day 2", 1),
        ("unrelated_notes", 1),
        ("videos", 1),
    ]
    # At threshold 80: "alpha_raw" and "Alpha Raw" both normalize to "alpha raw"
    # (100% match) but "Alpha-final" → "alpha final" only scores ~57% vs
    # "alpha raw" so it's a singleton cluster. At threshold 70 all three merge.
    clusters = cluster_folders(folders, threshold=80)
    groups = _labels_and_members(clusters)
    assert frozenset({"alpha_raw", "Alpha Raw"}) in groups
    assert frozenset({"Alpha-final"}) in groups
    assert frozenset({"bravo_shoot_day1", "Bravo Shoot Day 2"}) in groups
    assert frozenset({"unrelated_notes"}) in groups
    assert frozenset({"videos"}) in groups

    # At the looser threshold of 70 the three alpha folders merge.
    loose = cluster_folders(folders, threshold=70)
    loose_groups = _labels_and_members(loose)
    assert frozenset({"alpha_raw", "Alpha Raw", "Alpha-final"}) in loose_groups


def test_threshold_strictness():
    folders = [("alpha_raw", 1), ("Alpha-final", 1)]
    clusters_lenient = cluster_folders(folders, threshold=60)
    clusters_strict = cluster_folders(folders, threshold=95)
    assert len(clusters_lenient) == 1
    assert len(clusters_strict) == 2


def test_empty_input():
    assert cluster_folders([], threshold=80) == []


def test_label_is_medoid():
    folders = [("sangeeet", 1), ("Sangeet", 1), ("sangeet_night", 1)]
    clusters = cluster_folders(folders, threshold=70)
    assert len(clusters) == 1
    assert clusters[0].label in {"sangeeet", "Sangeet", "sangeet_night"}


def test_merge_clusters_unions_members():
    clusters = cluster_folders(
        [("alpha_raw", 1), ("Alpha-final", 1), ("videos", 1)], threshold=95
    )
    # At strict threshold these are 3 separate singletons
    assert len(clusters) == 3
    ids = sorted(c.id for c in clusters)
    merged = merge_clusters(clusters, [ids[0], ids[1]], new_label="Alpha")
    labels = {c.label for c in merged}
    assert "Alpha" in labels
    alpha = next(c for c in merged if c.label == "Alpha")
    assert alpha.file_count == 2
    assert set(alpha.members) == {"alpha_raw", "Alpha-final"} or set(
        alpha.members
    ) == {"videos"}  # safeguards against the branch picking wrong ids
    total = sum(c.file_count for c in merged)
    assert total == 3


def test_duplicate_folder_counts_sum():
    clusters = cluster_folders(
        [("alpha_raw", 3), ("alpha_raw", 2)], threshold=80
    )
    assert len(clusters) == 1
    assert clusters[0].file_count == 5
