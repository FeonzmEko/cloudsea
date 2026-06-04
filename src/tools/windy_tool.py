"""Windy Point Forecast API v2 封装为 LangChain Tool。"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import requests
from langchain_core.tools import tool

from src.locations import resolve_location

logger = logging.getLogger(__name__)

WINDY_ENDPOINT = "https://api.windy.com/api/point-forecast/v2"
FORECAST_HOURS = 24
MAX_RETRIES = 3
RETRY_DELAY_SEC = 1.0

FORECAST_PARAMETERS = [
    "temp",
    "rh",
    "wind",
    "lclouds",
    "precip",
]
FORECAST_LEVELS = ["surface", "800h", "850h"]


def _build_request_body(lat: float, lon: float, api_key: str) -> dict[str, Any]:
    """构造 Windy API 请求体。"""
    return {
        "lat": lat,
        "lon": lon,
        "model": "gfs",
        "parameters": FORECAST_PARAMETERS,
        "levels": FORECAST_LEVELS,
        "key": api_key,
    }


def slice_next_24_hours(data: dict[str, Any]) -> dict[str, Any]:
    """只保留未来 24 小时内的时序数据切片。

    Args:
        data: Windy API 原始响应。

    Returns:
        切片后的响应，非时序字段（如 units）原样保留。
    """
    ts = data.get("ts")
    if not ts:
        return data

    now_ms = int(time.time() * 1000)
    end_ms = now_ms + FORECAST_HOURS * 3600 * 1000
    indices = [i for i, t in enumerate(ts) if now_ms <= t <= end_ms]

    if not indices:
        indices = list(range(min(FORECAST_HOURS, len(ts))))
    else:
        indices = indices[:FORECAST_HOURS]

    sliced: dict[str, Any] = {"ts": [ts[i] for i in indices]}
    if "units" in data:
        sliced["units"] = data["units"]

    for key, value in data.items():
        if key in ("ts", "units"):
            continue
        if isinstance(value, list) and len(value) == len(ts):
            sliced[key] = [value[i] for i in indices]

    return sliced


def fetch_windy_forecast(lat: float, lon: float, api_key: str | None = None) -> dict[str, Any]:
    """调用 Windy API 获取气象预报并切片未来 24 小时。

    Args:
        lat: 纬度。
        lon: 经度。
        api_key: API 密钥，默认从环境变量 WINDY_API_KEY 读取。

    Returns:
        切片后的预报数据字典。

    Raises:
        ValueError: 缺少 API 密钥或响应无效。
        RuntimeError: 请求失败且重试耗尽。
    """
    key = api_key or os.getenv("WINDY_API_KEY")
    if not key:
        raise ValueError("未配置 WINDY_API_KEY 环境变量")

    body = _build_request_body(lat, lon, key)
    last_error: str | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                WINDY_ENDPOINT,
                json=body,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            if not response.ok:
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.warning("Windy API 失败 (第 %d 次): %s", attempt, last_error)
            else:
                payload = response.json()
                if not isinstance(payload, dict) or "ts" not in payload:
                    raise ValueError("Windy API 返回数据格式异常")
                return slice_next_24_hours(payload)
        except requests.RequestException as exc:
            last_error = str(exc)
            logger.warning("Windy API 请求异常 (第 %d 次): %s", attempt, exc)

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY_SEC * attempt)

    raise RuntimeError(f"Windy API 调用失败，已重试 {MAX_RETRIES} 次: {last_error}")


@tool
def get_weather_forecast(location_name: str) -> str:
    """获取指定景区未来 24 小时的气象数值预报。

    输入景区中文名称（支持简称，如「黄山」），返回 JSON 字符串，
    包含温度、湿度、风速、低云量、降水等时序数据。
    """
    location = resolve_location(location_name)
    if location is None:
        raise ValueError(f"未找到景区「{location_name}」，请检查名称是否正确")

    forecast = fetch_windy_forecast(location["lat"], location["lon"])
    result = {
        "location": location,
        "forecast": forecast,
        "hours": FORECAST_HOURS,
    }
    return json.dumps(result, ensure_ascii=False)
