"""云海预测结果的终端展示格式化。"""

from __future__ import annotations

from typing import Any

_PROBABILITY_LABEL = {
    "高": "高 ★★★  值得冲！",
    "中": "中 ★★☆  可以碰碰运气",
    "低": "低 ★☆☆  建议改天",
}

_LABEL_WIDTH = 12
_VALUE_WIDTH = 56


def _disp_width(text: str) -> int:
    """计算字符串在终端的显示宽度（中文按 2 计）。"""
    return sum(2 if ord(ch) > 0x2E7F else 1 for ch in text)


def _pad(text: str, width: int) -> str:
    """按显示宽度右侧补空格对齐。"""
    return text + " " * max(0, width - _disp_width(text))


def _wrap_lines(text: str, width: int) -> list[str]:
    """按显示宽度换行，返回行列表。"""
    if not text:
        return ["（暂无）"]

    lines: list[str] = []
    current = ""
    current_width = 0
    for ch in str(text):
        ch_width = 2 if ord(ch) > 0x2E7F else 1
        if ch == "\n" or current_width + ch_width > width:
            lines.append(current)
            current = "" if ch == "\n" else ch
            current_width = 0 if ch == "\n" else ch_width
        else:
            current += ch
            current_width += ch_width
    lines.append(current)
    return lines or [""]


def _table_row(label: str, value: str) -> list[str]:
    """渲染一行表格（含竖线边框），值过长时自动换行。"""
    value_lines = _wrap_lines(value, _VALUE_WIDTH)
    rows = []
    for i, vline in enumerate(value_lines):
        label_cell = _pad(label if i == 0 else "", _LABEL_WIDTH)
        value_cell = _pad(vline, _VALUE_WIDTH)
        rows.append(f"│ {label_cell} │ {value_cell} │")
    return rows


def format_report(result: dict[str, Any]) -> str:
    """将预测结果格式化为带边框的表格。"""
    kf = result.get("key_factors", {})
    inversion = "有（云层更稳，利于云海）" if kf.get("temp_inversion") else "无"
    prob = _PROBABILITY_LABEL.get(result.get("probability", ""), result.get("probability", ""))
    confidence = result.get("confidence", 0)
    confidence_text = f"{confidence:.0%}" if isinstance(confidence, int | float) else str(confidence)

    weather = (
        f"湿度 {kf.get('humidity', '-')}%、"
        f"山顶风速 {kf.get('wind_speed', '-')} m/s、"
        f"低云覆盖 {kf.get('low_cloud', '-')}%、"
        f"逆温层 {inversion}"
    )

    rows = [
        ("预测地点", result.get("location", "")),
        ("云海概率", f"{prob}（把握程度 {confidence_text}）"),
        ("预测时间", result.get("prediction_time", "")),
        ("最佳观赏时段", result.get("best_window", "")),
        ("关键天气", weather),
        ("简要总结", result.get("summary", "")),
        ("观赏建议", result.get("advice", "")),
        ("安全提醒", result.get("safety_tips", "山路湿滑请慢行，凌晨登山带好照明，注意脚下安全。")),
        ("穿衣提醒", result.get("clothing_tips", "山顶比山下冷很多，建议多带一件保暖防风外套。")),
    ]

    inner = _LABEL_WIDTH + _VALUE_WIDTH + 5
    sep = "├" + "─" * (_LABEL_WIDTH + 2) + "┼" + "─" * (_VALUE_WIDTH + 2) + "┤"
    bottom = "└" + "─" * (_LABEL_WIDTH + 2) + "┴" + "─" * (_VALUE_WIDTH + 2) + "┘"
    title_bar = "┌" + "─" * inner + "┐"
    title_text = "│ " + _pad("云海预测", inner - 2) + " │"
    title_sep = "├" + "─" * (_LABEL_WIDTH + 2) + "┬" + "─" * (_VALUE_WIDTH + 2) + "┤"

    lines = ["", title_bar, title_text, title_sep]
    for idx, (label, value) in enumerate(rows):
        lines.extend(_table_row(label, value))
        lines.append(sep if idx < len(rows) - 1 else bottom)
    lines.append("")
    return "\n".join(lines)
