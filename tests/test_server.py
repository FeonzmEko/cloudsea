"""FastAPI server 测试。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.server import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_get_locations(client: TestClient) -> None:
    resp = client.get("/api/locations")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(loc["name"] == "黄山" for loc in data)


def test_predict_empty_location(client: TestClient) -> None:
    resp = client.post("/api/predict", json={"location": "  "})
    assert resp.status_code == 200
    assert resp.json()["error"] == "请输入景区名称"


@patch("src.server.CloudSeaAgent")
def test_predict_known_location(mock_agent_cls: MagicMock, client: TestClient) -> None:
    prediction = {
        "location": "黄山",
        "prediction_time": "2026-06-03 05:00",
        "probability": "高",
        "best_window": "05:00-07:00",
        "confidence": 0.85,
        "summary": "很好",
        "key_factors": {"humidity": 90, "wind_speed": 1.0, "temp_inversion": True, "low_cloud": 70},
        "advice": "快冲",
    }
    mock_agent_cls.return_value.run.return_value = prediction
    resp = client.post("/api/predict", json={"location": "黄山"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["location"] == "黄山"
    assert data["probability"] == "高"


def test_predict_unknown_no_amap_key(client: TestClient, monkeypatch) -> None:
    monkeypatch.delenv("AMAP_API_KEY", raising=False)
    resp = client.post("/api/predict", json={"location": "不存在景区xyz"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["error"] == "景区未找到"


@patch("src.server.save_location")
@patch("src.server.CloudSeaAgent")
@patch("src.server.GeocodeAgent")
@patch("src.server.resolve_location", return_value=None)
def test_predict_geocode_fallback(
    _mock_resolve: MagicMock,
    mock_geo_cls: MagicMock,
    mock_cloud_cls: MagicMock,
    mock_save: MagicMock,
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AMAP_API_KEY", "test-key")

    mock_geo_cls.return_value.run.return_value = {
        "name": "测试山峰",
        "lat": 30.0,
        "lon": 115.0,
        "elevation": 1500,
    }
    mock_cloud_cls.return_value.run.return_value = {
        "location": "测试山峰",
        "prediction_time": "2026-06-03 05:00",
        "probability": "中",
        "best_window": "05:00-07:00",
        "confidence": 0.6,
        "summary": "一般",
        "key_factors": {"humidity": 80, "wind_speed": 2.0, "temp_inversion": False, "low_cloud": 60},
        "advice": "碰运气",
    }

    resp = client.post("/api/predict", json={"location": "测试山峰"})
    assert resp.status_code == 200
    assert resp.json()["location"] == "测试山峰"
    mock_save.assert_called_once()
