"""Uzbek voice warnings, generated once with edge-tts and cached in static/audio (works offline afterwards)."""
import asyncio
import logging
import shutil
import subprocess
import threading

from . import config

log = logging.getLogger("tts")

VOICE = "uz-UZ-SardorNeural"
AUDIO_DIR = config.ROOT / "static" / "audio"
PHRASES = {
    "helmet": "Kaskangizni kiying!",
    "vest": "Himoya jiletingizni kiying!",
    "entry": "Diqqat! Bu hududga kirish taqiqlangan! Darhol chiqing!",
    "zone": "Diqqat! Xavfli zona! Darhol kaskangizni kiying!",
}


async def ensure_audio():
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    for name, text in PHRASES.items():
        path = AUDIO_DIR / f"{name}.mp3"
        if path.exists() and path.stat().st_size > 0:
            continue
        try:
            import edge_tts

            await asyncio.wait_for(edge_tts.Communicate(text, VOICE).save(str(path)), timeout=20)
            log.info("Ovoz fayli yaratildi: %s", path.name)
        except Exception as e:
            path.unlink(missing_ok=True)
            log.warning("Ovoz fayli yaratilmadi (%s): %s. Internet kerak; signal ovozi ishlatiladi.", path.name, e)


_audio_lock = threading.Lock()
_current_proc = None
_current_urgent = False
URGENT = ("zone", "entry")  # danger-zone warnings


def _find_player():
    """Return command prefix list for an available CLI audio player, or None."""
    for cmd in (
        ["afplay"],
        ["mpg123", "-q"],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"],
        ["cvlc", "--play-and-exit", "--intf", "dummy"],
        ["paplay"],  # needs an MP3-capable libsndfile; tried last
    ):
        if shutil.which(cmd[0]):
            return cmd
    return None


def play_local(key: str) -> bool:
    """Start a cached warning mp3 on the local speaker (non-blocking).

    One sound at a time. A danger-zone warning stops an ordinary one; otherwise a new request is skipped
    while something is playing.
    """
    global _current_proc, _current_urgent
    path = AUDIO_DIR / f"{key}.mp3"
    if not path.exists():
        return False
    player = _find_player()
    if not player:
        log.warning("Lokal ovoz ijrochisi topilmadi (afplay/mpg123/ffplay)")
        return False
    urgent = key in URGENT
    with _audio_lock:
        if _current_proc is not None and _current_proc.poll() is None:
            if _current_urgent or not urgent:
                return False
            _current_proc.terminate()
        try:
            _current_proc = subprocess.Popen(
                [*player, str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            _current_urgent = urgent
            return True
        except Exception as e:
            log.warning("Lokal ovoz ijro etilmadi: %s", e)
            return False
