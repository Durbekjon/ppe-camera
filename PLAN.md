# Xavfsizlik nazorati: rivojlanish rejasi

**Jamoa:** Durbek (murakkab va muhim vazifalar), O'tkirbek (yengilroq vazifalar).

**Muddat:** Sprint 0 — 2 kun, Sprint 1–3 — 2 haftadan (jami taxminan 6,5 hafta). Sig'im: har bir kishiga sprintda taxminan 16 SP. Baholar taxminiy.

**Belgilar:** SP — story point (1 ≈ yarim kun, 2 ≈ 1 kun, 3 ≈ 2 kun, 5 ≈ 3–4 kun, 8 ≈ 1 hafta). P0 — majburiy, P1 — muhim, P2 — vaqt qolsa.

| Sprint | Durbek | O'tkirbek |
|---|---|---|
| Sprint 0: Demoga tayyorlik (2 kun) | PPE-002, PPE-004 (4 SP) | PPE-001, PPE-003 (4 SP) |
| Sprint 1: Ma'lumot, zonalar, kirish himoyasi (2 hafta) | PPE-501, PPE-502, PPE-503, PPE-301 (15 SP) | PPE-101, PPE-102, PPE-104, PPE-303 (14 SP) |
| Sprint 2: Model, maxfiylik, o'rnatish (2 hafta) | PPE-103, PPE-201, PPE-504 (16 SP) | PPE-203, PPE-302, PPE-401, PPE-402, PPE-601, PPE-602 (16 SP) |
| Sprint 3: Masshtab va pilot (2 hafta) | PPE-202, PPE-603 (13 SP) | PPE-304, PPE-404, PPE-604, PPE-605 (15 SP) |
| Backlog (vaqt qolsa) | PPE-403 (5 SP) | — |

---

## Sprint 0: Demoga tayyorlik (2 kun)

### PPE-002 · Haqiqiy Telegram xabari · P0 · 1 SP · Durbek
Qabul mezonlari:
- Sinov xabari va suratli hodisa xabari nazoratchi telefoniga keladi.
- Token log va repoda ko'rinmaydi.

### PPE-004 · Takroriy signallarni kamaytirish · P0 · 3 SP · Durbek
ByteTrack'ni sinash va bir vaqtdagi buzilishlarni bitta Telegram xabariga jamlash. Bog'liqlik: yo'q.

Qabul mezonlari:
- `data/demo.mp4` da ID va signallar soni o'zgarishdan oldin va keyin o'lchanadi, ikkalasi ham kamayadi.
- 5 soniya ichidagi bir nechta buzilish bitta xabar bo'lib keladi, har bir hodisa bazaga alohida yoziladi.
- Xavfli zona signali kechiktirilmaydi.
- Mavjud testlar o'tadi.

### PPE-001 · Webcam va telefon oqimida sinov · P0 · 2 SP · O'tkirbek
Qabul mezonlari:
- Webcam va telefon oqimining har birida 10 daqiqa uzluksiz ishlaydi, FPS yozib olinadi.
- Oqim uzilganda tizim o'zi qayta ulanadi.
- Topilgan muammolar alohida ticket qilinadi.

### PPE-003 · Kaskali ishchi bilan sinov · P0 · 2 SP · O'tkirbek
Qabul mezonlari:
- Demo xonasida turli yorug'lik va masofada kaska bilan hamda kaskasiz sinaladi.
- Soxta va o'tkazib yuborilgan signallar sanab yoziladi.
- Zarur bo'lsa `CONF`, `GEAR_CONF`, `IMG_SIZE` sozlanadi.

---

## Sprint 1: Ma'lumot, zonalar, kirish himoyasi (2 hafta)

### PPE-501 · Litsenziya qarori · P0 · 2 SP · Durbek
Qabul mezoni: Ultralytics (AGPL-3.0 yoki pullik litsenziya yoki boshqa kutubxona) va model og'irliklari bo'yicha yozma qaror. Pilotdan oldin yopiladi; tijoriy mahsulot rejalansa, Sprint 2 dagi o'qitishdan oldin boshlash ma'qul.

