"""FastAPI Web 服务入口。"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

load_dotenv(_ROOT / ".env")

from src.agent.agent import CloudSeaAgent  # noqa: E402
from src.agent.geocode_agent import GeocodeAgent  # noqa: E402
from src.locations import (  # noqa: E402
    load_locations,
    register_location,
    resolve_location,
    save_location,
)

logger = logging.getLogger(__name__)

level_name = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, level_name, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
for noisy in ("httpx", "httpcore", "openai", "langchain"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

app = FastAPI(title="云海预测")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DIST_DIR = _ROOT / "frontend" / "dist"


class PredictRequest(BaseModel):
    location: str


@app.get("/api/locations")
def get_locations() -> list[dict[str, Any]]:
    """返回所有景区列表。"""
    return load_locations()


@app.post("/api/predict")
def predict(req: PredictRequest) -> dict[str, Any]:
    """执行云海预测，未命中内置列表时自动 geocode 并持久化。"""
    query = req.location.strip()
    if not query:
        return {"error": "请输入景区名称"}

    location = resolve_location(query)

    if location is None:
        if not os.getenv("AMAP_API_KEY"):
            return {
                "error": "景区未找到",
                "message": f"「{query}」不在内置列表且未配置 AMAP_API_KEY",
            }

        geo = GeocodeAgent().run(query)
        if "error" in geo:
            return {
                "error": "坐标解析失败",
                "message": geo.get("message", geo["error"]),
            }

        location = register_location(geo)
        save_location(location)
        logger.info(
            "已解析并保存「%s」→ (%.4f, %.4f) 海拔 %.0f 米",
            location["name"], location["lat"], location["lon"], location["elevation"],
        )

    result = CloudSeaAgent().run(location["name"])
    return result


if DIST_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str) -> FileResponse:
        """SPA fallback：所有非 API 路由返回 index.html。"""
        file = DIST_DIR / full_path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(DIST_DIR / "index.html")


if __name__ == "__main__":
    uvicorn.run("src.server:app", host="0.0.0.0", port=8000, reload=True)
