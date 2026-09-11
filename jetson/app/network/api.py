from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response, StreamingResponse

from app.engine import DetectionEngine


def create_api(engine: DetectionEngine) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await engine.start()
        yield
        await engine.stop()

    app = FastAPI(title="Tank Passive Detection", version="0.1.0", lifespan=lifespan)

    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        # A dependency-free operator view, available from any browser on the LAN.
        return HTMLResponse("""<!doctype html><html lang='uz'><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'><title>TANK monitoring</title>
<style>body{font:16px system-ui;background:#101418;color:#eee;margin:20px}h1{margin:0 0 8px}.state{padding:8px;background:#202832;border-radius:6px;margin:8px 0}.cams{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}.cam{background:#1b222b;padding:10px;border-radius:8px}.cam img{width:100%;background:#000;aspect-ratio:4/3;object-fit:contain}.ok{color:#6ee7a0}.bad{color:#ff8c8c}pre{max-height:180px;overflow:auto;background:#090b0d;padding:8px}</style>
<h1>TANK operator monitoring</h1><div id='state' class='state'>Ulanmoqda...</div><div id='cams' class='cams'></div><h3>Oxirgi hodisalar</h3><pre id='log'></pre>
<script>
const state=document.querySelector('#state'), cams=document.querySelector('#cams'), log=document.querySelector('#log');
function esc(v){return String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]))}
async function refresh(){try{const [h,c]=await Promise.all([fetch('/health'),fetch('/cameras')]);if(!h.ok||!c.ok)throw Error('HTTP '+h.status);const health=await h.json(), data=await c.json();state.className='state ok';state.textContent='Server ishlayapti · rejim '+health.mode+' · detector '+health.detector;cams.innerHTML=Object.entries(data).map(([id,x])=>`<div class='cam'><b>${esc(id)} · ${esc(x.sector)}</b><br><span class='${x.online?'ok':'bad'}'>${x.online?'Ulangan':'Kamera uzilgan'}</span> · FPS ${Number(x.captureFPS||0).toFixed(1)}<img src='/stream/${encodeURIComponent(id)}.mjpg' onerror="this.alt='Kamera uzilgan';this.src='';"><small>${esc(x.error||'')}</small></div>`).join('')}catch(e){state.className='state bad';state.textContent='Server bilan aloqa yo‘q: '+e.message}}
function connect(){const ws=new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/ws');ws.onmessage=e=>{const m=JSON.parse(e.data);log.textContent=(JSON.stringify(m)+"\\n"+log.textContent).slice(0,8000)};ws.onclose=()=>setTimeout(connect,2000)}
refresh();setInterval(refresh,3000);connect();
</script></html>""")

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

    @app.get("/stream/{camera_id}.mjpg")
    async def stream(camera_id: str):
        """Low-latency MJPEG stream for browsers and the operator console."""
        if camera_id not in engine.cameras.health:
            raise HTTPException(404, "unknown camera")

        async def frames():
            last_image: bytes | None = None
            while True:
                image = engine.cameras.latest_jpeg.get(camera_id)
                if image is not None and image != last_image:
                    last_image = image
                    yield (b"--tankframe\r\nContent-Type: image/jpeg\r\n"
                           + f"Content-Length: {len(image)}\r\n\r\n".encode()
                           + image + b"\r\n")
                preview_fps = float(engine.cameras.configs[camera_id].get("previewFps", 5))
                await asyncio.sleep(1 / max(1.0, preview_fps))

        return StreamingResponse(
            frames(),
            media_type="multipart/x-mixed-replace; boundary=tankframe",
            headers={"Cache-Control": "no-store, no-cache", "Pragma": "no-cache"},
        )

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
