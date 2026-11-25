# PPE-203: Odam bo'lmagan obyektlardagi signallar

**Ijrochi:** O'tkirbek
**Sana:** 2026-11-25
**Holat:** Jarayonda (chizma namunalarda o'lchandi; real plakat yoki maneken misollari kerak)

## Qabul mezoni
Logotip va plakat misollari test to'plamiga qo'shilgan, ulardagi soxta signallar soni oldin va keyin o'lchangan.

## Namunalar
`testdata/non_human/` dagi 4 ta rasm **kod bilan chizilgan sodda shakllar**: kaskali plakat, ogohlantirish belgisi, ilgichdagi jilet va kaska, odam silueti. Ular real suratlarning o'rnini bosmaydi.

## Usul
Har bir rasm 3 soniya (30 FPS) kamerada turgandek ilovaning hodisa mantig'iga beriladi. Debounce ikkala holatda ham bir xil (1.5 s), faqat ishonch chegarasi farq qiladi. "Hodisa" bazaga yoziladigan hodisani bildiradi.

```bash
.venv/bin/python -m tools.eval_non_human
```

```text
== ppe_yolov8s.pt (har rasm 3 s, 30 FPS, debounce 1.5 s)
-- past chegara: CONF=0.2, GEAR_CONF=0.2
   jacket_stand_dummy.jpg       hodisa=1  ['person:0.73', 'vest:0.60', 'helmet:0.22']
   logo_warning_sign.jpg        hodisa=0  []
   poster_safety_helmet.jpg     hodisa=0  ['helmet:0.67']
   poster_silhouette.jpg        hodisa=0  []
   JAMI: topilgan obyekt=4, yozilgan hodisa=1
-- joriy chegara: CONF=0.4, GEAR_CONF=0.25
   jacket_stand_dummy.jpg       hodisa=1  ['person:0.73', 'vest:0.60']
   logo_warning_sign.jpg        hodisa=0  []
   poster_safety_helmet.jpg     hodisa=0  ['helmet:0.67']
   poster_silhouette.jpg        hodisa=0  []
   JAMI: topilgan obyekt=3, yozilgan hodisa=1

== ppe_yolov8n_alt.pt (har rasm 3 s, 30 FPS, debounce 1.5 s)
-- past chegara: CONF=0.2, GEAR_CONF=0.2
   jacket_stand_dummy.jpg       hodisa=1  ['helmet:0.48', 'person:0.25']
   logo_warning_sign.jpg        hodisa=0  []
   poster_safety_helmet.jpg     hodisa=0  ['helmet:0.28']
   poster_silhouette.jpg        hodisa=1  ['person:0.26']
   JAMI: topilgan obyekt=4, yozilgan hodisa=2
-- joriy chegara: CONF=0.4, GEAR_CONF=0.25
   jacket_stand_dummy.jpg       hodisa=0  ['helmet:0.48']
   logo_warning_sign.jpg        hodisa=0  []
   poster_safety_helmet.jpg     hodisa=0  ['helmet:0.28']
   poster_silhouette.jpg        hodisa=0  []
   JAMI: topilgan obyekt=2, yozilgan hodisa=0
```

## Xulosa

| Model | Past chegara (0.20) | Joriy chegara (0.4 / 0.25) |
|---|---|---|
| `ppe_yolov8s.pt` (asosiy) | 1 hodisa | **1 hodisa** (ilgichdagi kiyim) |
| `ppe_yolov8n_alt.pt` | 2 hodisa | 0 hodisa |

- **Asosiy modelda yaxshilanish yo'q:** ilgichdagi kiyim `person:0.73` deb topiladi va hodisa yoziladi.
- Kichik modelda joriy chegara bu 4 ta namunadagi hodisalarni yo'qotdi. Bu boshqa tasvirlarga umumlashtirilmaydi.
- "Joriy chegara" yangi tuzatish emas, ilovada avvaldan bor sozlama.
- Odamsiz kaska rasmi hodisa bermaydi, chunki hodisa faqat odam ramkasi bo'yicha yoziladi.
- Debounce faqat qisqa tebranishlarni to'sadi. Qo'zg'almas obyekt 1.5 s dan uzoq tursa, to'smaydi.
- Hozirgi chora: "Noto'g'ri signal" tugmasi (PPE-202). U hodisani hisobotdan chiqaradi, lekin keyingi signallarni to'xtatmaydi.

## Qolgan ishlar
1. Real plakat, logotip va maneken suratlarini (ruxsati va litsenziyasi aniq) qo'shish.
2. Ularni odamsiz misol sifatida qayta o'qitishga (PPE-201) kiritish va oldin hamda keyin o'lchash.
