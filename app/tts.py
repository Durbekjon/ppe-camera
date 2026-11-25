"""Uzbek voice warnings, generated once with edge-tts and cached in static/audio (works offline afterwards)."""
import asyncio
import logging

from . import config

log = logging.getLogger("tts")

VOICE = "uz-UZ-SardorNeural"
AUDIO_DIR = config.ROOT / "static" / "audio"
PHRASES = {
    "helmet": "Kaskangizni kiying!",
    "vest": "Himoya jiletingizni kiying!",
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
