from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from app.engine import DetectionEngine


def create_api(engine: DetectionEngine) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await engine.start()
        yield
        await engine.stop()

    app = FastAPI(title="Tank Passive Detection", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    async def health():
        return engine.health.snapshot(engine.cameras.health, engine.detector.name,
                                      sum(1 for n in engine.esp32.nodes.values() if n.connected),
                                      engine.config.mode, engine.esp32.health())

    @app.get("/cameras")
    async def cameras():
        return {camera_id: {"online": item.online, "lastFrameTime": item.last_frame_ms,
                "captureFPS": round(item.capture_fps, 2), "processingFPS": round(item.processing_fps, 2),
                "inferenceLatencyMs": round(item.inference_latency_ms, 2),
                "droppedFrames": item.dropped, "reconnectCount": item.reconnect_count,
                "resolution": [item.width, item.height], "sourceType": item.source_type,
                "sector": item.sector, "error": item.error}
                for camera_id, item in engine.cameras.health.items()}

    @app.get("/preview/{camera_id}.jpg")
    async def preview(camera_id: str):
        if camera_id not in engine.cameras.health:
            raise HTTPException(404, "unknown camera")
        image = engine.cameras.latest_jpeg.get(camera_id)
        if image is None:
            raise HTTPException(503, "camera frame unavailable")
        return Response(image, media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    @app.websocket("/ws")
    async def websocket_endpoint(socket: WebSocket):
        await socket.accept()
        queue = engine.broker.subscribe()
        try:
            while True:
                await socket.send_json(await queue.get())
        except WebSocketDisconnect:
            pass
        finally:
            engine.broker.unsubscribe(queue)

    return app
