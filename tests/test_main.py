"""命令行入口测试。"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

from src import main as cli


def test_list_locations(monkeypatch, capsys) -> None:
    """--list-locations 输出支持的景区名称。"""
    monkeypatch.setattr(sys, "argv", ["main.py", "--list-locations"])

    exit_code = cli.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "黄山" in captured.out


def test_missing_location_returns_usage_error(monkeypatch, capsys) -> None:
    """未提供 --location 时返回参数使用错误。"""
    monkeypatch.setattr(sys, "argv", ["main.py"])

    exit_code = cli.main()
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--location" in captured.err


def test_unknown_location_returns_error(monkeypatch, capsys) -> None:
    """未知景区返回错误并提示查看列表。"""
    monkeypatch.setattr(sys, "argv", ["main.py", "--location", "不存在景区"])

    exit_code = cli.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "未找到景区" in captured.err
    assert "AMAP_API_KEY" in captured.err


def test_geocode_fallback_for_unlisted_location(monkeypatch, capsys) -> None:
    """列表外地名在配置 AMAP_API_KEY 后走转换 Agent 并完成预测。"""
    monkeypatch.setenv("AMAP_API_KEY", "test-key")

    geo_agent = MagicMock()
    geo_agent.run.return_value = {
        "name": "梵净山",
        "lat": 27.91,
        "lon": 108.68,
        "elevation": 2572,
    }
    prediction = {
        "location": "梵净山",
        "prediction_time": "2026-06-03 05:00",
        "probability": "中",
        "best_window": "清晨 05:00-07:00",
        "confidence": 0.6,
        "summary": "条件一般。",
        "key_factors": {
            "humidity": 85,
            "wind_speed": 2.0,
            "temp_inversion": False,
            "low_cloud": 70,
        },
        "advice": "早点上山。",
        "safety_tips": "注意安全。",
        "clothing_tips": "注意保暖。",
    }
    cloud_agent = MagicMock()
    cloud_agent.run.return_value = prediction

    monkeypatch.setattr(cli, "GeocodeAgent", MagicMock(return_value=geo_agent))
    monkeypatch.setattr(cli, "CloudSeaAgent", MagicMock(return_value=cloud_agent))
    monkeypatch.setattr(cli, "save_location", MagicMock())
    monkeypatch.setattr(cli, "resolve_location", MagicMock(return_value=None))
    monkeypatch.setattr(sys, "argv", ["main.py", "--location", "梵净山"])

    exit_code = cli.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "梵净山" in captured.out
    geo_agent.run.assert_called_once_with("梵净山")
    cloud_agent.run.assert_called_once_with("梵净山")


def test_prediction_success_outputs_report(monkeypatch, capsys) -> None:
    """预测成功时输出可读报告并返回 0。"""
    prediction = {
        "location": "黄山",
        "prediction_time": "2026-06-02 06:00",
        "probability": "高",
        "best_window": "明日清晨 05:30-07:00",
        "confidence": 0.82,
        "summary": "湿度高、微风、逆温明显",
        "key_factors": {
            "humidity": 92,
            "wind_speed": 1.8,
            "temp_inversion": True,
            "low_cloud": 75,
        },
        "advice": "建议 05:00 前到达观景台",
        "safety_tips": "凌晨山路湿滑，请带头灯并慢行。",
        "clothing_tips": "山顶约 5 度，建议穿厚外套和防风衣。",
    }
    mock_agent = MagicMock()
    mock_agent.run.return_value = prediction
    monkeypatch.setattr(cli, "CloudSeaAgent", MagicMock(return_value=mock_agent))
    monkeypatch.setattr(sys, "argv", ["main.py", "--location", "黄山"])

    exit_code = cli.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "云海预测" in captured.out
    assert "预测地点" in captured.out
    assert "黄山" in captured.out
    assert "高 ★★★" in captured.out
    assert "82%" in captured.out
    assert "92%" in captured.out
    assert "1.8 m/s" in captured.out
    assert "建议 05:00 前到达观景台" in captured.out
    assert "安全提醒" in captured.out
    assert "头灯" in captured.out
    assert "穿衣提醒" in captured.out
    assert "防风衣" in captured.out
    assert "│" in captured.out
    assert "─" in captured.out
    mock_agent.run.assert_called_once_with("黄山")


def test_report_uses_fallback_tips_when_missing(monkeypatch, capsys) -> None:
    """模型未返回安全/穿衣提醒时使用兜底文案。"""
    prediction = {
        "location": "庐山",
        "prediction_time": "2026-06-02 06:00",
        "probability": "中",
        "best_window": "清晨 05:30-07:00",
        "confidence": 0.6,
        "summary": "条件一般，可碰运气。",
        "key_factors": {
            "humidity": 80,
            "wind_speed": 2.0,
            "temp_inversion": False,
            "low_cloud": 60,
        },
        "advice": "早点上山。",
    }
    mock_agent = MagicMock()
    mock_agent.run.return_value = prediction
    monkeypatch.setattr(cli, "CloudSeaAgent", MagicMock(return_value=mock_agent))
    monkeypatch.setattr(sys, "argv", ["main.py", "--location", "庐山"])

    exit_code = cli.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "安全提醒" in captured.out
    assert "穿衣提醒" in captured.out
    assert "山路湿滑" in captured.out
    assert "山顶比山下冷" in captured.out


def test_prediction_error_returns_nonzero(monkeypatch, capsys) -> None:
    """Agent 返回错误时 CLI 返回非 0。"""
    mock_agent = MagicMock()
    mock_agent.run.return_value = {"error": "执行失败", "message": "未配置 DEEPSEEK_API_KEY 环境变量"}
    monkeypatch.setattr(cli, "CloudSeaAgent", MagicMock(return_value=mock_agent))
    monkeypatch.setattr(sys, "argv", ["main.py", "--location", "黄山"])

    exit_code = cli.main()
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "DEEPSEEK_API_KEY" in captured.err
