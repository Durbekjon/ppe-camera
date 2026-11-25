"""Before a demo: is everything in place? Prints one line per check and changes nothing.

Usage (with the app stopped, so the camera is free):
  .venv/bin/python -m tools.precheck
  .venv/bin/python -m tools.precheck --no-camera     skip opening the cameras
Telegram is checked with getMe (no message is sent). Exit code 1 if anything failed.
"""
import argparse
import shutil
import socket
import sys
import time

from app import config

results = []


def report(level, name, text):
    results.append(level)
    print(f"{ {'ok': '✅', 'warn': '⚠️ ', 'bad': '❌'}[level]} {name}: {text}")


def check_files():
    for name, path in (("Asosiy model", config.MODEL_PATH), ("Skelet modeli", config.POSE_MODEL_PATH)):
        if name == "Skelet modeli" and not config.SKELETON:
            continue
        ok = path and __import__("os").path.isfile(path)
        report("ok" if ok else "bad", name, "bor" if ok else f"topilmadi: {path}")
    from app.privacy import FACE_MODEL
    if config.BLUR_FACES:
        report("ok" if FACE_MODEL.is_file() else "bad", "Yuz modeli", "bor" if FACE_MODEL.is_file() else "topilmadi")
    audio = config.ROOT / "static" / "audio"
    missing = [k for k in ("helmet", "vest", "zone", "entry") if not (audio / f"{k}.mp3").is_file()]
    report("warn" if missing else "ok", "Ovoz fayllari",
           f"yo'q: {', '.join(missing)} (birinchi ishga tushishda internet bilan yaratiladi)" if missing else "4 ta bor")
    demo = __import__("pathlib").Path(config.DEMO_VIDEO)
    report("ok" if demo.is_file() else "warn", "Zaxira demo video", "bor" if demo.is_file() else "yo'q: Demo rejimi ishlamaydi")


def check_users():
    from app import auth, db
    db.init()
    rows = db.query("SELECT role, COUNT(*) AS n FROM users GROUP BY role")
    roles = {r["role"]: r["n"] for r in rows}
    if not roles.get(auth.ADMIN):
        report("bad", "Foydalanuvchilar", "admin yo'q: .venv/bin/python -m tools.create_user NOM --role admin")
    else:
        report("ok", "Foydalanuvchilar", ", ".join(f"{k}: {v}" for k, v in sorted(roles.items())))
    n = db.query("SELECT COUNT(*) AS n FROM incidents")[0]["n"]
    report("ok" if n == 0 else "warn", "Hodisalar bazasi",
           "bo'sh" if n == 0 else f"{n} ta hodisa bor (toza boshlash: tools.archive_data --apply)")
    waiting = db.query("SELECT COUNT(*) AS n FROM outbox")[0]["n"]
    if waiting:
        report("warn", "Telegram navbati", f"{waiting} ta yuborilmagan xabar bor, ilova yoqilganda yuboriladi")


def check_settings():
    leftovers = [k for k, on in (("REQUIRE_VEST", config.REQUIRE_VEST), ("LOCAL_AUDIO", config.LOCAL_AUDIO)) if on]
    if leftovers:
        report("warn", "Sozlamalar", f"yoqilgan: {', '.join(leftovers)}; demoda kerakmi?")
    if config.CAMERAS:
        from app.cameras import parse_cameras
        try:
            report("ok", "Kameralar sozlamasi", ", ".join(n for n, _ in parse_cameras(config.CAMERAS, config.VIDEO_SOURCE)))
        except ValueError as e:
            report("bad", "Kameralar sozlamasi", str(e))
    report("ok" if config.SKELETON else "warn", "Skelet rejimi", "yoqilgan" if config.SKELETON else "o'chirilgan")
    if config.TAMPER_CHECK:
        report("ok", "Kamera to'silishi nazorati", "yoqilgan")


def check_port():
    with socket.socket() as s:
        s.settimeout(0.5)
        busy = s.connect_ex(("127.0.0.1", config.PORT)) == 0
    report("warn" if busy else "ok", f"Port {config.PORT}",
           "band: ilova allaqachon ishlayapti (kamera tekshiruvi o'tkazib yuboriladi)" if busy else "bo'sh")
    return busy


def check_disk():
    free = shutil.disk_usage(config.DATA if config.DATA.exists() else config.ROOT).free / 2**30
    report("ok" if free > 2 else "warn", "Disk", f"{free:.1f} GB bo'sh")


def check_cameras():
    import cv2
    from app.cameras import parse_cameras
    from app.redact import redact
    from app.tamper import view_ok
    try:
        cameras = parse_cameras(config.CAMERAS, config.VIDEO_SOURCE)
    except ValueError:
        return
    for name, source in cameras:
        cap = cv2.VideoCapture(int(source) if source.isdigit() else source,
                               cv2.CAP_FFMPEG if "://" in source else cv2.CAP_ANY)
        frame, start = None, time.monotonic()
        while cap.isOpened() and time.monotonic() - start < 5:
            ok, f = cap.read()
            if ok:
                frame = f  # the first frames of a webcam are often dark; keep the latest
                if time.monotonic() - start > 1.5:
                    break
        cap.release()
        if frame is None:
            report("bad", f"Kamera «{name}»", f"kadr olinmadi ({redact(source) if '://' in source else source})")
        elif not view_ok(frame):
            report("warn", f"Kamera «{name}»", f"ochildi ({frame.shape[1]}x{frame.shape[0]}), lekin rasm juda qorong'i yoki bir xil")
        else:
            report("ok", f"Kamera «{name}»", f"ishlayapti ({frame.shape[1]}x{frame.shape[0]})")


def check_telegram():
    from app import alerts, telegram_bot
    if not alerts.telegram_configured():
        report("warn", "Telegram", "sozlanmagan")
        return
    listener = telegram_bot.ButtonListener()
    me, error = listener._call("getMe")
    if error:
        report("bad", "Telegram", f"bot javob bermadi: {error}")
        return
    hook, _ = listener._call("getWebhookInfo")
    if hook and hook.get("url"):
        report("bad", "Telegram", "botda webhook sozlangan: tugmalar ishlamaydi")
    else:
        report("ok", "Telegram", f"bot @{me.get('username')} javob berdi (xabar yuborilmadi)")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-camera", action="store_true")
    args = parser.parse_args()
    check_files()
    check_users()
    check_settings()
    busy = check_port()
    check_disk()
    if not args.no_camera and not busy:
        check_cameras()
    check_telegram()
    bad, warn = results.count("bad"), results.count("warn")
    print(f"\n{'Tayyor' if not bad else 'Tuzatish kerak'}: {bad} ta xato, {warn} ta ogohlantirish.")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
