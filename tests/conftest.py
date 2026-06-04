"""pytest 公共 fixture。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCATIONS_PATH = PROJECT_ROOT / "config" / "locations.json"


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch) -> None:
    """隔离测试环境：禁用 .env 加载、清空敏感变量与动态景区注册表。"""
    from src.locations import clear_dynamic_locations

    monkeypatch.setattr("src.main.load_dotenv", lambda *a, **k: None)
    try:
        monkeypatch.setattr("src.server.load_dotenv", lambda *a, **k: None)
    except AttributeError:
        pass
    for var in ("AMAP_API_KEY", "DEEPSEEK_API_KEY", "WINDY_API_KEY"):
        monkeypatch.delenv(var, raising=False)

    clear_dynamic_locations()
    yield
    clear_dynamic_locations()


@pytest.fixture
def sample_locations() -> list[dict]:
    """加载真实景区配置用于测试。"""
    with LOCATIONS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def windy_response() -> dict:
    """模拟 Windy API 响应（含 48 小时逐小时数据）。"""
    import time

    base_ms = int(time.time() * 1000)
    ts = [base_ms + i * 3600 * 1000 for i in range(48)]
    n = len(ts)
    return {
        "ts": ts,
        "units": {
            "temp-surface": "K",
            "temp-850h": "K",
            "rh-surface": "%",
            "wind_u-surface": "m*s-1",
            "wind_v-surface": "m*s-1",
            "clouds_low-surface": "%",
            "precip-surface": "mm",
        },
        "temp-surface": [288.0 + i * 0.1 for i in range(n)],
        "temp-850h": [285.0 + i * 0.1 for i in range(n)],
        "rh-surface": [80.0 + i for i in range(n)],
        "wind_u-surface": [1.0] * n,
        "wind_v-surface": [0.5] * n,
        "clouds_low-surface": [60.0 + i for i in range(n)],
        "precip-surface": [0.0] * n,
    }
