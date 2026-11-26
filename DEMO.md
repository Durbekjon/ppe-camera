# 3 daqiqalik demo

Asosiy ssenariy **bitta webcam, bitta kaska va nazoratchi telefoni (Telegram)** bilan o'tadi.

## Bir kun oldin: sinov mashqi

Quyidagilarni demo xonasida, o'sha yorug'lik va masofada bir marta o'tkazing. Birortasi ishlamasa, o'sha qismni ssenariydan olib tashlang.

- [ ] Kaska bilan signal chiqmaydi, kaskasiz chiqadi.
- [ ] Turadigan joyingizdan, yon tomonga burilganda ham tizim sizni yo'qotmaydi (skelet chiziladi).
- [ ] Kaskasiz holda faqat qo'lni zonaga kiritganda ham signal chiqadi.
- [ ] Gul, ilingan kiyim, plakat va ekrandagi odamlarga ramka chiqmaydi.
- [ ] Ovoz eshitiladi.
- [ ] Telegram xabari keladi, **Ko'rildi** va **Noto'g'ri signal** tugmalari dashboard'ni o'zgartiradi.
- [ ] Excel fayli yuklanadi va ochiladi.
- [ ] Dashboard ochiq holda `Ctrl+C` ilovani bir necha soniyada to'xtatadi.

> Telegram tugmalari, "Tizim holati" kartasining haqiqiy Telegram bilan ishlashi va skeletning haqiqiy kameradagi xatti-harakati testlar yoki namunalarda tekshirilgan. Haqiqiy sharoitdagi tasdig'i shu mashqda olinadi.

## Demodan 10 daqiqa oldin

