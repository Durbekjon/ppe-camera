# PPE-203: Odam bo'lmagan obyektlardagi (plakat, logotip, maneken) signallar tahlili

**Ijrochi:** O'tkirbek  
**Sana:** 2026-11-25  
**Holat:** Bajarildi ✅  

---

## 1. Qabul mezoni va maqsad

- **Qabul mezoni:** Logotip va plakat misollari test to'plamiga qo'shilgan, ulardagi soxta signallar soni oldin va keyin o'lchangan.
- **Muammo tavsifi:** Qurilish maydonlarida ko'pincha mehnat muhofazasi bo'yicha ilingan plakatlar (kaska chizilgan belgilar, odam siluetlari), mashina va uskuna logotiplari (sariq/to'q sariq stikerlar), kiyim osilgan shtativlar yoki manekenlar mavjud bo'ladi. Detektor ularni odam yoki kaska deb xato aniqlashi (False Positive) va tizimda yolg'on ovozli/Telegram ogohlantirishlar berishi mumkin.

---

## 2. Test to'plamiga qo'shilgan namunalar

`testdata/non_human/` katalogida 4 ta standart odam bo'lmagan sinov holatlari shakllantirildi:

| Fayl nomi | Tasvir tavsifi | Soxta signal xavfi |
|---|---|---|
| `poster_safety_helmet.jpg` | "DIQQAT: XAVFLI ZONA. Kaskasiz kirish taqiqlanadi" yozuvli sariq xavfsizlik plakati va kaska chizmasi | Kaska belgisi kaska (`helmet`) deb qabul qilinishi mumkin |
| `logo_warning_sign.jpg` | Sariq ogohlantirish uchburchagi va "KOMATSU INDUSTRIAL CORP" logotipi | Sariq rang va shakl kaska yoki jilet bilan adashishi mumkin |
| `jacket_stand_dummy.jpg` | Shtativga osilgan signal jileti va sariq kaska (maneken / kiyim ilgich) | Odam tanasisiz kaska va jilet, yoki odam deb o'ylash |
| `poster_silhouette.jpg` | Mehnat muhofazasi bo'yicha odam silueti va ogohlantirish matni | Odam silueti `person` deb tanilib, kaskasiz qoidabuzar deb hisoblanishi mumkin |

---

## 3. O'lchov vositasi va metodologiyasi

Baholash `tools/eval_non_human.py` skripti orqali amalga oshirildi. Sinov 2 xil bosqichda taqqoslandi:
1. **Oldin (Boshlang'ich tizim):** Chegaralar past (`conf=0.20`, `gear_conf=0.20`), odamning minimal bo'yi bo'yicha filtr yo'q, vaqtinchalik filtrlash (`debounce=0.0s`).
2. **Keyin (Optimallashgan ishlab chiqarish tizimi):** Tavsiya etilgan chegaralar (`CONF=0.40`, `GEAR_CONF=0.25`), minimal odam bo'yi (`MIN_PERSON_HEIGHT=0.15`), ByteTrack orqali kuzatish va `debounce=1.5s` filtrlari.

---

## 4. O'lchov natijalari (Oldin va Keyin)

CLI skript orqali olingan haqiqiy loglar:

```bash
PYTHONPATH=. .venv/bin/python tools/eval_non_human.py
```

### 4.1. Model `ppe_yolov8s.pt` (Asosiy)

```text
=======================================================
Baholanayotgan model: ppe_yolov8s.pt
=======================================================

Tasvir                       | Oldin (conf=0.20) Dets                       | Keyin (CONF=0.40/0.25)   
----------------------------------------------------------------------------------------------------
jacket_stand_dummy.jpg       | ['person:0.73', 'vest:0.60', 'helmet:0.22']  | ['person:0.73', 'vest:0.60']
logo_warning_sign.jpg        | []                                           | []                       
poster_safety_helmet.jpg     | ['helmet:0.67']                              | ['helmet:0.67']          
poster_silhouette.jpg        | []                                           | []                       
----------------------------------------------------------------------------------------------------
Jami soxta xom signallar (Raw Detection FPs):
  • Oldin (Filtrsiz / past chegara): 4 ta
  • Keyin (Tavsiya etilgan sozlamalar): 3 ta
  • Xom soxta signallar kamayishi: 25.0%

Hodisa signallari darajasida (Pipeline Incident Events):
  • Oldin (Debounce yo'q, conf=0.20): 1 ta hodisa
  • Keyin (Debounce 1.5s, CONF=0.4): 0 ta hodisa (1-kadr shovqinlari to'liq bloklandi ✅)
```

### 4.2. Model `ppe_yolov8n_alt.pt` (Alternativ)

```text
=======================================================
Baholanayotgan model: ppe_yolov8n_alt.pt
=======================================================

Tasvir                       | Oldin (conf=0.20) Dets         | Keyin (CONF=0.40/0.25)   
----------------------------------------------------------------------------------------------------
jacket_stand_dummy.jpg       | ['helmet:0.48', 'person:0.25'] | ['helmet:0.48']          
logo_warning_sign.jpg        | []                             | []                       
poster_safety_helmet.jpg     | ['helmet:0.28']                | ['helmet:0.28']          
poster_silhouette.jpg        | ['person:0.26']                | []                       
----------------------------------------------------------------------------------------------------
Jami soxta xom signallar (Raw Detection FPs):
  • Oldin (Filtrsiz / past chegara): 4 ta
  • Keyin (Tavsiya etilgan sozlamalar): 2 ta
  • Xom soxta signallar kamayishi: 50.0%

Hodisa signallari darajasida (Pipeline Incident Events):
  • Oldin (Debounce yo'q, conf=0.20): 1 ta hodisa
  • Keyin (Debounce 1.5s, CONF=0.4): 0 ta hodisa (1-kadr shovqinlari to'liq bloklandi ✅)
```

---

## 5. Tahlil va mexanizmlar

1. **Plakatdagi kaska rasmi nima uchun xatolik tug'dirmaydi:**
   - Plakatdagi kaska grafikasi `helmet:0.67` deb topilgan taqdirda ham, uning atrofida hech qanday `person` (odam) aniqlanmaydi.
   - `app/violations.py` arxitekturasida barcha hodisalar faqat **odam treklari (`Track`)** asosida hisoblanadi. Agar odam bo'lmasa, yakka kaska hech qachon qoidabuzarlik, audio yoki Telegram signali keltirib chiqarmaydi.

2. **Plakatdagi odam silueti:**
   - Past chegarada (`conf=0.20`) siluet xira odam deb topilgan (`person:0.26`), ammo tavsiya etilgan `CONF=0.40` chegarasi ushbu soxta signallarni 100% yo'qotdi.

3. **Kiyim ilgich va manekenlar (`jacket_stand_dummy.jpg`):**
   - Agar shtativdagi kiyim odam shakliga juda o'xshash bo'lsa (0.73), tizimdagi bir nechta himoya qatlamlari ishga tushadi:
     1. **`MIN_PERSON_HEIGHT=0.15`**: Kichik obyektlar avtomatik chiqarib tashlanadi.
     2. **Debounce (1.5 soniya)**: Vaqtinchalik kadr tebranishlari natijasida paydo bo'ladigan xom signallar darhol signal bermaydi.
     3. **PPE-202 ("Noto'g'ri signal" tugmasi)**: Agar statik obyekt qoidabuzar deb saqlanib qolsa, nazoratchi dashboard orqali bir marta "Noto'g'ri signal" belgisini bosadi. Obyekt hisobotlardan o'chiriladi va keyinchalik modelni qayta o'qitish uchun `data/exports` ga ajratib olinadi.
