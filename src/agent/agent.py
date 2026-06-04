"""LangChain Agent：调用 Windy 工具并由 DeepSeek 生成云海预测 JSON。"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from src.agent.prompts import SYSTEM_PROMPT
from src.agent.shared import _build_llm, _extract_json, _last_ai_text
from src.locations import resolve_location
from src.tools.windy_tool import get_weather_forecast

logger = logging.getLogger(__name__)

ALLOWED_PROBABILITIES = {"高", "中", "低"}
REQUIRED_RESULT_FIELDS = {
    "location",
    "prediction_time",
    "probability",
    "best_window",
    "confidence",
    "summary",
    "key_factors",
    "advice",
}
REQUIRED_KEY_FACTORS = {"humidity", "wind_speed", "temp_inversion", "low_cloud"}


def _validate_prediction_result(data: dict[str, Any]) -> None:
    """校验模型输出是否符合云海预测 JSON 结构。"""
    missing = REQUIRED_RESULT_FIELDS - set(data)
    if missing:
        raise ValueError(f"预测结果缺少字段: {', '.join(sorted(missing))}")

    probability = data["probability"]
    if probability not in ALLOWED_PROBABILITIES:
        raise ValueError("probability 只能是「高」「中」「低」之一")

    confidence = data["confidence"]
    if not isinstance(confidence, int | float) or not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence 必须是 0.0 到 1.0 之间的数字")

    key_factors = data["key_factors"]
    if not isinstance(key_factors, dict):
        raise ValueError("key_factors 必须是对象")

    missing_factors = REQUIRED_KEY_FACTORS - set(key_factors)
    if missing_factors:
        raise ValueError(f"key_factors 缺少字段: {', '.join(sorted(missing_factors))}")


def _build_agent_graph():
    """构建带 Windy 工具的 Agent 图。"""
    return create_agent(
        model=_build_llm(),
        tools=[get_weather_forecast],
        system_prompt=SYSTEM_PROMPT,
    )


class CloudSeaAgent:
    """云海预测 Agent。"""

    def __init__(self, graph: Any | None = None) -> None:
        self._graph = graph or _build_agent_graph()

    def run(self, location_query: str) -> dict[str, Any]:
        """对指定景区运行预测流程。

        Args:
            location_query: 景区名称（支持模糊匹配）。

        Returns:
            解析后的预测 JSON；失败时含 error 与 raw 字段。
        """
        location = resolve_location(location_query)
        if location is None:
            return {
                "error": "景区未找到",
                "message": f"无法匹配景区「{location_query}」",
            }

        user_input = (
            f"请为景区「{location['name']}」（海拔 {location['elevation']} 米，"
            f"坐标 {location['lat']}, {location['lon']}）分析未来 24 小时云海出现概率。"
            f"请先调用 get_weather_forecast 工具获取气象数据，再输出严格符合要求的 JSON。"
        )

        output = ""
        try:
            result = self._graph.invoke({"messages": [HumanMessage(content=user_input)]})
            output = _last_ai_text(result.get("messages", []))
            if not output:
                return {"error": "解析失败", "raw": str(result)}
            parsed = _extract_json(output)
            parsed.setdefault("location", location["name"])
            _validate_prediction_result(parsed)
            return parsed
        except json.JSONDecodeError as exc:
            logger.error("Agent 输出非合法 JSON: %s", exc)
            return {"error": "解析失败", "raw": output}
        except ValueError as exc:
            logger.error("Agent 输出格式不符合要求: %s", exc)
            return {"error": "格式校验失败", "message": str(exc), "raw": output}
        except Exception as exc:
            logger.exception("Agent 执行失败")
            return {"error": "执行失败", "message": str(exc)}


def run_prediction(location_query: str) -> dict[str, Any]:
    """便捷函数：运行单次云海预测。"""
    return CloudSeaAgent().run(location_query)
