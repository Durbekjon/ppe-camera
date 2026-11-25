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

The dashboard needs a login. Create the first user (you are asked for a password, at least 8 characters):

```bash
.venv/bin/python -m tools.create_user NAME --role admin        # can change zone, demo mode, test Telegram
.venv/bin/python -m tools.create_user NAME --role supervisor   # watch only
```

On a fresh clone, run `./run.sh` once first so that `.venv` exists. Running the command again resets a password.
Sessions last 12 hours.

**Access from another computer (HTTPS).** By default the app listens on this computer only. To open it to the
local network, run `tools/make_cert.sh <this computer's IP>`, add the three printed lines to `.env`, restart,
and open `https://<IP>:8000`. The certificate is self-signed, so the browser warns on first use; compare its
fingerprint (`openssl x509 -in data/certs/cert.pem -noout -fingerprint -sha256`) before accepting. Without a
certificate `run.sh` refuses to listen on the network, and the app rejects non-HTTPS network requests.

**Secrets** stay in `.env` (`run.sh` makes it readable by you only). Logs hide stream passwords, URL query strings
and the Telegram token; OpenCV/FFmpeg messages are switched off for that reason (to debug a camera, set
`OPENCV_FFMPEG_LOGLEVEL=32`, which may print the password).

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
| `DEBOUNCE_S` / `COOLDOWN_S` | `1.5` / `15` | Violation must last this long / gap between voice reminders |
| `RESOLVE_S` / `REJOIN_S` | `5` / `10` | Compliance needed to end a violation / longest disappearance after which a worker nearby with a new ID continues the same incident. `COOLDOWN_S` now only spaces voice reminders and repeat zone entries |
| `TELEGRAM_GROUP_S` | `5` | Ordinary alerts within this window share one Telegram message; zone alerts are sent at once |
| `BLUR_FACES` | `1` | Blur faces in saved and Telegram snapshots (plus the head area of people on whom no face was found). The live video is not blurred |
| `RETENTION_DAYS` | `30` | Snapshots older than this are deleted at start-up and hourly; incident rows stay. `0` keeps everything. No raw frames are stored; any future feature that stores them must follow the same two rules |
| `PORT` | `8000` | Dashboard port |

**Phone as camera.** iPhone: with Continuity Camera the phone appears as a webcam (try `VIDEO_SOURCE=1`).
Android: an IP-camera app gives a URL such as `http://192.168.1.50:8080/video`. Phone and laptop must be on the same network.

**Telegram.** Create a bot with @BotFather, send it any message from the supervisor's account, get the
chat id (for example from @userinfobot), put both in `.env`, restart, and press **Telegramni tekshirish** in the dashboard.

## How it works

```
camera/file -> app/video.py (newest frame, auto-reconnect)
            -> app/detector.py (YOLOv8s PPE model, CPU)
            -> app/violations.py (ByteTrack tracking, 1.5 s debounce, one incident per continuing violation, danger zone)
            -> app/alerts.py (snapshot + SQLite + Telegram)   -> dashboard plays the Uzbek voice warning
app/main.py serves the MJPEG stream, the JSON API and static/ (dashboard)
```

- Danger zones (up to 10): **Zona qo'shish**, click corners on the video, set a name, a rule (**Himoya vositasi shart**: a
  worker without gear raises a zone alert; **Hech kim kirmasin**: anyone inside does) and optional working hours
  (computer's local time, may run over midnight), then **Saqlash**. To change a zone, delete it and draw it again. A person is "in the zone" when the
  bottom-centre of their box is inside the polygon. If the box reaches the bottom edge (feet out of view), the centre of the box counts too. Zones are kept in `data/zones.json`; an old `data/zone.json` is converted on first start and left in place.
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

Face detection uses [YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)
(`models/face_yunet_2023mar.onnx`, MIT). Blurring is best-effort: check real snapshots before relying on it.
Snapshots saved before this feature are not blurred (see `tools/blur_snapshots.py`).

## Testing tools

```bash
.venv/bin/python -m pytest tests -q                         # violation logic, zone geometry, alerts (Telegram mocked)
.venv/bin/python -m tools.eval_video path/to/video.mp4      # alerts + raw speed on a file, no server
.venv/bin/python tools/fake_camera.py testdata/stills.mp4   # fake IP camera at http://127.0.0.1:8770/video
```

## Known limitations

See [DEMO.md](DEMO.md).
