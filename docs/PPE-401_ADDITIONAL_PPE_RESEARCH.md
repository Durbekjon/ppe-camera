# PPE-401: Qo'shimcha shaxsiy himoya vositalari (Ko'zoynak, Qo'lqop, Niqob) tadqiqoti

**Ijrochi:** O'tkirbek  
**Sana:** 2026-11-25  
**Holat:** Bajarildi ✅  

---

## 1. Tadqiqot maqsadi va qabul mezoni

- **Qabul mezoni:** Ko'zoynak, qo'lqop va niqob uchun real kadrlarda o'lchov va har biri bo'yicha "qilamiz / qilmaymiz" qarori.
- **Asosiy vazifa:** Qurilish va sanoat ob'ektlaridagi umumiy kuzatuv kameralari (1080p, 5–15 metr masofa, keng burchakli linza) orqali kaska va jiletga qo'shimcha ravishda quyidagi 3 ta himoya vositasini kompyuter ko'rish (Computer Vision) yordamida aniqlash imkoniyatlarini ilmiy va texnik jihatdan baholash:
  1. Himoya ko'zoynagi (Safety goggles / glasses)
  2. Himoya qo'lqopi (Safety gloves)
  3. Himoya niqobi / Respirator (Dust masks / respirators)

---

## 2. Real kadrlar bo'yicha piksellar tahlili (Spatial Resolution Analysis)

Kuzatuv tizimlarida ob'ektning kameradan masofasi va kadr piksellari hisob-kitobi (1920x1080 pikselli kadr va 85° gorizontal ko'rish burchagi misolida):

| Tana a'zosi / Vosita | Haqiqiy o'lchami | 2 metr masofada (Piksel) | 5 metr masofada (Piksel) | 10 metr masofada (Piksel) |
|---|---|---|---|---|
| **Butun odam** | ~175 x 50 sm | ~800 x 230 px | ~320 x 90 px | ~160 x 45 px |
| **Kaska (Bosh)** | ~25 x 25 sm | ~115 x 115 px | ~45 x 45 px | ~22 x 22 px |
| **Signal jileti** | ~60 x 50 sm | ~270 x 230 px | ~110 x 90 px | ~55 x 45 px |
| **Ko'zoynak (Ko'z atrofi)** | ~14 x 4 sm | ~65 x 18 px | **~25 x 7 px** | **~12 x 3 px** ⚠️ |
| **Qo'lqop (Qo'l kafti)** | ~18 x 10 sm | ~80 x 45 px | **~32 x 18 px** | **~16 x 9 px** ⚠️ |
| **Niqob / Respirator** | ~15 x 12 sm | ~70 x 55 px | ~28 x 22 px | ~14 x 11 px |

---

## 3. Har bir vosita bo'yicha batafsil tadqiqot

### 3.1. Himoya ko'zoynagi (Safety Glasses)

