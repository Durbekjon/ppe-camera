"""FastAPI app: live MJPEG stream, JSON API and the dashboard page."""
import logging
import time
from contextlib import asynccontextmanager
from datetime import date as date_cls

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import alerts, auth, config, db, tts
from .pipeline import Pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)-8s %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("app")

pipeline: Pipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pipeline
    db.init()
    if not auth.has_users():
        log.warning("Foydalanuvchi yo'q. Yarating: .venv/bin/python -m tools.create_user NOM --role admin")
    await tts.ensure_audio()
    pipeline = Pipeline()
    pipeline.start()
    log.info("Tayyor, port %d  (demo rejimi: %s)", config.PORT, "ha" if pipeline.demo else "yo'q")
    yield
    pipeline.stop()


app = FastAPI(lifespan=lifespan)
STATIC = config.ROOT / "static"
COOKIE = "session"
# Everything else needs a login, so a newly added route is protected by default.
PUBLIC = {"/login", "/api/login", "/static/style.css", "/static/login.js"}
# Any request that changes something needs the admin role, except signing out.
ANY_ROLE_POSTS = {"/api/logout"}
LOOPBACK = {"127.0.0.1", "::1"}


@app.middleware("http")
async def require_login(request: Request, call_next):
    path = request.url.path
    # Backstop for any way of starting the server: from the network, only HTTPS is served.
    if request.url.scheme != "https" and (request.client is None or request.client.host not in LOOPBACK):
        return JSONResponse({"detail": "Tarmoq orqali faqat HTTPS bilan kiring"}, status_code=403)
    if path not in PUBLIC:
        user = auth.user_for(request.cookies.get(COOKIE))
        if not user:
            if path == "/":
                return RedirectResponse("/login", status_code=303)
            return JSONResponse({"detail": "Tizimga kiring"}, status_code=401)
        if request.method not in ("GET", "HEAD") and path not in ANY_ROLE_POSTS and user["role"] != auth.ADMIN:
            return JSONResponse({"detail": "Bu amal faqat admin uchun"}, status_code=403)
        request.state.user = user
    response = await call_next(request)
    if path.startswith(("/snapshots", "/api")):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/login")
def login_page():
    return FileResponse(STATIC / "login.html", headers={"Cache-Control": "no-store"})


class Credentials(BaseModel):
    username: str
    password: str


@app.post("/api/login")
def login(cred: Credentials, request: Request, response: Response):
    if auth.is_locked(cred.username):
        raise HTTPException(429, "Juda ko'p urinish. 1 daqiqadan keyin qayta urining")
    token = auth.login(cred.username, cred.password)
    if not token:
        log.warning("Muvaffaqiyatsiz kirish urinishi")
        raise HTTPException(401, "Login yoki parol noto'g'ri")
    response.set_cookie(COOKIE, token, max_age=auth.SESSION_S, httponly=True, samesite="strict",
                        secure=request.url.scheme == "https")
    return {"ok": True}


@app.post("/api/logout")
def logout(request: Request, response: Response):
    auth.logout(request.cookies.get(COOKIE))
    response.delete_cookie(COOKIE)
    return {"ok": True}


@app.get("/api/me")
def me(request: Request):
    return request.state.user


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/video")
def video(request: Request):
    token = request.cookies.get(COOKIE)

    def frames():
        seq, checked = 0, time.monotonic()
        while not pipeline.stopped:
            if time.monotonic() - checked > 2:  # stop streaming after logout or expiry
                if not auth.user_for(token):
                    return
                checked = time.monotonic()
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
        "voice": pipeline.voice,
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
