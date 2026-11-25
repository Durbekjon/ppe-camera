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
| `CAMERAS` | empty | Up to 4 cameras: `Kirish=0;Sex=rtsp://...`. Replaces `VIDEO_SOURCE`; see **Several cameras** |
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
| `TELEGRAM_BUTTONS` | `1` | **Ko'rildi** and **Noto'g'ri signal** buttons under incident alerts (an album is followed by a message with the buttons). Presses are fetched by polling, so no public address is needed; only the chat in `TELEGRAM_CHAT_ID` is accepted, and **in a group every member can press them**. Only one program may poll a bot, and it must have no webhook |
| `TELEGRAM_RETRY_HOURS` | `24` | An alert Telegram has not accepted is retried (pauses grow from 10 s to 15 min) for this long, also after a restart. After a timeout it may arrive twice. The **Telegramni tekshirish** test message is not retried |
| `TELEGRAM_GROUP_S` | `5` | Ordinary alerts within this window share one Telegram message; zone alerts are sent at once |
| `BLUR_FACES` | `1` | Blur faces in saved and Telegram snapshots (plus the head area of people on whom no face was found). The live video is not blurred |
| `RETENTION_DAYS` | `30` | Snapshots older than this are deleted at start-up and hourly; incident rows stay. `0` keeps everything. Stored raw frames and exports follow the same two rules |
| `SAVE_RAW` | `1` | Keep a clean, blurred frame per incident (`data/raw/`) so marked false alarms can be exported; same retention as snapshots |
| `LOCAL_AUDIO` | `0` | Play voice warnings on the speaker of the computer running the app (needs `afplay` on macOS, or `mpg123` / `ffplay`; `paplay` only if it can read MP3). A zone warning interrupts an ordinary one. An open dashboard with sound on will also play them. Not tested on Linux or in Docker (a container needs access to the audio device) |
| `SKELETON` / `POSE_IMG_SIZE` | `1` / `480` | Skeleton model (`models/yolo11n-pose.pt`, Ultralytics, AGPL-3.0): see **Skeletons**. `0` uses boxes only |
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
- Test photos in `testdata/images/` are from Wikimedia Commons (CC0 / public domain; the licence of
  `metro_shaft_group.jpg` is unconfirmed, see [docs/DATASET_LICENSES.md](docs/DATASET_LICENSES.md)) and the Ultralytics samples.

Face detection uses [YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)
(`models/face_yunet_2023mar.onnx`, MIT). Blurring is best-effort: check real snapshots before relying on it.
Snapshots saved before this feature are not blurred (see `tools/blur_snapshots.py`).

## Several cameras

Set `CAMERAS` in `.env` and restart. The dashboard shows a small live tile per camera; click one to see it large and
edit its zones. The header shows the most serious state of any camera, and voice warnings and incidents from every
camera arrive. **Demo rejimi** applies to the selected camera. The name identifies a camera: renaming it leaves its
zones and old incidents under the old name. The daily report counts all cameras together. A `;` cannot appear in a
source URL. All cameras share one model, so speed per camera drops as cameras are added; measure on your computer
with `.venv/bin/python -m tools.measure_fps 2`.

## False alarms

Press **Noto'g'ri signal** on an incident (admin or supervisor; it can be undone). Marked incidents leave the daily
report. `.venv/bin/python -m tools.export_false_alarms` copies their clean frames and the model's detections to
`data/exports/` (export before the retention period ends). Faces are blurred; where no face was found the head
area is blurred too, which makes such frames less useful for helmet training.

## Clean start before a demo

Stop the app, then:
```bash
.venv/bin/python -m tools.archive_data            # shows what would move; changes nothing
.venv/bin/python -m tools.archive_data --apply    # incidents and pictures move to data/archive/<time>/
.venv/bin/python -m tools.archive_data --restore <time>
```
Users, zones and settings stay, and incident numbers start from 1 again. Nothing is deleted, but archived
pictures still expire after `RETENTION_DAYS`. Unsent Telegram alerts are set aside and not sent later.

## Skeletons

With `SKELETON=1` a second model finds 17 body points.
- **Only people are judged.** A box the main model calls a person is ignored until a skeleton (3 or more
  trusted points) has been seen on it. After that it stays a person even if the skeleton drops out. A real
  worker on whom no skeleton is ever found (far away, mostly hidden) is **missed**.
- **Zones:** a zone alert is raised if any joint or bone is inside the polygon (fingers and toes are not part of
  the model). Without a skeleton in a frame, the feet-point rule is used. The check is made in the picture:
  an arm that only passes in front of a zone, nearer to the camera, also counts. Draw zones tightly around the
  hazard and place the camera so that depth overlap is small.

## Model evaluation

```bash
.venv/bin/python -m tools.evaluate datasets/site/data.yaml --out docs/EVALUATION.md
```

The test set is in YOLO format (`images/<split>/`, `labels/<split>/`, class names in `data.yaml` such as
`person`, `helmet`, `no_helmet`). It compares both bundled models: precision and recall at the app's
thresholds, AP50 and mAP50, and how often a labelled bare head or cap is taken for a helmet. AP uses all-point
interpolation, so it can differ slightly from other tools. Keep datasets in `datasets/` (ignored by git).

## Testing tools

```bash
.venv/bin/python -m pytest tests -q                         # violation logic, zone geometry, alerts (Telegram mocked)
.venv/bin/python -m tools.eval_video path/to/video.mp4      # alerts + raw speed on a file, no server
.venv/bin/python tools/fake_camera.py testdata/stills.mp4   # fake IP camera at http://127.0.0.1:8770/video
```

## Known limitations

See [DEMO.md](DEMO.md).
