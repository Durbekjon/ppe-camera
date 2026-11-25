"""All settings come from environment variables (optionally via a .env file)."""
import os
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
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


_load_dotenv(ROOT / ".env")


def _flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes", "on")


DEMO_VIDEO = os.getenv("DEMO_VIDEO", str(DATA / "demo.mp4"))
DEMO_MODE = _flag("DEMO_MODE")
# Webcam index ("0"), stream URL (http://..., rtsp://...) or a video file path.
VIDEO_SOURCE = os.getenv("VIDEO_SOURCE", "0")

MODEL_PATH = os.getenv("MODEL_PATH", str(ROOT / "models" / "ppe_yolov8s.pt"))
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

# Ordinary alerts raised within this many seconds share one Telegram message. Zone alerts are never delayed.
TELEGRAM_GROUP_S = float(os.getenv("TELEGRAM_GROUP_S", "5"))

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

PORT = int(os.getenv("PORT", "8000"))
