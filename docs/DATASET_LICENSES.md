# PPE-104: Datasetlar va manbalar litsenziyalari reyestri

**Ijrochi:** O'tkirbek  
**Sana:** 2026-11-25  
**Holat:** Bajarildi ✅  

Loyiha doirasida ishlatilayotgan barcha tashqi modellar, datasetlar, sinov tasvirlari va resurslarning litsenziya holati quyida to'liq hujjatlashtirildi.

---

## 1. Modellarning og'irliklari (Weights)

| Resurs nomi | Fayl / Manba | E'lon qilingan litsenziya | O'quv ma'lumotlari (Training Data) | Xavf va cheklovlar |
|---|---|---|---|---|
| **YOLOv8s PPE** (Asosiy) | `models/ppe_yolov8s.pt`<br>Manba: [`killuminati1/construction-ppe-yolov8`](https://huggingface.co/killuminati1/construction-ppe-yolov8) | **Apache-2.0** | Roboflow va GitHub ochiq datasetlari asosida | Muallif individual tasvirlar litsenziyasini ko'rsatmagan. Ultralytics talqinida AGPL-3.0 bilan to'qnashuv bo'lishi mumkin. |
| **YOLOv8n PPE** (Alternativ) | `models/ppe_yolov8n_alt.pt`<br>Manba: [`Hansung-Cho/yolov8-ppe-detection`](https://huggingface.co/Hansung-Cho/yolov8-ppe-detection) | **MIT** | Roboflow PPE dataset | Tijoriy va ochiq loyihalar uchun ruxsat berilgan, biroq Ultralytics AGPL talablari inobatga olinishi lozim. |
| **YOLO11n-pose** (Skelet) | `models/yolo11n-pose.pt`<br>Manba: [`ultralytics/assets` v8.4.0](https://github.com/ultralytics/assets/releases/tag/v8.4.0) | **AGPL-3.0** yoki Enterprise ([Ultralytics](https://www.ultralytics.com/license)) | COCO keypoints; shartlari tekshirilmagan | Odamni tasdiqlash va zona tekshiruvi (PPE-007). |
| **YuNet Face Detector** (Maxfiylik) | `models/face_yunet_2023mar.onnx`<br>Manba: [`opencv/opencv_zoo`](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) / Shiqi Yu | **MIT** | Tekshirilmagan | Yuzlarni topish va xiralashtirish (PPE-504). Litsenziya manbasi: model papkasidagi [`LICENSE`](https://github.com/opencv/opencv_zoo/blob/main/models/face_detection_yunet/LICENSE) fayli. |

---

## 2. Dasturiy kutubxonalar va freymvorklar

| Kutubxona | Versiya | Litsenziya | Izoh |
|---|---|---|---|
| `ultralytics` | `>=8.3` | **AGPL-3.0** yoki Enterprise | Demo va ochiq kodli versiya uchun mos. Yopiq tijoriy mahsulot uchun pullik litsenziya talab etiladi. |
| `opencv-python` | `5.x` / `4.x` | **Apache-2.0** | Cheklovlarsiz ishlatiladi. |
| `fastapi` | `>=0.115` | **MIT** | To'liq erkin litsenziya. |
| `uvicorn` | `>=0.30` | **BSD-3-Clause** | To'liq erkin litsenziya. |
| `edge-tts` | `>=6.1` | **LGPL-3.0** | Microsoft Azure TTS norasmiy mijozi. Tijoriy sotuvda o'z ovoz modelimiz yoki rasmiy TTS API zarur. |
| `lap` / `lapx` | `>=0.5` | **BSD-2-Clause** | ByteTrack chiziqli bog'lash uchun, erkin litsenziya. |

---

## 3. Sinov ma'lumotlari (Testdata)

| Fayl | Manba | Litsenziya | Foydalanish maqsadi |
|---|---|---|---|
| `testdata/images/amsterdam_workers_cc0.jpg` | Wikimedia Commons | **CC0 (Public Domain)** | Ochiq havoda 2 ishchining kaska kiyganligini tekshirish |
| `testdata/images/hardhat_worker_pd.jpg` | Public Domain Archive | **Public Domain (CC0)** | Yaqin masofadagi kaskali ishchi aniqligi |
| `testdata/images/metro_shaft_group.jpg` | Wikimedia Commons | CC BY-SA 4.0 *(tasdiqlanmagan: quyidagi izohga qarang)* | Shaxtadagi guruh ishchilari, xira yorug'lik va masofa sinovi |
| `testdata/images/zidane.jpg` | Ultralytics namuna to'plami | Ochiq sinov uchun | Kal boshda soxta signal bermaslikni tekshirish |
| `testdata/images/bus.jpg` | Ultralytics namuna to'plami | Ochiq sinov uchun | Ko'chadagi oddiy kiyimli odamlar va bosh kiyimsiz holatlar |
| `testdata/stills.mp4` | Yuqoridagi tasvirlardan `make_test_video.py` orqali generatsiya qilingan | Loyihaning o'z resursi | Offline demo va avtomatik barqarorlik testlari |

> ⚠️ **`metro_shaft_group.jpg` litsenziyasi aniqlanmagan.**
> Bu yerda CC BY-SA 4.0 deb yozilgan, README esa test rasmlarini CC0 / public domain deb ko'rsatadi. Rasm sahifasining havolasi yo'q, shuning uchun ikkalasi ham tasdiqlanmagan.
> Aniq fayl sahifasi havolasi qo'shilguncha rasmni tashqi relizda ishlatmaslik yoki litsenziyasi aniq rasmga almashtirish kerak.

---

## 4. Ovozli ogohlantirish fayllari

- Fayllar: `static/audio/helmet.mp3`, `static/audio/vest.mp3`, `static/audio/zone.mp3`.
- Generatsiya: `edge-tts` orqali `uz-UZ-SardorNeural` ovozida amalga oshiriladi.
- Kesh: Loyihada generatsiya qilingandan so'ng to'liq offline ishlaydi.

---

## 5. Yangi ma'lumotlar yig'ish qoidalari (Sprint 1 uchun talablar)

1. Har bir olingan yangi rasm yoki video uchun kadr egasining yozma roziligi olinishi shart (`docs/DATA_COLLECTION_CONSENT.md`).
2. Internetdan olinadigan qo'shimcha datasetlar faqat **CC0**, **CC BY** yoki **MIT/Apache** litsenziyalarida bo'lishi tekshiriladi.
3. Notijoriy yoki noaniq litsenziyali datasetlar (masalan, "Non-commercial only" yoki "Research only") o'quv bazasiga kiritilmaydi.
