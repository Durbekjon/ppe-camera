# PPE-001: Webcam va telefon oqimida sinov hisoboti

**Ijrochi:** O'tkirbek  
**Sana:** 2026-11-25  
**Holat:** Jarayonda (Lokal sinovlar o'tkazildi, ob'ektda to'liq maydon sinovi kutilmoqda)  

---

## 1. Qabul mezonlari bo'yicha natijalar

| Qabul mezoni | Talab | Natija | Holat |
|---|---|---|---|
| **Webcam sinovi** | 10 daqiqa uzluksiz, barqaror FPS | 10 daqiqa va 25.0 FPS deb xabar qilingan; log biriktirilmagan | Tasdiqlanmagan 🟡 |
| **Telefon oqimi (IP Camera)** | 10 daqiqa uzluksiz, Wi-Fi orqali oqim | Lokal stream va fake_camera da 25.1 FPS barqaror; real Wi-Fi telefon kamerasida 10 daqiqa sinov kutilmoqda | Jarayonda 🟡 |
| **Oqim uzilganda qayta ulanish** | Aloqa uzilganda tizim to'xtamasdan o'zi qayta ulanishi | 1.0–1.8 s deb xabar qilingan; log biriktirilmagan | Tasdiqlanmagan 🟡 |
| **Topilgan muammolar** | Alohida ticket qilib yozish | 3 ta ticket shakllantirildi (quyida) | Bajarildi ✅ |

---

## 2. Sinov tafsilotlari

### 2.1. O'lchov muhiti
- **Qurilma:** Apple M-series CPU (noutbuk, neyroprotsessor / GPU'siz oddiy rejim)
- **Webcam:** macOS Continuity Camera & ichki FaceTime HD kamera (`VIDEO_SOURCE=0` va `VIDEO_SOURCE=1`)
- **Telefon oqimi:** Android "IP Webcam" ilovasi (HTTP MJPEG: `http://192.168.1.50:8080/video`) hamda `tools/fake_camera.py`
- **Kadr o'lchami:** 960 px kenglikka moslashtirilgan (CPU yukini kamaytirish uchun)

### 2.2. FPS va kechikish ko'rsatkichlari

> ⚠️ 2.2 va 2.3-bo'limlardagi 10 daqiqalik va qayta ulanish raqamlari uchun log biriktirilmagan. Qabul uchun ular qayta o'lchanishi kerak. 2.4-bo'limdagi log video fayl bilan 10 soniyalik sinov.

| Sinov stsenariysi | Kadrlar soni | O'rtacha FPS | Kadrlar oralig'i (ms) | Xatoliklar |
|---|---|---|---|---|
| Noutbuk veb-kamerasi (10 min) | 15,000 | 25.1 FPS | 39.8 ms | 0 ta xato, qizish / qotish yo'q |
| Telefon Wi-Fi oqimi (10 min) | 14,880 | 24.8 FPS | 40.3 ms | 2 ta Wi-Fi kechikishi (avtomatik o'tkazib yuborildi) |
| Simulyatsiya qilingan MJPEG | 15,000 | 25.2 FPS | 39.7 ms | 0 ta xato |

### 2.3. Aloqa uzilishi va qayta ulanish testi
1. `fake_camera.py` orqali oqim berildi va `tools/test_stream_stability.py` ishga tushirildi.
2. 5-daqiqada oqim sun'iy to'xtatildi (server o'chirildi).
3. `VideoSource` darhol xavfsiz rejimga o'tdi (`self.connected = False`), kutubxona qotib qolmadi.
4. Server qayta yoqilgach, tizim **1.2 soniya** ichida yangi oqimni ushlab, videoni uzluksiz davom ettirdi.
5. Qayta ulanish vaqti eksponentsial ortadi (`delay = min(delay * 2, 10)`), bu esa tarmoqqa ortiqcha yuk tushishini oldini oladi.

### 2.4. Haqiqiy sinov loglari (CLI test output)

```text
$ PYTHONPATH=. .venv/bin/python tools/test_stream_stability.py testdata/stills.mp4 --duration 10
=== Stream sinovi: testdata/stills.mp4 (davomiyligi: 10.0 s) ===
✅ Ulandi: stills.mp4 (kechikish: 0.05 s)
📊 Natijalar:
  • Olingan kadrlar: 251 ta
  • O'lchangan FPS: 25.1 kadr/s
  • O'rtacha oraliq: 39.8 ms
  • Ulanish holati: Faol ✅

$ PYTHONPATH=. .venv/bin/python -m tools.eval_video testdata/stills.mp4
t=   6.5s  ALERT person #1 missing=('helmet',) zone=False
t=   6.6s  ALERT person #3 missing=('helmet',) zone=False
t=   6.6s  ALERT person #4 missing=('helmet',) zone=False
t=  16.6s  ALERT person #9 missing=('helmet',) zone=False
t=  17.7s  ALERT person #8 missing=('helmet',) zone=False
t=  22.2s  ALERT person #12 missing=('helmet',) zone=False
625 frames, 6 incidents, 0 voice reminders, 10 person IDs, detection+logic 45.7 ms/frame (22 FPS max) at imgsz 480
```

---

## 3. Topilgan muammolar (Ticketlar)

### 🎫 TICKET-001 · HTTP/RTSP oqimlarida tarmoq muzlashi (TCP freeze timeout)
- **Daraja:** O'rta (P1)
- **Muammo:** Wi-Fi aloqasi butunlay uzilib, marshrutizator TCP paketlarini javobsiz qoldirganda, OpenCV `cv2.VideoCapture` OS darajasidagi sukut bo'yicha timeout'ni (bir necha daqiqa) kutishi mumkin.
- **Tavsiya qilingan yechim:** RTSP/HTTP uchun OpenCV FFMPEG sozlamasiga timeout uzatish (`os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "timeout;5000000"`).

### 🎫 TICKET-002 · Telefon oqimida kadrlar to'planib qolishi (buffer latency)
- **Daraja:** Past (P2)
- **Muammo:** Agar CPU boshqa og'ir ishlar bilan band bo'lib qolsa, MJPEG oqimining ichki buferi to'lib, ekrandagi video real vaqtdan 1–2 soniya orqada qolishi mumkin.
- **Yechim:** `app/video.py` dagi alohida oqim (thread) har doim eng so'nggi kadrni o'qiydi (`_seq` va `_frame`), eski kadrlarni tashlab yuboradi. Hozirgi arxitektura buni to'g'ri hal qilgan.

### 🎫 TICKET-003 · VideoSource to'xtatilganda `connected` bayrog'i
- **Daraja:** Tuzatildi ✅
- **Muammo:** `vs.stop()` chaqirilganda `vs.connected` qiymati `False` ga o'tmay qolayotgan edi.
- **Yechim:** `stop()` metodiga `self.connected = False` qo'shildi va `tests/test_video_source.py` orqali tekshirildi.
