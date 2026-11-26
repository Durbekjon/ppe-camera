"""All settings come from environment variables (optionally via a .env file)."""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            value = value.strip()
            if value[:1] not in ("'", '"'):  # "KEY=1   # note": the note is not part of the value
                value = re.split(r"\s+#", value, maxsplit=1)[0]
            os.environ.setdefault(key.strip(), value.strip("\"'"))


_load_dotenv(ROOT / ".env")


def _flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes", "on")


_default_demo = DATA / "demo.mp4"
if not _default_demo.exists() and (ROOT / "testdata" / "stills.mp4").exists():
    _default_demo = ROOT / "testdata" / "stills.mp4"
DEMO_VIDEO = os.getenv("DEMO_VIDEO", str(_default_demo))
DEMO_MODE = _flag("DEMO_MODE")
# Webcam index ("0"), stream URL (http://..., rtsp://...) or a video file path.
VIDEO_SOURCE = os.getenv("VIDEO_SOURCE", "0")
# Several cameras: "Kirish=0;Sex=rtsp://...". Empty: the single VIDEO_SOURCE.
CAMERAS = os.getenv("CAMERAS", "")

_default_model = ROOT / "models" / "ppe_yolov8s.pt"
if not _default_model.exists() and (ROOT / "models" / "ppe_yolov8n_alt.pt").exists():
    _default_model = ROOT / "models" / "ppe_yolov8n_alt.pt"
MODEL_PATH = os.getenv("MODEL_PATH", str(_default_model))
# Warn when a running camera shows nothing useful (covered, black, blank wall, out of focus). Off by default.
TAMPER_CHECK = _flag("TAMPER_CHECK", "0")
# Skeleton model: only people with a skeleton are judged, and any body part in a zone counts as inside it.
SKELETON = _flag("SKELETON", "1")
POSE_MODEL_PATH = os.getenv("POSE_MODEL_PATH", str(ROOT / "models" / "yolo11n-pose.pt"))
POSE_IMG_SIZE = int(os.getenv("POSE_IMG_SIZE", "480"))
IMG_SIZE = int(os.getenv("IMG_SIZE", "480"))
CONF = float(os.getenv("CONF", "0.4"))  # people and "no helmet" detections
GEAR_CONF = float(os.getenv("GEAR_CONF", "0.25"))  # helmets and vests
FRAME_WIDTH = int(os.getenv("FRAME_WIDTH", "960"))  # frames are downscaled to this width

REQUIRE_VEST = _flag("REQUIRE_VEST")
# "missing": a person with no helmet detected on them is violating (default).
# "explicit": only when the model positively sees a bare head (fewer false alarms, more misses).
HELMET_RULE = os.getenv("HELMET_RULE", "missing")
DEBOUNCE_S = float(os.getenv("DEBOUNCE_S", "1.5"))
COOLDOWN_S = float(os.getenv("COOLDOWN_S", "15"))

# A violation counts as over only after this many seconds of continuous compliance.
RESOLVE_S = float(os.getenv("RESOLVE_S", "5"))
# A worker who disappears and gets a new ID within this time, near the same spot, is not counted again.
REJOIN_S = float(os.getenv("REJOIN_S", "10"))
# Ordinary alerts raised within this many seconds share one Telegram message. Zone alerts are never delayed.
TELEGRAM_GROUP_S = float(os.getenv("TELEGRAM_GROUP_S", "5"))

# Privacy: faces in saved and sent snapshots are blurred; snapshots expire after this many days (0 = keep).
BLUR_FACES = _flag("BLUR_FACES", "1")
# Play voice warnings on the server's local speaker even when no browser is open.
LOCAL_AUDIO = _flag("LOCAL_AUDIO", "0")
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "30"))

# Keep a clean (blurred) frame per incident so false alarms can be exported for retraining.
SAVE_RAW = _flag("SAVE_RAW", "1")

# An alert Telegram has not accepted is retried for this long.
TELEGRAM_RETRY_HOURS = float(os.getenv("TELEGRAM_RETRY_HOURS", "24"))

# "Ko'rildi" / "Noto'g'ri signal" buttons under incident alerts.
TELEGRAM_BUTTONS = _flag("TELEGRAM_BUTTONS", "1")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DAILY_SUMMARY_HOUR = int(os.getenv("DAILY_SUMMARY_HOUR", "18"))

PORT = int(os.getenv("PORT", "8000"))
