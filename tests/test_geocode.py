"""高德 geocode 工具、转换 Agent 与动态景区注册测试。"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from src.agent.geocode_agent import GeocodeAgent, _normalize_location
from src.locations import (
    clear_dynamic_locations,
    register_location,
    resolve_location,
)
from src.tools.geocode_tool import fetch_geocode, geocode_location


def _amap_ok_response() -> dict:
    return {
        "status": "1",
        "info": "OK",
        "geocodes": [
            {
                "location": "114.1900,27.4600",
                "formatted_address": "江西省萍乡市武功山",
                "level": "风景名胜",
            }
        ],
    }


class TestFetchGeocode:
    """高德 API 调用测试。"""

    @patch("src.tools.geocode_tool.requests.get")
    def test_success_parses_lat_lon(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock(ok=True)
        mock_resp.json.return_value = _amap_ok_response()
        mock_get.return_value = mock_resp

        result = fetch_geocode("武功山", api_key="test-key")
        assert result["lat"] == pytest.approx(27.46)
        assert result["lon"] == pytest.approx(114.19)
        assert "武功山" in result["formatted_address"]

    def test_missing_key_raises(self, monkeypatch) -> None:
        monkeypatch.delenv("AMAP_API_KEY", raising=False)
        with pytest.raises(ValueError, match="AMAP_API_KEY"):
            fetch_geocode("武功山")

    @patch("src.tools.geocode_tool.requests.get")
    def test_no_result_raises(self, mock_get: MagicMock) -> None:
        mock_resp = MagicMock(ok=True)
        mock_resp.json.return_value = {"status": "1", "info": "OK", "geocodes": []}
        mock_get.return_value = mock_resp

        with pytest.raises(ValueError, match="未匹配到地点"):
            fetch_geocode("不存在的地名xyz", api_key="test-key")

    @patch("src.tools.geocode_tool.requests.get")
    def test_retries_then_raises(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = requests.ConnectionError("network down")
        with patch("src.tools.geocode_tool.time.sleep"):
            with pytest.raises(RuntimeError, match="已重试"):
                fetch_geocode("武功山", api_key="test-key")
        assert mock_get.call_count == 3

    @patch("src.tools.geocode_tool.fetch_geocode")
    def test_tool_returns_json(self, mock_fetch: MagicMock) -> None:
        mock_fetch.return_value = {"lat": 27.46, "lon": 114.19, "formatted_address": "武功山"}
        raw = geocode_location.invoke({"place_name": "武功山"})
        assert "27.46" in raw
        assert "114.19" in raw


class TestNormalizeLocation:
    """转换结果规范化测试。"""

    def test_valid(self) -> None:
        loc = _normalize_location(
            {"name": "武功山", "lat": 27.46, "lon": 114.19, "elevation": 1918}, "武功山"
        )
        assert loc["name"] == "武功山"
        assert loc["elevation"] == 1918

    def test_missing_elevation_defaults(self) -> None:
        loc = _normalize_location({"lat": 27.46, "lon": 114.19}, "武功山")
        assert loc["name"] == "武功山"
        assert loc["elevation"] == 1000

    def test_invalid_lat_raises(self) -> None:
        with pytest.raises(ValueError, match="纬度"):
            _normalize_location({"lat": 200, "lon": 114.19}, "武功山")

    def test_missing_coords_raises(self) -> None:
        with pytest.raises(ValueError, match="经纬度"):
            _normalize_location({"name": "武功山"}, "武功山")


class TestGeocodeAgent:
    """转换 Agent 运行流程测试。"""

    def test_empty_query(self) -> None:
        agent = GeocodeAgent(graph=MagicMock())
        assert agent.run("  ")["error"] == "地名为空"

    def test_valid_conversion(self) -> None:
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "messages": [
                _ai_message('{"name": "武功山", "lat": 27.46, "lon": 114.19, "elevation": 1918}')
            ]
        }
        agent = GeocodeAgent(graph=mock_graph)
        loc = agent.run("武功山")
        assert loc["lat"] == pytest.approx(27.46)
        assert loc["elevation"] == 1918

    def test_invalid_output_returns_error(self) -> None:
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {"messages": [_ai_message("这不是 JSON")]}
        agent = GeocodeAgent(graph=mock_graph)
        assert agent.run("武功山")["error"] == "转换失败"


class TestDynamicRegistry:
    """运行时动态景区注册测试。"""

    def test_register_then_resolve(self) -> None:
        clear_dynamic_locations()
        register_location({"name": "武功山", "lat": 27.46, "lon": 114.19, "elevation": 1918})
        loc = resolve_location("武功山")
        assert loc is not None
        assert loc["lon"] == pytest.approx(114.19)
        clear_dynamic_locations()

    def test_register_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            register_location({"name": "坏数据", "lat": 999, "lon": 0, "elevation": 100})


def _ai_message(text: str):
    from langchain_core.messages import AIMessage

    return AIMessage(content=text)
