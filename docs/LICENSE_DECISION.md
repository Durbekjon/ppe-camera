# PPE-501: Litsenziya qarori (QORALAMA, qaror hali qabul qilinmagan)

Sana: 2026-11-25. Bu yuridik maslahat emas. Tijoriy sotuvdan oldin yurist tekshirishi kerak.

## Hozirgi holat
| Qism | Litsenziya | Izoh |
|---|---|---|
| Ultralytics kutubxonasi (aniqlash va ByteTrack) | AGPL-3.0 yoki pullik Enterprise | Ultralytics'ga ko'ra uning o'qitish kodi bilan olingan modellar ham sukut bo'yicha AGPL-3.0 |
| `ppe_yolov8s.pt` (asosiy model) | Muallif Apache-2.0 deb e'lon qilgan | YOLOv8 asosida, shuning uchun Ultralytics talqinida AGPL-3.0 ta'sir qilishi mumkin. O'quv ma'lumotlari litsenziyasi ko'rsatilmagan |
| `ppe_yolov8n_alt.pt` | Muallif MIT deb e'lon qilgan | YOLOv8 asosida, yuqoridagi xavf bunga ham tegishli |
| Ovoz fayllari (`edge-tts`) | Tekshirilmagan | Tijoriy foydalanish shartlarini alohida tekshirish kerak |

## Variantlar
**A. AGPL-3.0 bilan ochiq loyiha.** Litsenziya to'lovi yo'q. Butun loyihani AGPL-3.0 shartlarida ochish kerak. Yopiq mahsulot sotishga mos emas.

**B. Ultralytics Enterprise litsenziyasi.** Kod o'zgarmaydi, loyiha yopiq bo'lishi mumkin. Pullik; narx va shartlarni Ultralytics'dan so'rash kerak. Modelning o'quv ma'lumotlari masalasini hal qilmaydi.

**C. Ruxsat beruvchi litsenziyali modelga o'tish** (YOLOX, RT-DETR, D-FINE yoki RF-DETR Nano–Large: manbalarga ko'ra Apache-2.0).
- `app/detector.py` qayta yoziladi va `app/tracker.py` dagi Ultralytics ByteTrack almashtiriladi.
- Yangi modelni o'z ma'lumotimizda o'qitish kerak. Mavjud YOLOv8 og'irliklarini ko'chirib bo'lmaydi.
- CPU tezligi: YOLOX uchun dastlabki o'lchov quyida; boshqa nomzodlar o'lchanmagan.
- Tayyor og'irliklar va o'quv dataseti litsenziyasi ham alohida tekshiriladi.

## Taklif
- **Hozir (demo, o'quv loyiha):** A. Repo allaqachon public. `LICENSE` fayliga AGPL-3.0 matni qo'shiladi va README yangilanadi.
- **Tijoriy mahsulot rejalansa:** PPE-201 dan oldin C ni 1–2 kunlik sinov bilan tekshirish (CPU tezligi va aniqlik). Yetarli bo'lmasa, B. Model hali qayta o'qitilmagani uchun almashtirishning eng qulay vaqti shu.
- Ikkala holatda ham: o'z datasetimizni litsenziyasi aniq ma'lumotlardan yig'ish (PPE-101, PPE-104).

Eslatma: C tanlansa, PPE-201 bahosi (8 SP) qayta ko'riladi.

## Holat (2026-11-25)
Loyiha egasi: **tijoriy mahsulot bo'lish ehtimoli bor.** Shuning uchun yuqoridagi taklifning "tijoriy mahsulot rejalansa" yo'li dolzarb:
- [ ] PPE-201 (qayta o'qitish) dan oldin C ni sinash: CPU tezligi (dastlabki o'lchov quyida) va belgilangan test to'plamida aniqlik (`tools/evaluate.py`; model boshqa kutubxonada bo'lsa, skriptdagi `predict` moslanadi).
- [ ] Nomzod modelning kod, og'irlik va o'quv ma'lumotlari litsenziyasini o'z manbasidan tekshirish.
- [ ] C yetarli bo'lmasa, Ultralytics'dan Enterprise narxi va shartlarini so'rash.
- [ ] Tijoriy sotuvdan oldin yurist ko'rigi.

A, B yoki C hali tanlanmagan.

