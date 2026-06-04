"""windy_tool 单元测试。"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.locations import resolve_location
from src.tools.windy_tool import (
    WINDY_ENDPOINT,
    _build_request_body,
    fetch_windy_forecast,
    get_weather_forecast,
    slice_next_24_hours,
)


class TestSliceNext24Hours:
    """24 小时切片逻辑测试。"""

    def test_keeps_only_future_24h(self, windy_response: dict) -> None:
        sliced = slice_next_24_hours(windy_response)
        assert len(sliced["ts"]) <= 24
        now_ms = int(time.time() * 1000)
        end_ms = now_ms + 24 * 3600 * 1000
        for t in sliced["ts"]:
            assert now_ms <= t <= end_ms
        assert len(sliced["temp-surface"]) == len(sliced["ts"])

    def test_preserves_units(self, windy_response: dict) -> None:
        sliced = slice_next_24_hours(windy_response)
        assert sliced["units"] == windy_response["units"]


class TestFetchWindyForecast:
    """Windy API 调用测试。"""

    def test_request_uses_official_endpoint_and_parameters(self) -> None:
        body = _build_request_body(30.13, 118.17, "test-key")

        assert WINDY_ENDPOINT == "https://api.windy.com/api/point-forecast/v2"
        assert body["parameters"] == ["temp", "rh", "wind", "lclouds", "precip"]

    @patch("src.tools.windy_tool.requests.post")
    def test_success_returns_sliced_data(self, mock_post: MagicMock, windy_response: dict) -> None:
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.json.return_value = windy_response
        mock_post.return_value = mock_resp

        result = fetch_windy_forecast(30.13, 118.17, api_key="test-key")
        assert "ts" in result
        assert len(result["ts"]) <= 24

    @patch("src.tools.windy_tool.requests.post")
    def test_retries_on_failure(self, mock_post: MagicMock, windy_response: dict) -> None:
        fail_resp = MagicMock(ok=False, status_code=503, text="Service Unavailable")
        ok_resp = MagicMock(ok=True)
        ok_resp.json.return_value = windy_response
        mock_post.side_effect = [fail_resp, ok_resp]

        with patch("src.tools.windy_tool.time.sleep"):
            result = fetch_windy_forecast(30.13, 118.17, api_key="test-key")

        assert mock_post.call_count == 2
        assert "ts" in result

    @patch("src.tools.windy_tool.requests.post")
    def test_raises_after_max_retries(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = requests.ConnectionError("network down")

        with patch("src.tools.windy_tool.time.sleep"):
            with pytest.raises(RuntimeError, match="已重试"):
                fetch_windy_forecast(30.13, 118.17, api_key="test-key")

        assert mock_post.call_count == 3


class TestGetWeatherForecastTool:
    """LangChain Tool 行为测试。"""

    @patch("src.tools.windy_tool.fetch_windy_forecast")
    def test_unknown_location_raises(self, mock_fetch: MagicMock) -> None:
        with pytest.raises(ValueError, match="未找到景区"):
            get_weather_forecast.invoke({"location_name": "不存在景区"})
        mock_fetch.assert_not_called()

    @patch("src.tools.windy_tool.fetch_windy_forecast")
    def test_known_location_returns_json(
        self, mock_fetch: MagicMock, windy_response: dict, sample_locations: list
    ) -> None:
        mock_fetch.return_value = slice_next_24_hours(windy_response)
        loc = resolve_location("黄山", sample_locations)
        assert loc is not None

        raw = get_weather_forecast.invoke({"location_name": "黄山"})
        assert "黄山" in raw
        mock_fetch.assert_called_once_with(loc["lat"], loc["lon"])
