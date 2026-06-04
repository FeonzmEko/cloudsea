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
from src.reporting import format_report  # noqa: E402


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

    print(format_report(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
