"""经纬度转换 Agent：把中文地名转换为合法经纬度与海拔。"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from src.agent.agent import _build_llm, _extract_json, _last_ai_text
from src.agent.prompts import GEOCODE_SYSTEM_PROMPT
from src.tools.geocode_tool import geocode_location

logger = logging.getLogger(__name__)


def _build_agent_graph():
    """构建带高德 geocode 工具的 Agent 图。"""
    return create_agent(
        model=_build_llm(),
        tools=[geocode_location],
        system_prompt=GEOCODE_SYSTEM_PROMPT,
    )


def _normalize_location(data: dict[str, Any], query: str) -> dict[str, Any]:
    """校验并规范化转换结果为标准景区字典。"""
    try:
        lat = float(data["lat"])
        lon = float(data["lon"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("缺少合法的经纬度") from exc

    if not -90 <= lat <= 90:
        raise ValueError(f"纬度超出范围: {lat}")
    if not -180 <= lon <= 180:
        raise ValueError(f"经度超出范围: {lon}")

    try:
        elevation = float(data.get("elevation", 0))
    except (TypeError, ValueError):
        elevation = 0.0
    if elevation <= 0:
        logger.warning("转换结果缺少有效海拔，按 1000 米估算")
        elevation = 1000.0

    name = data.get("name") or query
    if not isinstance(name, str) or not name.strip():
        name = query

    return {"name": name.strip(), "lat": lat, "lon": lon, "elevation": elevation}


class GeocodeAgent:
    """地名 → 经纬度转换 Agent。"""

    def __init__(self, graph: Any | None = None) -> None:
        self._graph = graph or _build_agent_graph()

    def run(self, place_name: str) -> dict[str, Any]:
        """把地名转换为标准景区字典。

        Args:
            place_name: 用户输入的中文地名。

        Returns:
            含 name、lat、lon、elevation 的字典；失败时含 error 字段。
        """
        query = place_name.strip()
        if not query:
            return {"error": "地名为空"}

        user_input = (
            f"请把地名「{query}」转换为经纬度和海拔。"
            f"先调用 geocode_location 工具获取坐标，再输出严格符合要求的 JSON。"
        )

        output = ""
        try:
            result = self._graph.invoke({"messages": [HumanMessage(content=user_input)]})
            output = _last_ai_text(result.get("messages", []))
            if not output:
                return {"error": "转换失败", "raw": str(result)}
            parsed = _extract_json(output)
            return _normalize_location(parsed, query)
        except json.JSONDecodeError as exc:
            logger.error("转换 Agent 输出非合法 JSON: %s", exc)
            return {"error": "转换失败", "raw": output}
        except ValueError as exc:
            logger.error("转换结果不合法: %s", exc)
            return {"error": "转换失败", "message": str(exc), "raw": output}
        except Exception as exc:
            logger.exception("转换 Agent 执行失败")
            return {"error": "执行失败", "message": str(exc)}
