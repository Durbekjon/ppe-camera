# PPE-401: Ko'zoynak, qo'lqop va niqob tadqiqoti

**Ijrochi:** O'tkirbek
**Sana:** 2026-11-25
**Holat:** Jarayonda (faqat nazariy hisob; real kadrlarda o'lchov qilinmagan)

## Qabul mezoni
Ko'zoynak, qo'lqop va niqob uchun **real kadrlarda o'lchov** va har biri bo'yicha "qilamiz / qilmaymiz" qarori.

## Nazariy hisob (o'lchov emas)
Obyektning 1920 piksel kenglikdagi kadrdagi taxminiy o'lchami (gorizontal ko'rish burchagi 85°, obyekt kameraga ro'para, linza buzilishi hisobga olinmagan). O'lchamlar balandlik x kenglik, taxminiy.

| Obyekt | Haqiqiy o'lcham, sm | 2 m, px | 5 m, px | 10 m, px |
|---|---|---|---|---|
| Butun odam | 175 x 50 | 917 x 262 | 367 x 105 | 183 x 52 |
| Kaska | 25 x 25 | 131 x 131 | 52 x 52 | 26 x 26 |
| Signal jileti | 60 x 50 | 314 x 262 | 126 x 105 | 63 x 52 |
| Ko'zoynak | 4 x 14 | 21 x 73 | 8 x 29 | 4 x 15 |
| Qo'lqop (kaft) | 18 x 10 | 94 x 52 | 38 x 21 | 19 x 10 |
| Niqob / respirator | 12 x 15 | 63 x 79 | 25 x 31 | 13 x 16 |

**Muhim:** ilova kadrni 960 pikselgacha kichraytiradi va modelga `IMG_SIZE=480` bilan beradi. Shuning uchun model ko'radigan o'lcham jadvaldagidan **taxminan 4 baravar kichik** bo'ladi.

## Dastlabki mulohazalar (qaror emas)

| Vosita | Dastlabki yo'nalish | Sabab (tekshirilishi kerak) |
|---|---|---|
| Ko'zoynak | Hozircha ustuvor emas | Juda kichik obyekt; shaffof linza yomon ajralishi mumkin |
| Qo'lqop | Hozircha ustuvor emas | Kichik va asbob ushlaganda to'silishi mumkin |
| Niqob / respirator | Birinchi bo'lib sinash | Yuzning kattaroq qismini qoplaydi. YuNet faqat yuzni topadi, niqobni aniqlash uchun alohida model kerak |

Aniqlik (precision, recall, mAP) va qo'shimcha CPU vaqti **o'lchanmagan**.

## Qarorni yopish uchun
1. Ruxsat olingan real kadrlar (har bir vosita bilan va vositasiz, turli masofada).
2. Nomzod modellar va ularning litsenziyasi.
3. `tools/evaluate.py` kabi ramka bo'yicha precision va recall (yangi sinflar uchun skript kengaytiriladi) hamda CPU vaqti.
4. Shundan keyin har bir vosita bo'yicha "qilamiz / qilmaymiz".
