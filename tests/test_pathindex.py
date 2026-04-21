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


def test_time_split_routing():
    item = _item(("Marriage-001", "HALDI&SANGEETH"))
    haldi_window = TimeSplit(
        start=None,
        end=datetime(2024, 6, 1, 14, 0, 0),
        destination_label="Haldi",
    )
    sangeet_window = TimeSplit(
        start=datetime(2024, 6, 1, 14, 0, 0),
        end=None,
        destination_label="Sangeet",
    )
    pick = FolderPick(
        name="HALDI&SANGEETH",
        destination_label="HS_Default",
        time_splits=[haldi_window, sangeet_window],
    )
    picks = {"HALDI&SANGEETH": pick}

    morning = datetime(2024, 6, 1, 10, 0, 0)
    evening = datetime(2024, 6, 1, 20, 0, 0)
    assert route_file(item, picks, morning) == "Haldi"
    assert route_file(item, picks, evening) == "Sangeet"

    # A timestamp outside every window falls back to the pick's default.
    # (Here both windows together cover all time, so construct a bounded case.)
    bounded = FolderPick(
        name="HALDI&SANGEETH",
        destination_label="HS_Default",
        time_splits=[
            TimeSplit(
                start=datetime(2024, 6, 1, 8, 0, 0),
                end=datetime(2024, 6, 1, 12, 0, 0),
                destination_label="Haldi",
            )
        ],
    )
    assert route_file(item, {"HALDI&SANGEETH": bounded}, evening) == "HS_Default"
