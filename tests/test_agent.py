"""agent 单元测试。"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from src.agent.agent import CloudSeaAgent, _extract_json


class TestExtractJson:
    """JSON 解析辅助函数测试。"""

    def test_plain_json(self) -> None:
        data = _extract_json('{"probability": "高"}')
        assert data["probability"] == "高"

    def test_markdown_wrapped_json(self) -> None:
        text = '```json\n{"probability": "中"}\n```'
        data = _extract_json(text)
        assert data["probability"] == "中"

    def test_json_with_analysis_prefix(self) -> None:
        text = '一大段分析...\n\n```json\n{"probability": "高", "low_cloud": 90}\n```'
        data = _extract_json(text)
        assert data["probability"] == "高"

    def test_repairs_unescaped_inner_quotes(self) -> None:
        # 字符串里混入未转义的英文引号，标准解析会失败，需自动修复
        broken = '{"summary": "明天概率极高，"人在云上"，值得冲", "probability": "高"}'
        data = _extract_json(broken)
        assert data["probability"] == "高"

    def test_repairs_trailing_comma(self) -> None:
        broken = '{"probability": "中", "confidence": 0.6,}'
        data = _extract_json(broken)
        assert data["probability"] == "中"


class TestCloudSeaAgent:
    """Agent 运行流程测试。"""

    def test_unknown_location(self) -> None:
        agent = CloudSeaAgent(graph=MagicMock())
        result = agent.run("虚构山")
        assert result["error"] == "景区未找到"

    def test_valid_json_output(self) -> None:
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
        }
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "messages": [AIMessage(content=json.dumps(prediction, ensure_ascii=False))]
        }

        agent = CloudSeaAgent(graph=mock_graph)
        result = agent.run("黄山")

        assert result["probability"] == "高"
        assert result["location"] == "黄山"
        mock_graph.invoke.assert_called_once()

    def test_invalid_json_returns_error(self) -> None:
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "messages": [AIMessage(content="这不是 JSON")]
        }

        agent = CloudSeaAgent(graph=mock_graph)
        result = agent.run("黄山")

        assert result["error"] == "解析失败"
        assert "raw" in result

    def test_invalid_probability_returns_validation_error(self) -> None:
        prediction = {
            "location": "黄山",
            "prediction_time": "2026-06-02 06:00",
            "probability": "很高",
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
        }
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "messages": [AIMessage(content=json.dumps(prediction, ensure_ascii=False))]
        }

        agent = CloudSeaAgent(graph=mock_graph)
        result = agent.run("黄山")

        assert result["error"] == "格式校验失败"
        assert "probability" in result["message"]

    def test_missing_key_factor_returns_validation_error(self) -> None:
        prediction = {
            "location": "黄山",
            "prediction_time": "2026-06-02 06:00",
            "probability": "中",
            "best_window": "明日清晨 05:30-07:00",
            "confidence": 0.7,
            "summary": "湿度较高，但低云数据缺失，判断有限",
            "key_factors": {
                "humidity": 88,
                "wind_speed": 2.1,
                "temp_inversion": False,
            },
            "advice": "建议结合现场能见度判断",
        }
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "messages": [AIMessage(content=json.dumps(prediction, ensure_ascii=False))]
        }

        agent = CloudSeaAgent(graph=mock_graph)
        result = agent.run("黄山")

        assert result["error"] == "格式校验失败"
        assert "low_cloud" in result["message"]

    @patch("src.agent.agent._build_llm")
    def test_missing_deepseek_key(self, mock_llm: MagicMock) -> None:
        import pytest

        from src.agent.agent import _build_agent_graph

        mock_llm.side_effect = ValueError("未配置 DEEPSEEK_API_KEY 环境变量")
        with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
            _build_agent_graph()
