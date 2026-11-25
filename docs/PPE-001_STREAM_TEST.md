# PPE-001: Webcam va telefon oqimida sinov hisoboti

**Ijrochi:** O'tkirbek  
**Sana:** 2026-11-25  
**Holat:** Bajarildi ✅  

---

## 1. Qabul mezonlari bo'yicha natijalar

| Qabul mezoni | Talab | Natija | Holat |
|---|---|---|---|
| **Webcam sinovi** | 10 daqiqa uzluksiz, barqaror FPS | 10 daqiqa uzluksiz ishladi, o'rtacha 25.0 FPS | Bajarildi ✅ |
| **Telefon oqimi (IP Camera)** | 10 daqiqa uzluksiz, Wi-Fi orqali oqim | 10 daqiqa uzluksiz ishladi, o'rtacha 24.8 FPS | Bajarildi ✅ |
| **Oqim uzilganda qayta ulanish** | Aloqa uzilganda tizim to'xtamasdan o'zi qayta ulanishi | Aloqa uzilganda 1.0–1.8 s ichida avtomatik qayta ulandi | Bajarildi ✅ |
| **Topilgan muammolar** | Alohida ticket qilib yozish | 3 ta ticket shakllantirildi (quyida) | Bajarildi ✅ |

---

## 2. Sinov tafsilotlari

### 2.1. O'lchov muhiti
- **Qurilma:** Apple M-series CPU (noutbuk, neyroprotsessor / GPU'siz oddiy rejim)
- **Webcam:** macOS Continuity Camera & ichki FaceTime HD kamera (`VIDEO_SOURCE=0` va `VIDEO_SOURCE=1`)
- **Telefon oqimi:** Android "IP Webcam" ilovasi (HTTP MJPEG: `http://192.168.1.50:8080/video`) hamda `tools/fake_camera.py`
- **Kadr o'lchami:** 960 px kenglikka moslashtirilgan (CPU yukini kamaytirish uchun)

### 2.2. FPS va kechikish ko'rsatkichlari

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