### PPE-502 · Login va rollar · P0 · 5 SP · Durbek
Qabul mezonlari:
- Admin va nazoratchi rollari.
- Video, API va suratlar loginsiz ochilmaydi.

### PPE-503 · HTTPS va maxfiy sozlamalar · P0 · 3 SP · Durbek
Qabul mezoni: tarmoq orqali faqat HTTPS bilan kiriladi, kamera paroli va token loglarda ko'rinmaydi.

### PPE-301 · Bir nechta zona va qoidalar · P1 · 5 SP · Durbek
Qabul mezonlari:
- Har bir zonaning nomi, qoidasi va ish vaqti bor.
- "Hech kim kirmasin" qoidasi ishlaydi.
- Eski `zone.json` yo'qolmaydi, yangi formatga o'tadi.

### PPE-101 · Kadr yig'ish va maxfiylik roziligi · P0 · 3 SP · O'tkirbek
Qabul mezonlari:
- Suratga olish va ma'lumotdan foydalanishga yozma ruxsat olinadi (yig'ishdan oldin).
- Kamida 1500 xilma-xil kadr: kaskali, kaskasiz, kepkali, turli yorug'lik.

### PPE-102 · Kadrlarni belgilash · P0 · 8 SP · O'tkirbek
Bog'liqlik: PPE-101.

Qabul mezonlari:
- Odam, kaska va yalang bosh belgilangan, yozma qoidalar bor.
- Train/validation/test video yoki kun bo'yicha ajratiladi, bir videoning kadrlari ikki to'plamga tushmaydi.

### PPE-104 · Dataset litsenziyalarini yozib borish · P1 · 1 SP · O'tkirbek
Qabul mezoni: ishlatilgan har bir ma'lumot manbasi va litsenziyasi hujjatlashtirilgan.

### PPE-303 · Kunlik Telegram xulosasi · P1 · 2 SP · O'tkirbek
Qabul mezoni: belgilangan soatda jami buzilishlar, zonadagilar va eng xavfli soat yuboriladi.

---

## Sprint 2: Model, maxfiylik, o'rnatish (2 hafta)

### PPE-103 · Baholash skripti va boshlang'ich natija · P0 · 3 SP · Durbek
Bog'liqlik: PPE-102.

Qabul mezonlari:
- Bitta buyruq bilan precision, recall va mAP50 chiqadi.
- Hozirgi ikkala model natijasi yozib qo'yiladi.
- Shu natijaga qarab qayta o'qitish uchun maqsad raqamlar belgilanadi.

### PPE-201 · Modelni qayta o'qitish · P0 · 8 SP · Durbek
Bog'liqlik: PPE-102, PPE-103. GPU kerak (ijaraga yoki bulutda).

Qabul mezonlari:
- Test to'plamida PPE-103 da belgilangan maqsadga yetadi.
- Kepkani kaska deb olish holati alohida o'lchanadi va kamayadi.
- Noutbuk CPU'sida kamida 15 FPS.

### PPE-504 · Yuzni xiralashtirish va saqlash muddati · P0 · 5 SP · Durbek
Qabul mezonlari:
- Saqlanadigan va Telegramga ketadigan suratlarda yuz xiralashtiriladi.
- Belgilangan muddatdan eski suratlar avtomatik o'chiriladi.
- PPE-202 uchun saqlanadigan asl kadrlarga ham shu qoidalar yoki alohida ruxsat qo'llanadi.

### PPE-203 · Odam bo'lmagan obyektlardagi signallar · P1 · 3 SP · O'tkirbek
Qabul mezoni: logotip va plakat misollari test to'plamiga qo'shilgan, ulardagi soxta signallar soni oldin va keyin o'lchangan.

### PPE-302 · Hodisa holati va filtr · P1 · 3 SP · O'tkirbek
Qabul mezonlari: "yangi / ko'rildi / hal qilindi" holatlari; sana, tur va zona bo'yicha filtr. Baza migratsiyasida eski hodisalar saqlanadi.

### PPE-401 · Qo'shimcha himoya vositalari tadqiqoti · P1 · 3 SP · O'tkirbek
Qabul mezoni: ko'zoynak, qo'lqop va niqob uchun real kadrlarda o'lchov va har biri bo'yicha "qilamiz / qilmaymiz" qarori.

