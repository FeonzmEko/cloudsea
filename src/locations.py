"""景区配置加载与名称模糊匹配。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "locations.json"

# 运行时动态注册的景区（如通过高德 geocoding 临时解析得到），按名称存储。
_DYNAMIC_LOCATIONS: dict[str, dict[str, Any]] = {}


def register_location(location: dict[str, Any]) -> dict[str, Any]:
    """在运行时注册一个景区，使其可被 resolve_location 解析。

    Args:
        location: 含 name、lat、lon、elevation 的景区字典。

    Returns:
        校验并存储后的景区字典。
    """
    validated = _validate_location_entry(location, 0, _CONFIG_PATH)
    _DYNAMIC_LOCATIONS[validated["name"]] = validated
    return validated


def clear_dynamic_locations() -> None:
    """清空运行时注册的景区（主要用于测试）。"""
    _DYNAMIC_LOCATIONS.clear()


def save_location(
    location: dict[str, Any], config_path: Path | None = None,
) -> dict[str, Any]:
    """将景区持久化到 locations.json，已存在同名则跳过。

    Args:
        location: 含 name、lat、lon、elevation 的景区字典。
        config_path: 配置文件路径，默认使用项目 config/locations.json。

    Returns:
        校验后的景区字典。
    """
    path = config_path or _CONFIG_PATH
    validated = _validate_location_entry(location, 0, path)

    with path.open(encoding="utf-8") as f:
        data: list[dict[str, Any]] = json.load(f)

    for existing in data:
        if existing.get("name") == validated["name"]:
            logger.info("景区「%s」已在本地列表中，跳过写入", validated["name"])
            return validated

    entry = {
        "name": validated["name"],
        "lat": validated["lat"],
        "lon": validated["lon"],
        "elevation": validated["elevation"],
    }
    data.append(entry)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("景区「%s」已保存到 %s", validated["name"], path)
    return validated


def _validate_location_entry(entry: Any, index: int, path: Path) -> dict[str, Any]:
    """校验单个景区配置项。"""
    if not isinstance(entry, dict):
        raise ValueError(f"景区配置第 {index + 1} 项必须是对象: {path}")

    required = ("name", "lat", "lon", "elevation")
    missing = [field for field in required if field not in entry]
    if missing:
        raise ValueError(f"景区配置第 {index + 1} 项缺少字段 {', '.join(missing)}: {path}")

    name = entry["name"]
    lat = entry["lat"]
    lon = entry["lon"]
    elevation = entry["elevation"]

    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"景区配置第 {index + 1} 项 name 必须是非空字符串: {path}")
    if not isinstance(lat, int | float) or not -90 <= lat <= 90:
        raise ValueError(f"景区「{name}」lat 必须是 -90 到 90 之间的数字: {path}")
    if not isinstance(lon, int | float) or not -180 <= lon <= 180:
        raise ValueError(f"景区「{name}」lon 必须是 -180 到 180 之间的数字: {path}")
    if not isinstance(elevation, int | float):
        raise ValueError(f"景区「{name}」elevation 必须是数字: {path}")

    return entry


def load_locations(config_path: Path | None = None) -> list[dict[str, Any]]:
    """从 JSON 文件加载景区列表。

    Args:
        config_path: 配置文件路径，默认使用项目 config/locations.json。

    Returns:
        景区字典列表，每项含 name、lat、lon、elevation。
    """
    path = config_path or _CONFIG_PATH
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"景区配置格式错误: {path}")
    return [_validate_location_entry(entry, index, path) for index, entry in enumerate(data)]



def resolve_location(query: str, locations: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """根据用户输入模糊匹配景区。

    支持简称（如「黄山」匹配名称中包含该子串的景区）。

    Args:
        query: 用户输入的景区名称。
        locations: 景区列表，为 None 时从默认配置加载。

    Returns:
        匹配到的景区字典，未匹配返回 None。
    """
    q = query.strip()
    if not q:
        return None

    if locations is not None:
        locs = locations
    else:
        locs = load_locations() + list(_DYNAMIC_LOCATIONS.values())

    for loc in locs:
        if loc["name"] == q:
            return loc

    matches = [loc for loc in locs if q in loc["name"] or loc["name"] in q]
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    return min(matches, key=lambda loc: len(loc["name"]))


def list_location_names(locations: list[dict[str, Any]] | None = None) -> list[str]:
    """返回所有可用景区名称。"""
    locs = locations if locations is not None else load_locations()
    return [loc["name"] for loc in locs]
