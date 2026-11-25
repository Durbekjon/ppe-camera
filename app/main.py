"""FastAPI app: live MJPEG stream, JSON API and the dashboard page."""
import logging
from contextlib import asynccontextmanager
from datetime import date as date_cls

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import alerts, config, db, tts
from .pipeline import Pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)-8s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("app")

pipeline: Pipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    db.init()
    await tts.ensure_audio()
    pipeline = Pipeline()
    pipeline.start()
    log.info("Tayyor: http://localhost:%d  (demo rejimi: %s)", config.PORT, "ha" if pipeline.demo else "yo'q")
    yield
    pipeline.stop()


app = FastAPI(lifespan=lifespan)
STATIC = config.ROOT / "static"


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/video")
def video():
    def frames():
        seq = 0
        while not pipeline.stopped:
            seq, jpeg = pipeline.wait_jpeg(seq)
            if jpeg:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"

    return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/api/status")
def status():
    camera = pipeline.video.connected
    state = pipeline.state if camera else {"status": "offline", "people": 0, "violators": 0}
    return {
        **state,
        "camera": camera,
        "fps": round(pipeline.fps, 1) if camera else 0,
        "demo": pipeline.demo,
        "telegram": alerts.telegram_configured(),
        "require_vest": config.REQUIRE_VEST,
        "last_incident_id": db.last_id(),
    }


@app.get("/api/incidents")
def incidents(limit: int = 30):
    return db.list_incidents(min(limit, 200))


@app.get("/api/report")
def report(date: str = ""):
    return db.report(date or date_cls.today().isoformat())


class Zone(BaseModel):
    points: list[tuple[float, float]]


@app.get("/api/zone")
def get_zone():
    return {"points": pipeline.engine.zone}


@app.post("/api/zone")
def set_zone(zone: Zone):
    if zone.points and len(zone.points) < 3:
        raise HTTPException(400, "Zona uchun kamida 3 ta nuqta kerak")
    pipeline.set_zone(zone.points)
    return {"points": pipeline.engine.zone}


class Demo(BaseModel):
    on: bool


@app.post("/api/demo")
def set_demo(demo: Demo):
    try:
        pipeline.set_demo(demo.on)
    except FileNotFoundError:
        raise HTTPException(400, f"Demo video topilmadi: {config.DEMO_VIDEO}")
    return {"demo": pipeline.demo}


@app.post("/api/telegram-test")
def telegram_test():
    ok, err = alerts.telegram_send("✅ Xavfsizlik nazorati: sinov xabari")
    return {"ok": ok, "error": err}


alerts.SNAPSHOTS.mkdir(parents=True, exist_ok=True)
app.mount("/snapshots", StaticFiles(directory=alerts.SNAPSHOTS), name="snapshots")
app.mount("/static", StaticFiles(directory=STATIC), name="static")
