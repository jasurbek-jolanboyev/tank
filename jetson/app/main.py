from __future__ import annotations

import argparse
import asyncio
import logging
import platform
from pathlib import Path

import uvicorn

from app.config.loader import load_config
from app.engine import DetectionEngine
from app.network.api import create_api


async def serve(config_path: Path) -> None:
    config = load_config(config_path)
    engine = DetectionEngine(config)
    app = create_api(engine)
    rest = config.raw["rest"]
    ws_port = int(config.raw["websocket"]["port"])
    logging.info("startup mode=%s platform=%s config=%s", config.mode, platform.platform(), config.path)
    servers = [uvicorn.Server(uvicorn.Config(app, host=rest["host"], port=int(rest["port"]), log_level="info"))]
    if ws_port != int(rest["port"]):
        # A second listener exposes the same API so /ws can retain its documented default port.
        servers.append(uvicorn.Server(uvicorn.Config(app, host=rest["host"], port=ws_port, log_level="warning", lifespan="off")))
    await asyncio.gather(*(server.serve() for server in servers))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path,
                        default=Path(__file__).parents[1] / "configs" / "dev.yaml")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        asyncio.run(serve(args.config))
    except KeyboardInterrupt:
        logging.info("shutdown requested")


if __name__ == "__main__":
    main()
