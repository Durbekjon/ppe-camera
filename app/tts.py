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


def _find_player():
    """Return command prefix list for an available CLI audio player, or None."""
    for cmd in (
        ["afplay"],
        ["mpg123", "-q"],
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"],
        ["cvlc", "--play-and-exit", "--intf", "dummy"],
        ["paplay"],
        ["aplay", "-q"],
    ):
        if shutil.which(cmd[0]):
            return cmd
    return None


def play_local(key: str) -> bool:
    """Play a cached warning mp3 on the local speaker in a background thread. Non-blocking."""
    global _current_proc
    path = AUDIO_DIR / f"{key}.mp3"
    if not path.exists():
        return False
    player = _find_player()
    if not player:
        log.debug("Lokal ovoz ijrochisi topilmadi (afplay/mpg123/ffplay)")
        return False
    with _audio_lock:
        if _current_proc is not None and _current_proc.poll() is None:
            return False  # already playing an alert
        try:
            _current_proc = subprocess.Popen(
                [*player, str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception as e:
            log.warning("Lokal ovoz ijro etilmadi: %s", e)
            return False
