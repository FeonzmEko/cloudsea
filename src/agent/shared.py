"""Agent 间共享的模型初始化与输出解析工具。"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from json_repair import repair_json
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


def _find_json_candidate(text: str) -> str:
    """从模型输出中定位最可能的 JSON 字符串（不解析）。"""
    cleaned = text.strip()

    if cleaned.startswith("{"):
        return cleaned

    fenced = list(
        re.finditer(
            r"```(?:json)?\s*\n(\{.*?\})\s*\n```",
            cleaned,
            re.DOTALL | re.IGNORECASE,
        )
    )
    if fenced:
        return fenced[-1].group(1)

    depth = 0
    start = -1
    last_json = ""
    for i, ch in enumerate(cleaned):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start != -1:
                last_json = cleaned[start : i + 1]
    return last_json


def _extract_json(text: str) -> dict[str, Any]:
    """从模型输出中提取并解析 JSON，必要时用 json-repair 修复常见残缺。"""
    candidate = _find_json_candidate(text)
    if not candidate:
        raise json.JSONDecodeError("未在模型输出中找到 JSON", text, 0)

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    repaired = repair_json(candidate, return_objects=True)
    if isinstance(repaired, dict) and repaired:
        logger.warning("模型 JSON 不规范，已自动修复后解析")
        return repaired

    raise json.JSONDecodeError("无法解析或修复模型输出的 JSON", candidate, 0)


def _last_ai_text(messages: list[Any]) -> str:
    """从消息列表中取最后一条 AI 回复文本。"""
    for msg in reversed(messages):
        if not isinstance(msg, AIMessage):
            continue
        content = msg.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            return "".join(parts)
        return str(content)
    return ""


def _build_llm() -> ChatOpenAI:
    """初始化 DeepSeek 兼容的 ChatOpenAI 客户端。"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("未配置 DEEPSEEK_API_KEY 环境变量")
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
        temperature=0.3,
    )