## C varianti: YOLOX tezlik sinovi (2026-11-25)

**Litsenziya:** [YOLOX repozitoriysining LICENSE fayli](https://github.com/Megvii-BaseDetection/YOLOX/blob/main/LICENSE) Apache-2.0 (o'qildi). Sinovda rasmiy `0.1.1rc0` relizidagi ONNX og'irliklari ishlatildi, repoga qo'shilmadi. Og'irliklar COCO'da o'qitilgan; og'irliklar va COCO rasmlarining tijoriy foydalanish shartlari **tekshirilmagan**.

**Sharoit:** Apple M5 Pro, CPU, OpenCV 5.1.0, `data/demo.mp4` dan 240 kadr (har 15-kadr), CONF=0.4. Ikki marta o'lchandi.
```bash
.venv/bin/python -m tools.benchmark_yolox data/demo.mp4 yolox_nano.onnx yolox_tiny.onnx yolox_s.onnx
```

| Model (kirish o'lchami) | Median, ms (1- / 2-o'lchov) | Topilgan odam ramkalari | Joriy model topgan 268 tadan mos kelgani | Qo'shimcha ramka |
|---|---|---|---|---|
| joriy `ppe_yolov8s` (480) | 19.2 / 18.0 | 268 | — | — |
| YOLOX-Nano (416) | 15.4 / 15.7 | 305 | 226 (84%) | 79 |
| YOLOX-Tiny (416) | 59.2 / 59.9 | 343 | 229 (85%) | 114 |
| YOLOX-S (640) | 244.1 / 243.1 | 328 | 228 (85%) | 100 |

**Bu natija nimani bildiradi va nimani bildirmaydi:**
- Mos kelish **aniqlik emas**: ikkala model javobi solishtirilgan, qo'lda belgilangan to'g'ri javob yo'q. Qo'shimcha ramkalar haqiqiy odam yoki xato ekani tekshirilmagan.
- COCO og'irliklarida **kaska sinflari yo'q**. Kaskani aniqlash sifati faqat o'z ma'lumotimizda o'qitgandan keyin o'lchanadi.
- Vaqtlar turli ijrochilarda: joriy model Ultralytics/PyTorch, YOLOX esa OpenCV DNN orqali (to'liq `detect` chaqiruvi). ONNX Runtime bilan YOLOX o'lchanmagan.
- Shu sharoitda bitta kamera uchun Nano joriy modeldan tez; Tiny taxminan 17 FPS chegarasida (bir nechta kameraga zaxira yo'q); S juda sekin.

**Dastlabki xulosa:** keyingi sinov uchun asosiy nomzod YOLOX-Nano (Tiny aniqroq bo'lishi mumkin, lekin buni belgilangan ma'lumotsiz bilib bo'lmaydi). C hali tanlanmagan.

**C ga o'tish uchun qolgan ishlar:** kaska sinflari bilan o'qitish (belgilangan kadrlar va GPU), `tools/evaluate.py` ni YOLOX ga moslab solishtirish, hamda Ultralytics'ga bog'liq qolgan qismlarni almashtirish: `app/detector.py`, `app/tracker.py` (ByteTrack), `tools/evaluate.py`. Hozirgi YOLOv8 og'irliklari repodan olib tashlanadi.

## Qo'shimcha bog'liqlik: skelet modeli (PPE-007)
`models/yolo11n-pose.pt` ham Ultralytics modeli (AGPL-3.0 yoki Enterprise). C variantiga o'tilsa, uni ham ruxsat beruvchi litsenziyali skelet modeli bilan almashtirish kerak (nomzodlar tekshirilmagan). `SKELETON=0` uni o'chiradi, lekin Ultralytics kutubxonasiga bog'liqlik qoladi.

## Qaror
- [ ] A  - [ ] B  - [ ] C
- Kim va qachon:
- Sabab:

## Manbalar
- https://www.ultralytics.com/license
- https://ultralytics.com/legal/terms-of-service
- https://roboflow.com/model-licenses/rf-detr
- https://pypi.org/project/libreyolo/
- https://playground.roboflow.com/models/compare/rt-detr-vs-yolox

Muqobil modellar haqidagi ma'lumot qidiruv natijalari xulosasidan olingan. Har birining o'z repozitoriysidagi litsenziyasi hali tekshirilmagan.
