"""locations 模块测试。"""

from __future__ import annotations

import json

import pytest

from src.locations import list_location_names, load_locations, resolve_location, save_location


def test_resolve_exact_name(sample_locations: list) -> None:
    loc = resolve_location("黄山", sample_locations)
    assert loc is not None
    assert loc["name"] == "黄山"


def test_resolve_fuzzy_substring(sample_locations: list) -> None:
    loc = resolve_location("峨眉", sample_locations)
    assert loc is not None
    assert "峨眉" in loc["name"]


def test_resolve_unknown_returns_none(sample_locations: list) -> None:
    assert resolve_location("长城", sample_locations) is None


def test_list_location_names(sample_locations: list) -> None:
    names = list_location_names(sample_locations)
    assert "黄山" in names
    assert len(names) == len(sample_locations)


def test_load_locations_rejects_missing_field(tmp_path) -> None:
    config_path = tmp_path / "locations.json"
    config_path.write_text(
        json.dumps([{"name": "测试山", "lat": 30.0, "lon": 120.0}], ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="elevation"):
        load_locations(config_path)


def test_save_location_appends_to_file(tmp_path) -> None:
    config_path = tmp_path / "locations.json"
    config_path.write_text(
        json.dumps([{"name": "黄山", "lat": 30.13, "lon": 118.17, "elevation": 1864}], ensure_ascii=False),
        encoding="utf-8",
    )
    save_location(
        {"name": "武功山", "lat": 27.46, "lon": 114.19, "elevation": 1918},
        config_path=config_path,
    )
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert len(data) == 2
    assert data[1]["name"] == "武功山"


def test_save_location_skips_duplicate(tmp_path) -> None:
    config_path = tmp_path / "locations.json"
    config_path.write_text(
        json.dumps([{"name": "黄山", "lat": 30.13, "lon": 118.17, "elevation": 1864}], ensure_ascii=False),
        encoding="utf-8",
    )
    save_location(
        {"name": "黄山", "lat": 30.13, "lon": 118.17, "elevation": 1864},
        config_path=config_path,
    )
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert len(data) == 1


def test_load_locations_rejects_invalid_latitude(tmp_path) -> None:
    config_path = tmp_path / "locations.json"
    config_path.write_text(
        json.dumps(
            [{"name": "测试山", "lat": 100.0, "lon": 120.0, "elevation": 1000}],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="lat"):
        load_locations(config_path)
