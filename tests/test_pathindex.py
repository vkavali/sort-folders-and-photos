"""Tests for the folder picker (pathindex) module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.engine.pathindex import (
    FolderPick,
    TimeSplit,
    build_folder_index,
    route_file,
)
from app.engine.scanner import MediaItem


def _item(ancestors: tuple[str, ...], name: str = "f.jpg") -> MediaItem:
    # Path doesn't need to exist for pathindex logic.
    return MediaItem(
        source_path=Path("/".join(("", *ancestors, name))),
        ancestors=ancestors,
        size_bytes=1234,
    )


def test_folder_index_counts_all_depths():
    items = [
        _item(("Marriage-001", "Marriage", "HALDI&SANGEETH", "PICS"), "a.jpg"),
        _item(("Marriage-002", "Marriage", "HALDI&SANGEETH", "PICS"), "b.jpg"),
        _item(("Marriage-001", "Marriage", "Marriage Selected"), "c.jpg"),
    ]
    entries = {e.name: e for e in build_folder_index(items)}
    # Every ancestor depth is represented.
    assert {"Marriage-001", "Marriage-002", "Marriage", "HALDI&SANGEETH", "PICS",
            "Marriage Selected"} <= set(entries.keys())

    # File counts reflect distinct descendants, not repeated counting per depth.
    assert entries["HALDI&SANGEETH"].file_count == 2
    assert entries["PICS"].file_count == 2
    assert entries["Marriage Selected"].file_count == 1
    assert entries["Marriage"].file_count == 3
    # Occurrences = # of distinct ancestor prefixes the name appears in.
    assert entries["Marriage"].occurrences == 2
    assert entries["HALDI&SANGEETH"].occurrences == 2
    assert entries["Marriage Selected"].occurrences == 1


def test_auto_suggested_heuristic():
    items = [
        _item(("Marriage-20260111T075732Z-3-001", "Marriage", "HALDI&SANGEETH",
               "PICS"), "a.jpg"),
    ]
    entries = {e.name: e for e in build_folder_index(items)}
    # Timestamped export name → untick
    assert entries["Marriage-20260111T075732Z-3-001"].auto_suggested is False
    # Generic container → untick
    assert entries["PICS"].auto_suggested is False
    # Meaningful name → tick
    assert entries["HALDI&SANGEETH"].auto_suggested is True
    assert entries["Marriage"].auto_suggested is True


def test_route_file_picks_deepest_match():
    item = _item(("Marriage-001", "Marriage", "HALDI&SANGEETH", "PICS"))
    picks = {
        "Marriage": FolderPick(name="Marriage", destination_label="Wedding"),
        "HALDI&SANGEETH": FolderPick(
            name="HALDI&SANGEETH", destination_label="Haldi_Sangeet"
        ),
    }
    # HALDI&SANGEETH is deeper than Marriage → it wins.
    assert route_file(item, picks, None) == "Haldi_Sangeet"


def test_route_file_falls_through_when_deepest_not_picked():
    item = _item(("Marriage-001", "Marriage", "HALDI&SANGEETH", "PICS"))
    picks = {
        "Marriage": FolderPick(name="Marriage", destination_label="Wedding"),
    }
    # Only Marriage is ticked → falls back to it.
    assert route_file(item, picks, None) == "Wedding"


def test_route_file_no_match_returns_empty():
    item = _item(("Marriage-001", "Marriage", "HALDI&SANGEETH", "PICS"))
    picks = {
        "unrelated": FolderPick(name="unrelated", destination_label="Other"),
    }
    assert route_file(item, picks, None) == ""


def test_global_time_split_overrides_folder_label():
    # Two different ticked folders under different parents.
    item_a = _item(("Marriage-001", "HALDI&SANGEETH"), "a.jpg")
    item_b = _item(("Marriage-002", "Marriage Selected"), "b.jpg")

    picks = {
        "HALDI&SANGEETH": FolderPick(
            name="HALDI&SANGEETH", destination_label="HS_Default"
        ),
        "Marriage Selected": FolderPick(
            name="Marriage Selected", destination_label="Wedding_Default"
        ),
    }

    # Global time windows: morning=Haldi, evening=Sangeet.
    haldi = TimeSplit(
        start=None,
        end=datetime(2024, 6, 1, 14, 0, 0),
        destination_label="Haldi",
    )
    sangeet = TimeSplit(
        start=datetime(2024, 6, 1, 14, 0, 0),
        end=None,
        destination_label="Sangeet",
    )

    morning = datetime(2024, 6, 1, 10, 0, 0)
    evening = datetime(2024, 6, 1, 20, 0, 0)

    # Files captured in the morning — from EITHER folder — go to Haldi.
    assert route_file(item_a, picks, morning, [haldi, sangeet]) == "Haldi"
    assert route_file(item_b, picks, morning, [haldi, sangeet]) == "Haldi"
    # Evening files go to Sangeet regardless of source folder.
    assert route_file(item_a, picks, evening, [haldi, sangeet]) == "Sangeet"
    assert route_file(item_b, picks, evening, [haldi, sangeet]) == "Sangeet"


def test_time_split_falls_back_to_folder_when_no_window_matches():
    item = _item(("Marriage-001", "HALDI&SANGEETH"))
    picks = {
        "HALDI&SANGEETH": FolderPick(
            name="HALDI&SANGEETH", destination_label="HS_Default"
        ),
    }
    bounded = TimeSplit(
        start=datetime(2024, 6, 1, 8, 0, 0),
        end=datetime(2024, 6, 1, 12, 0, 0),
        destination_label="Haldi",
    )
    morning = datetime(2024, 6, 1, 10, 0, 0)
    evening = datetime(2024, 6, 1, 20, 0, 0)
    assert route_file(item, picks, morning, [bounded]) == "Haldi"
    # Outside the window → fall back to the folder's default.
    assert route_file(item, picks, evening, [bounded]) == "HS_Default"


def test_time_split_does_not_capture_unpicked_files():
    """A file whose ancestor is NOT ticked should stay Unsorted even if its
    timestamp matches a global time window."""
    item = _item(("totally_unrelated",), "u.jpg")
    picks: dict[str, FolderPick] = {}
    window = TimeSplit(start=None, end=None, destination_label="Haldi")
    morning = datetime(2024, 6, 1, 10, 0, 0)
    # No picks → route_file returns "" which the planner turns into Unsorted.
    assert route_file(item, picks, morning, [window]) == ""
