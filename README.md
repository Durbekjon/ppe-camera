# Xavfsizlik nazorati (Worker Safety Monitor)

A camera watches the workplace, detects workers without a helmet (optionally without a vest) in real time,
warns them out loud in Uzbek, notifies the supervisor on Telegram, and logs every incident.
Runs on a laptop CPU; no GPU needed.

## Start

Requires Python 3.11 (3.10–3.12 should work) and, on first run, internet to install packages (about 1 GB).

```bash
cp .env.example .env    # optional: set camera and Telegram
./run.sh
```

Open http://localhost:8000 and click **Ovozni yoqish** once (browsers block sound until a click).

No camera at hand? Tick **Demo rejimi** in the dashboard, or start with `DEMO_MODE=1 ./run.sh`.
Demo mode plays `data/demo.mp4` in a loop and needs no internet.

## Settings (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `VIDEO_SOURCE` | `0` | Webcam index, stream URL (`http://phone-ip:8080/video`, `rtsp://...`) or a video file |
| `DEMO_MODE` | `0` | `1` starts on the demo video |
| `DEMO_VIDEO` | `data/demo.mp4` | File used by demo mode |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | empty | Supervisor alerts; empty disables them |
| `REQUIRE_VEST` | `0` | `1` also alerts on a missing vest |
| `HELMET_RULE` | `missing` | `missing`: no helmet detected on a person is a violation. `explicit`: only a positively detected bare head |
| `MODEL_PATH` | `models/ppe_yolov8s.pt` | YOLO weights with person / helmet / no-helmet classes |
| `CONF` / `GEAR_CONF` | `0.4` / `0.25` | Minimum confidence for people / for helmets and vests |
| `IMG_SIZE` | `480` | Model input size; `416` is faster, `640` sees small people better |
| `DEBOUNCE_S` / `COOLDOWN_S` | `1.5` / `15` | Violation must last this long / minimum gap between alerts per person |
| `TELEGRAM_GROUP_S` | `5` | Ordinary alerts within this window share one Telegram message; zone alerts are sent at once |
| `PORT` | `8000` | Dashboard port |

**Phone as camera.** iPhone: with Continuity Camera the phone appears as a webcam (try `VIDEO_SOURCE=1`).
Android: an IP-camera app gives a URL such as `http://192.168.1.50:8080/video`. Phone and laptop must be on the same network.

**Telegram.** Create a bot with @BotFather, send it any message from the supervisor's account, get the
chat id (for example from @userinfobot), put both in `.env`, restart, and press **Telegramni tekshirish** in the dashboard.

## How it works

```
camera/file -> app/video.py (newest frame, auto-reconnect)
            -> app/detector.py (YOLOv8s PPE model, CPU)
            -> app/violations.py (ByteTrack tracking, 1.5 s debounce, 15 s cooldown, danger zone)
            -> app/alerts.py (snapshot + SQLite + Telegram)   -> dashboard plays the Uzbek voice warning
app/main.py serves the MJPEG stream, the JSON API and static/ (dashboard)
```

- Danger zone: **Xavfli zonani chizish**, click corners on the video, **Saqlash**. A person is "in the zone" when the
  bottom-centre of their box is inside the polygon. The zone is kept in `data/zone.json`.
- Incidents: `data/incidents.db` (SQLite) and `data/snapshots/`.
- Voice files are generated once with `edge-tts` (voice `uz-UZ-SardorNeural`) into `static/audio/` and reused offline.

## Model and licences

- Weights: [`killuminati1/construction-ppe-yolov8`](https://huggingface.co/killuminati1/construction-ppe-yolov8)
  (`models/ppe_yolov8s.pt`), YOLOv8s, 19 classes including `Hard_hat`, `No-Helmet`, `Vest`, `No-Vest`, `Worker`.
  Published as **Apache-2.0**. The author states it was trained on combined Roboflow/GitHub datasets whose
  individual licences are not listed, and reports mAP50 of about 0.76 on their own validation set (not re-measured here).
- Alternative: `models/ppe_yolov8n_alt.pt` from [`Hansung-Cho/yolov8-ppe-detection`](https://huggingface.co/Hansung-Cho/yolov8-ppe-detection)
  (MIT, YOLOv8n, faster). Use with `MODEL_PATH=models/ppe_yolov8n_alt.pt`.
- The Ultralytics library is **AGPL-3.0**: fine for a demo, but a closed commercial product needs their enterprise licence.
- Test photos in `testdata/images/` are from Wikimedia Commons (CC0 / public domain) and the Ultralytics samples.

## Testing tools

```bash
.venv/bin/python -m pytest tests -q                         # violation logic, zone geometry, alerts (Telegram mocked)
.venv/bin/python -m tools.eval_video path/to/video.mp4      # alerts + raw speed on a file, no server
.venv/bin/python tools/fake_camera.py testdata/stills.mp4   # fake IP camera at http://127.0.0.1:8770/video
```

## Known limitations

See [DEMO.md](DEMO.md).
