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
- Noutbuk CPU'sida tezlik o'lchanmagan, avval sinash kerak.
- Tayyor og'irliklar va o'quv dataseti litsenziyasi ham alohida tekshiriladi.

## Taklif
- **Hozir (demo, o'quv loyiha):** A. Repo allaqachon public. `LICENSE` fayliga AGPL-3.0 matni qo'shiladi va README yangilanadi.
- **Tijoriy mahsulot rejalansa:** PPE-201 dan oldin C ni 1–2 kunlik sinov bilan tekshirish (CPU tezligi va aniqlik). Yetarli bo'lmasa, B. Model hali qayta o'qitilmagani uchun almashtirishning eng qulay vaqti shu.
- Ikkala holatda ham: o'z datasetimizni litsenziyasi aniq ma'lumotlardan yig'ish (PPE-101, PPE-104).

Eslatma: C tanlansa, PPE-201 bahosi (8 SP) qayta ko'riladi.

## Holat (2026-11-25)
Loyiha egasi: **tijoriy mahsulot bo'lish ehtimoli bor.** Shuning uchun yuqoridagi taklifning "tijoriy mahsulot rejalansa" yo'li dolzarb:
- [ ] PPE-201 (qayta o'qitish) dan oldin C ni sinash: CPU tezligi va belgilangan test to'plamida aniqlik (`tools/evaluate.py`; model boshqa kutubxonada bo'lsa, skriptdagi `predict` moslanadi).
- [ ] Nomzod modelning kod, og'irlik va o'quv ma'lumotlari litsenziyasini o'z manbasidan tekshirish.
- [ ] C yetarli bo'lmasa, Ultralytics'dan Enterprise narxi va shartlarini so'rash.
- [ ] Tijoriy sotuvdan oldin yurist ko'rigi.

A, B yoki C hali tanlanmagan.

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