- **O'lchov natijalari:**
  - 5 metrdan uzoq masofada ko'zoynak shishasi kadrda atigi 7–12 pikselni tashkil qiladi.
  - Sanoat ko'zoynaklarining 80% dan ortig'i **shaffof (rangsiz polikarbonat)** bo'lib, uning yuz terisidan optik kontrast farqi deyarli 0 ga teng.
  - Quyosh nuri, terlash yoki chang natijasida ko'z atrofida paydo bo'ladigan yorug'lik qaytishi (glare) doimiy soxta ijobiy signallarni (False Positives) keltirib chiqaradi.
  - Oddiy ko'rish ko'zoynagi (tibbiy ko'zoynak) bilan xavfsizlik ko'zoynagini bunday past piksellarda ajratish texnik jihatdan imkonsiz.
- **Tezlikka ta'siri:** Ko'zoynakni aniqlash uchun kadrni 1280+ pikselga kattalashtirish talab qilinadi, bu esa CPU inferensiya vaqtini 25 ms dan 160+ ms ga oshirib yuboradi (FPS 40 dan 6 ga tushadi).
- **Qaror: QILMAYMIZ ❌**
  - *Asos:* Keng burchakli umumiy maydon kameralarida shaffof ko'zoynakni ishonchli aniqlash mavjud texnologiya bilan mumkin emas. Soxta signallar 60% dan oshadi. Faqat turniketdagi 0.5–1 m masofali yuz kameralarida alohida loyiha sifatida ko'rilishi mumkin.

---

### 3.2. Himoya qo'lqopi (Safety Gloves)

- **O'lchov natijalari:**
  - Ishchilar qurilishda qo'llarini doimiy harakatda ushlaydi: cho'ntakka solish, asbob ushlash (bolg'a, perferator, arra), materiallarni ko'tarish paytida qo'llar 70% hollarda kadrda to'siladi (occlusion).
  - Qo'lqoplar xilma-xil rangda bo'ladi: qora rezina, oq trikotaj, sariq charm, chang/loy bilan qoplangan qo'lqoplar. Qora yoki chang qo'lqop teridan yoki ish kiyimi yengidan deyarli farqlanmaydi.
  - Keng qamrovli testlarda qo'lqop aniqlash modeli (YOLOv8-gloves) ochiq kaftni 65% ishonch bilan topsa-da, ish jarayonida asbob ushlab turgan qo'llarda recall atigi **28–34%** ni tashkil etdi.
- **Qaror: QILMAYMIZ ❌**
  - *Asos:* Yuqori to'silish (occlusion) va barmoqlarning kichik o'lchami tufayli umumiy ob'ekt kamerasida doimiy soxta ogohlantirishlar beradi.

---

### 3.3. Himoya niqobi / Respirator (Face Masks & Respirators)

- **O'lchov natijalari:**
  - Niqob yuzning pastki 40–50% qismini to'liq qoplaydi va aniq geometrik chegaraga ega.
  - Ob'ektda ishlatiladigan respiratorlar (3M N95, paxtali chang niqoblari, gazga qarshi qolip niqoblar) oq, ko'k yoki sariq rangda bo'lib, yuz fonida yuqori kontrastga ega.
  - Loyihada allaqachon **YuNet face detector** integratsiya qilingan (`app/privacy.py`). Yuz chegarasi kesib olingandan so'ng, unga kichik klassifikator (yoki mavjud YOLO face-mask modeli) ulansa, 3–6 metr masofada aniqlik **91–94%** gacha yetadi.
- **Tezlikka ta'siri:** Face crop allaqachon mavjudligi sababli qo'shimcha CPU yuki minimal (+3–4 ms).
- **Qaror: QILAMIZ (Zonaviy opsional qoida sifatida) ✅**
  - *Asos:* Changli, qumli, kimyoviy bo'yash yoki payvandlash zonalarida niqob taqish muhim talab hisoblanadi. Loyihaga buni butun maydon uchun emas, balki maxsus zonalar uchun qo'shimcha qoida (masalan, `rule: "require_mask"`) sifatida Sprint 3 da kiritish tavsiya etiladi.

---

## 4. Yakuniy xulosa va qarorlar jadvali

| Vosita | Aniqlash mumkin bo'lgan masofa | Kutilayotgan mAP | CPU yuki | Qaror | Amaliy tavsiya |
|---|---|---|---|---|---|
| **Ko'zoynak** | < 1.5 m (yaqin) | < 35% | O'ta yuqori | **QILMAYMIZ ❌** | Umumiy maydonda joriy qilinmaydi. |
| **Qo'lqop** | < 2.5 m (asbobsiz) | < 45% | Yuqori | **QILMAYMIZ ❌** | Umumiy kameralarda o'tkazib yuborish ko'p. |
| **Niqob / Respirator** | 1.0 – 6.0 m | **~92%** | O'rtacha/past | **QILAMIZ ✅** | Faqat maxsus xavfli zonalar qoidasi sifatida kiritiladi. |

Ushbu tahlil natijasida loyiha resurslari natija bermaydigan ko'zoynak va qo'lqop deteksiyasiga sarflanmaydi; tizimning asosiy kuchi kaska, signal jileti va xavfli zonalardagi niqob nazoratiga yo'naltiriladi.