1. Noutbukni quvvatga ulang, ovozini balandlating, uyqu rejimini o'chiring. Internetni tekshiring (Telegram uchun kerak).
2. Kameradan foydalanayotgan boshqa dasturlarni (Zoom, Meet, FaceTime) yoping.
3. `.env` ni tekshiring: sinovdan qolgan `CAMERAS`, `REQUIRE_VEST`, `LOCAL_AUDIO` qatorlari kerak bo'lmasa, o'chiring. Telefondan dashboard ochilmasa, `HOST`, `TLS_CERT`, `TLS_KEY` ham kerak emas.
4. Ilovani to'xtatib, bo'sh hisobotdan boshlang (hech narsa o'chirilmaydi, [README](README.md)):
   ```bash
   .venv/bin/python -m tools.archive_data           # nima ko'chishini ko'rsatadi
   .venv/bin/python -m tools.archive_data --apply
   ./run.sh
   ```
   Buni **mashqdan keyin** qiling, shunda mashq hodisalari hisobotda qolmaydi.
5. http://localhost:8000 ga **admin** bo'lib kiring (`HOST`/TLS yoqilgan bo'lsa, `https://`). Tepadagi **🔊 Ovozni yoqish** ni bosing, so'ng 3D xaritada kamera binosini bosing: jonli video shundan keyin ochiladi.
6. **Zona qo'shish:** polda belgilangan joyni chizing, qoida **Himoya vositasi shart**, ish vaqtini bo'sh qoldiring, **Saqlash**. Zonani xavfli obyekt atrofiga zich chizing va siz oddiy turadigan joyni unga kiritmang.
7. **Telegramni tekshirish** ni bosing va xabar telefonga kelganini ko'ring (bu sinov xabari hisobotga tushmaydi). Bundan keyin demo boshlanguncha kamera oldiga kaskasiz o'tmang: har bir tasdiqlangan buzilish hisobotga yoziladi.
8. Kamera oldida oyoqlaringiz va pol ko'rinadigan joyni belgilang (taxminan 2–3 m).

## Ssenariy

| Vaqt | Harakat | Gap |
|---|---|---|
| 0:00–0:20 | 3D xarita, binoni bosib jonli videoni oching, holat **Xavfsiz**. | "Kaska kiyilmaganini nazoratchi hamma joyda ko'rib turolmaydi. Bizning tizim oddiy kamera va noutbukda, GPU'siz ishlaydi." |
| 0:20–0:40 | **Kaska bilan** kadrga kiring. Yashil ramka va skelet. | "Tizim odamni skeleti bo'yicha tasdiqlaydi va kaskasini tekshiradi." |
| 0:40–1:10 | **Kaskani yeching.** Taxminan 1,5 soniyadan keyin qizil ramka va "Kaskangizni kiying!". | "Qisqa tasodif signal bermaydi. Tasdiqlangach, ishchining o'zi o'zbek tilida ogohlantiriladi." |
| 1:10–1:40 | Telefonni ko'rsating: surat, vaqt, tugmalar. **Ko'rildi** ni bosing va dashboard'da holat o'zgarganini ko'rsating. | "Nazoratchi Telegram'dan javob beradi. Saqlangan suratda yuz xiralashtiriladi. Xato signal bo'lsa, bitta tugma bilan hisobotdan chiqadi." |
| 1:40–2:20 | Kaskasiz holda oyoqni tashqarida qoldirib, **qo'lingizni zonaga** uzating. Sirena va "Xavfli zona!". | "Tizim faqat oyoqni emas, qo'l va tana bo'g'imlarini ham zonada tekshiradi." |
| 2:20–2:45 | Kaskani kiying. Pastga tushing: kunlik hisobot, trend, **Excel (.xlsx)**. | "Rahbar qachon va qancha buzilish bo'lganini ko'radi va Excel'ga yuklaydi." |
| 2:45–3:00 | **Tizim holati** kartasi. | "Telegram yetib bormasa, panelda ko'rinadi va xabar navbatda qayta yuboriladi. Rahmat!" |

**Eslab qoling:**
- Buzilish davom etsa, **bitta hodisa** yoziladi, ovoz taxminan har 15 soniyada takrorlanadi.
- Yangi hodisa uchun kaskani kamida 5 soniya kiyib turing yoki 10 soniyadan uzoq kadrdan chiqing.
- Oddiy Telegram xabari 5 soniyagacha yig'iladi; zona xabari kutmaydi.
- Zonaga qayta kirish yangi hodisa bo'lishi uchun kamida 15 soniya o'tsin.

## Ixtiyoriy: ikkinchi kamera

Faqat mashqdan o'tgan bo'lsa. `.env` ga `CAMERAS=Kamera 1=0;Sex=<telefon oqimi manzili>` yozing (birinchi nom o'zgarmasin, zonalar shunga bog'langan). Panelda ikkita kichik surat chiqadi. Skelet bilan, Apple M5 Pro'da demo video bilan har kamerada: 1 kamera 30 FPS, 2 kamera 21 FPS, 3 kamera 15 FPS. Haqiqiy kameralar va boshqa noutbukda boshqacha bo'lishi mumkin.

## Biror narsa ishlamay qolsa

| Muammo | Nima qilish |
|---|---|
| Kamera ochilmayapti | macOS **Privacy & Security → Camera** da terminalga ruxsat bering; boshqa dasturlarni yoping; `VIDEO_SOURCE=1` ni sinang |
| Odamga ramka chiqmayapti | Yaqinroq turing, yelka va qo'llar ko'rinsin. Baribir bo'lmasa, `.env` ga `SKELETON=0` qo'shib qayta ishga tushiring (qo'l bo'yicha zona qismini aytmang) |
| Ovoz yo'q | **Ovozni yoqish** tugmasini bosing; sahifa yangilansa, qayta bosing |
| Telegram kelmayapti | **Tizim holati** kartasini ko'rsating: xabar navbatda va qayta yuboriladi. Dashboard'dagi hodisalar bilan davom eting |
| Kaska "yo'q" deb chiqyapti | Yorug'likni yaxshilang, bosh to'liq ko'rinsin |
| Kamera butunlay ishlamadi | **Demo rejimi** ni yoqing (`data/demo.mp4`; bu fayl faqat sizning kompyuteringizda). Unda real ustaxona yozuvi bor: **ko'rsatishga ishchilarning ruxsati bo'lsagina** ishlating. Video ichida kaskali ishchi yo'q. Ruxsat bo'lmasa, mashqda yozib olingan o'z ekran videongizni tayyorlab qo'ying |

## Ko'p so'raladigan savollar

- **Aniqligi qancha?** Qo'lda belgilangan test to'plamida hali o'lchanmagan. Baholash skripti tayyor (`tools/evaluate.py`), keyingi qadam obyektdan ruxsat bilan kadr yig'ish.
- **GPU kerakmi?** Yo'q, noutbuk CPU'sida ishlaydi.
- **Maxfiylik?** Saqlanadigan va Telegram'ga ketadigan suratlarda yuz xiralashtiriladi (kafolatli emas), suratlar 30 kundan keyin o'chadi, panel login bilan. Jonli video xiralashtirilmaydi.
- **Sanoatda ishlatsa bo'ladimi?** Hozir prototip. Obyektda pilot, aniqlik o'lchovi va litsenziya qarori kerak. U sertifikatlangan xavfsizlik uskunasining o'rnini bosmaydi.

## Ma'lum cheklovlar

1. **Aniqlik umumiy o'lchanmagan.** Sinovlar kichik namunalar va uy sharoitidagi tekshiruvlar.
2. **Kepka, kapyushon, g'ayrioddiy rang, kuchli orqa yorug'lik** xato natija berishi mumkin.
3. **Skeleti hech topilmagan odam baholanmaydi** (uzoqda yoki ko'p qismi to'silgan). Juda kichik odamlar (kadr balandligining 15% idan past) ham.
4. **Odam bo'lmagan narsa** baribir odam deb olinishi mumkin; skelet buni kamaytirishga mo'ljallangan, lekin faqat namunalarda tekshirilgan.
5. **Zona rasmda tekshiriladi:** zona oldidan o'tgan qo'l ham signal beradi. Barmoq va oyoq uchi skeletda yo'q.
6. **Kuzatuv uzilishi** mumkin: takror hodisa yoki yaqinda kelgan boshqa odamning alohida yozilmasligi.
7. **Kamera tik tepadan** qarasa, sinalmagan.
8. **Telegram** uchun internet kerak; timeout'dan keyin xabar ikki marta kelishi mumkin.
9. **Linux va Docker** o'rnatilishi to'liq sinalmagan.
10. **Litsenziya:** Ultralytics kutubxonasi va skelet modeli AGPL-3.0; asosiy modelning o'quv ma'lumotlari litsenziyasi to'liq hujjatlashtirilmagan ([docs/LICENSE_DECISION.md](docs/LICENSE_DECISION.md)).