### PPE-402 · Jilet nazoratini sinash · P1 · 2 SP · O'tkirbek
Qabul mezoni: jiletli va jiletsiz real kadrlarda precision va recall o'lchangan.

### PPE-601 · Docker va avtomatik qayta ishga tushish · P0 · 3 SP · O'tkirbek
Qabul mezoni: toza kompyuterda hujjat bo'yicha o'rnatiladi, qayta yuklangandan keyin o'zi ishga tushadi.

### PPE-602 · Tizim holati monitoringi · P0 · 2 SP · O'tkirbek
Qabul mezoni: kamera yoki xizmat to'xtasa, Telegramga xabar keladi. Butun kompyuter o'chsa ham bilinishi uchun tekshiruv tashqaridan qilinadi.

---

## Sprint 3: Masshtab va pilot (2 hafta)

### PPE-202 · "Noto'g'ri signal" tugmasi · P1 · 5 SP · Durbek
Qabul mezonlari:
- Dashboard'da hodisa noto'g'ri deb belgilanadi.
- Belgi bazada saqlanadi, hisobotdan chiqariladi.
- Belgilangan suratlarni qayta o'qitish uchun eksport qilsa bo'ladi. Buning uchun ramkasiz asl kadr ham saqlanadi.

### PPE-603 · Bir nechta kamera · P1 · 8 SP · Durbek
Bog'liqlik: PPE-301, PPE-502.
Qabul mezonlari: kamida 2 kamera bitta panelda; zona va hodisalar kameraga bog'langan; tanlangan qurilmada FPS o'lchangan.

### PPE-304 · Haftalik/oylik trend va eksport · P2 · 5 SP · O'tkirbek
Qabul mezonlari: trend grafigi; tanlangan davr Excel'ga eksport qilinadi.

### PPE-404 · Olov va tutunni aniqlash (prototip) · P2 · 5 SP · O'tkirbek
Qabul mezoni: model va litsenziyasi tanlangan, test videolarida o'lchangan. Sertifikatlangan yong'in signalizatsiyasi o'rnini bosmasligi hujjatda yoziladi.

### PPE-604 · Obyekt karnayida ovoz · P1 · 2 SP · O'tkirbek
Qabul mezoni: brauzer ochilmagan holda ham ogohlantirish karnaydan eshitiladi.

### PPE-605 · Pilotni boshlash · P0 · 3 SP · O'tkirbek
Bog'liqlik: PPE-501–504, PPE-601, PPE-602.
Qabul mezonlari: bitta obyektda o'rnatilgan; muvaffaqiyat o'lchovlari (soxta signallar soni, ishlash vaqti) kelishilgan; qo'llanma topshirilgan. Pilot kuzatuvi sprintdan keyin davom etadi.

---

## Backlog (vaqt qolsa)

### PPE-403 · Yiqilgan odamni aniqlash (prototip) · P2 · 5 SP · Durbek
Qabul mezonlari: sahnalashtirilgan videolarda o'lchov; engashish va o'tirishdagi soxta signallar alohida sanaladi.

---

## Bajarildi deb hisoblash sharti
Qabul mezonlari bajarilgan, testlar o'tgan, README yoki DEMO.md yangilangan.

## Asosiy xavflar
- **Belgilash vaqti:** PPE-102 bahodan ko'p vaqt olishi mumkin.
- **Zich jadval:** PPE-103 va PPE-201 belgilash (PPE-102) tugashiga bog'liq. U kechiksa, Durbek avval PPE-504 ni qiladi.
- **Ruxsat:** obyektda suratga olishga ruxsat kechiksa, model bilan bog'liq ishlar (PPE-101, 102, 103, 201) to'xtaydi. Uni Sprint 0 paytidayoq so'rash kerak.
- **Pilot:** real obyektda sinov faqat login, HTTPS va maxfiylik ishlari tugagach boshlanadi.
- **Kod ko'rigi:** har bir o'zgarishni ikkinchi dasturchi ko'rib chiqadi, ayniqsa PPE-502–504. Ko'rik vaqti SP ga kiritilmagan.
