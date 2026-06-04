"""云海预测命令行入口。"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 将项目根目录加入模块搜索路径
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.agent.agent import CloudSeaAgent  # noqa: E402
from src.agent.geocode_agent import GeocodeAgent  # noqa: E402
from src.locations import (  # noqa: E402
    list_location_names,
    register_location,
    resolve_location,
    save_location,
)


def _configure_logging(level_name: str | None = None) -> None:
    """根据命令行参数或环境变量配置日志级别。"""
    level_name = (level_name or os.getenv("LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )
    for noisy in ("httpx", "httpcore", "openai", "langchain"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="云海预测 Agent")
    parser.add_argument(
        "--location",
        help="景区名称，支持简称模糊匹配（如：黄山）",
    )
    parser.add_argument(
        "--list-locations",
        action="store_true",
        help="列出当前支持的景区名称",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        help="临时覆盖 LOG_LEVEL 日志级别",
    )
    return parser.parse_args()


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


def _wrap(text: str, width: int = 40, indent: str = "  ") -> str:
    """按显示宽度对文本换行（保留给其它调用方）。"""
    body = _wrap_lines(text, width)
    return "\n".join(f"{indent}{line}" for line in body)


def _table_row(label: str, value: str) -> list[str]:
    """渲染一行表格（含竖线边框），值过长时自动换行。"""
    value_lines = _wrap_lines(value, _VALUE_WIDTH)
    rows = []
    for i, vline in enumerate(value_lines):
        label_cell = _pad(label if i == 0 else "", _LABEL_WIDTH)
        value_cell = _pad(vline, _VALUE_WIDTH)
        rows.append(f"│ {label_cell} │ {value_cell} │")
    return rows

def _format_report(result: dict) -> str:
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

    inner = _LABEL_WIDTH + _VALUE_WIDTH + 5  # 两侧空格与中间竖线
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


def main() -> int:
    """程序主入口。"""
    load_dotenv(_ROOT / ".env")
    args = _parse_args()
    _configure_logging(args.log_level)

    if args.list_locations:
        try:
            for name in list_location_names():
                print(name)
        except Exception as exc:
            logging.error("景区配置加载失败：%s", exc)
            return 1
        return 0

    if not args.location:
        logging.error("请使用 --location 指定景区，或使用 --list-locations 查看支持的景区。")
        return 2

    try:
        location = resolve_location(args.location)
        names = "、".join(list_location_names())
    except Exception as exc:
        logging.error("景区配置加载失败：%s", exc)
        logging.error("请检查 config/locations.json 的 JSON 格式和字段。")
        return 1

    if location is None:
        if not os.getenv("AMAP_API_KEY"):
            logging.error("未找到景区「%s」。支持的景区：%s", args.location, names)
            logging.error("如需查询列表外的地名，请在 .env 配置 AMAP_API_KEY 以启用高德坐标解析。")
            return 1

        print(f"\n  「{args.location}」不在内置列表，正在用高德解析坐标...\n")
        geo = GeocodeAgent().run(args.location)
        if "error" in geo:
            logging.error("坐标解析失败：%s", geo.get("message", geo["error"]))
            if geo.get("raw"):
                logging.debug("原始输出: %s", geo["raw"])
            logging.error("请确认地名正确，且 .env 中 AMAP_API_KEY、DEEPSEEK_API_KEY 已正确配置。")
            return 1

        location = register_location(geo)
        save_location(location)
        logging.info(
            "已解析「%s」→ 坐标 (%.4f, %.4f)，海拔约 %.0f 米，已保存到本地列表",
            location["name"], location["lat"], location["lon"], location["elevation"],
        )

    print(f"\n  正在分析「{location['name']}」云海条件，请稍候...\n")
    result = CloudSeaAgent().run(location["name"])

    if "error" in result:
        logging.error("%s", result.get("message", result["error"]))
        if result.get("raw"):
            logging.debug("原始输出: %s", result["raw"])
        logging.error("请确认 .env 中已配置 WINDY_API_KEY 和 DEEPSEEK_API_KEY，必要时使用 --log-level DEBUG 查看详情。")
        return 1

    print(_format_report(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
