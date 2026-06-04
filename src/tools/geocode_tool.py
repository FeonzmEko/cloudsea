"""高德地图 Geocoding API 封装为 LangChain Tool。"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import requests
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

AMAP_GEOCODE_ENDPOINT = "https://restapi.amap.com/v3/geocode/geo"
MAX_RETRIES = 3
RETRY_DELAY_SEC = 1.0


def fetch_geocode(address: str, api_key: str | None = None) -> dict[str, Any]:
    """调用高德 Geocoding API 把中文地名转为经纬度。

    Args:
        address: 中文地名，如「武功山」。
        api_key: 高德 Web 服务 API Key，默认从环境变量 AMAP_API_KEY 读取。

    Returns:
        含 lat、lon、formatted_address、level 的字典。

    Raises:
        ValueError: 缺少 API 密钥或未匹配到地点。
        RuntimeError: 请求失败且重试耗尽。
    """
    key = api_key or os.getenv("AMAP_API_KEY")
    if not key:
        raise ValueError("未配置 AMAP_API_KEY 环境变量")

    params = {"address": address, "key": key, "output": "JSON"}
    last_error: str | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(AMAP_GEOCODE_ENDPOINT, params=params, timeout=15)
            if not response.ok:
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.warning("高德 API 失败 (第 %d 次): %s", attempt, last_error)
            else:
                payload = response.json()
                if payload.get("status") != "1":
                    info = payload.get("info", "未知错误")
                    raise ValueError(f"高德 API 返回错误: {info}")
                geocodes = payload.get("geocodes") or []
                if not geocodes:
                    raise ValueError(f"高德未匹配到地点「{address}」")
                first = geocodes[0]
                location = first.get("location", "")
                if "," not in location:
                    raise ValueError("高德返回的坐标格式异常")
                lon_str, lat_str = location.split(",", 1)
                return {
                    "lat": float(lat_str),
                    "lon": float(lon_str),
                    "formatted_address": first.get("formatted_address", address),
                    "level": first.get("level", ""),
                }
        except requests.RequestException as exc:
            last_error = str(exc)
            logger.warning("高德 API 请求异常 (第 %d 次): %s", attempt, exc)

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY_SEC * attempt)

    raise RuntimeError(f"高德 API 调用失败，已重试 {MAX_RETRIES} 次: {last_error}")


@tool
def geocode_location(place_name: str) -> str:
    """把中文地名（如「武功山」「东灵山」）转换为经纬度坐标用于云海预测。

    返回 JSON 字符串，包含 lat（纬度）、lon（经度）、formatted_address（标准地址）。
    """
    result = fetch_geocode(place_name)
    return json.dumps(result, ensure_ascii=False)
