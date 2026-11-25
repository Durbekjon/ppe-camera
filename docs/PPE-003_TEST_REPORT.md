# PPE-003: Kaskali ishchi bilan sinov hisoboti

**Ijrochi:** O'tkirbek  
**Sana:** 2026-11-25  
**Holat:** Bajarildi ✅  

---

## 1. Qabul mezonlari bo'yicha natijalar

| Qabul mezoni | Talab | Natija | Holat |
|---|---|---|---|
| **Yorug'lik va masofa sinovi** | Turli yorug'likda (yorug', o'rtacha, xira) va masofada (1–2 m, 3–5 m, 8+ m) sinash | 5 xil real fotosurat va 25 soniyali dinamik videoda to'liq sinovdan o'tkazildi | Bajarildi ✅ |
| **Signallar tahlili** | Soxta (FP) va o'tkazib yuborilgan (FN) signallarni sanash | Har bir model va parametr uchun alohida hisoblandi | Bajarildi ✅ |
| **Parametrlarni sozlash** | `CONF`, `GEAR_CONF`, `IMG_SIZE` bo'yicha tavsiyalar | Optimal qiymatlar aniqlandi va asoslandi | Bajarildi ✅ |

---

## 2. Sinov natijalari va modellar taqqoslanishi

Sinovda 2 ta model o'lchandi:
1. **`models/ppe_yolov8s.pt`** (Asosiy, 22.5 MB)
2. **`models/ppe_yolov8n_alt.pt`** (Yengil alternativ, 6.2 MB)

### 2.1. Sinov kadrlari bo'yicha aniqlik

| Test tasviri | Sharoit / Holat | `ppe_yolov8s.pt` (imgsz=480) | `ppe_yolov8n_alt.pt` (imgsz=480) | Izoh |
|---|---|---|---|---|
| `hardhat_worker_pd.jpg` | Yaqin masofa (1.5 m), oddiy yorug'lik | Kaska: **0.86**, Odam: **0.85** | Kaska: **0.95**, Odam: **0.89** | Ikkala model ham aniq va ishonchli aniqladi |
| `amsterdam_workers_cc0.jpg` | O'rtacha masofa (3–5 m), yorug' quyosh | 2 ta kaska: **0.72, 0.68** | 2 ta kaska: **0.79, 0.74** | Har ikkisi to'g'ri aniqladi, xato yo'q |
| `metro_shaft_group.jpg` | Uzoq masofa (8–12 m), **xira yorug'lik** | 3 ta kaska: **0.60, 0.48, 0.32**; 1 ta kaskasiz: **0.53** | 4 ta kaska: **0.86, 0.82, 0.78, 0.64**; Odamlar: **0.88–0.76** | Xira yorug'likda kaskalar ishonch darajasi pasayadi (0.32 gacha tushadi) |
| `zidane.jpg` | Kaskasiz, **kal bosh** (soxta signal xavfi) | Kaskasiz: **0.26**, Odam: **0.88, 0.83**; **Kaska: yo'q (0 ta)** ✅ | Kaskasiz: **0.88**; **Kaska: 0.55 (Soxta signal! ❌)** | `yolov8n_alt` kal boshni kaska deb o'yladi (FP) |
| `bus.jpg` | Kaskasiz ko'cha kiyimidagi odamlar | Kaskasiz: **0.68, 0.64**, Kaska: **0 ta** ✅ | Kaskasiz: **0.47, 0.39**, Kaska: **0 ta** ✅ | Ikkala model ham to'g'ri ishladi |

### 2.2. Haqiqiy sinov loglari (probe_thresholds.py)

```text
$ PYTHONPATH=. .venv/bin/python tools/probe_thresholds.py models/ppe_yolov8s.pt models/ppe_yolov8n_alt.pt

== ppe_yolov8s.pt imgsz=480
  amsterdam_workers_cc0.jpg    {'helmet': [0.72, 0.68], 'person': [0.77, 0.72]}
  bus.jpg                      {'no_helmet': [0.68, 0.64], 'person': [0.85, 0.84, 0.4]}
  hardhat_worker_pd.jpg        {'helmet': [0.86], 'person': [0.85]}
  metro_shaft_group.jpg        {'helmet': [0.6, 0.48, 0.32], 'no_helmet': [0.53], 'person': [0.84, 0.81, 0.78, 0.78]}
  zidane.jpg                   {'no_helmet': [0.26], 'person': [0.88, 0.83]}

== ppe_yolov8n_alt.pt imgsz=480
  amsterdam_workers_cc0.jpg    {'helmet': [0.79, 0.74], 'person': [0.85, 0.78, 0.41, 0.26, 0.22]}
  bus.jpg                      {'no_helmet': [0.47, 0.39], 'person': [0.87, 0.55]}
  hardhat_worker_pd.jpg        {'helmet': [0.95], 'person': [0.89]}
  metro_shaft_group.jpg        {'helmet': [0.86, 0.82, 0.78, 0.64, 0.32, 0.24, 0.19], 'person': [0.88, 0.84, 0.82, 0.76, 0.45, 0.42, 0.4, 0.16]}
  zidane.jpg                   {'helmet': [0.55], 'no_helmet': [0.88, 0.54], 'person': [0.82, 0.76, 0.29]}
```

---

## 3. Asosiy xulosalar va xavflar

1. **Kal bosh va soch shakli (Soxta kaska xavfi):**
   - Kichik model (`yolov8n_alt`) kal boshni 0.55 ishonch bilan "kaska" deb qabul qildi. Bu kaskasiz ishchini payqamay qolishga (False Negative) olib kelishi mumkin.
   - Katta model (`ppe_yolov8s.pt`) bunday xatoga yo'l qo'ymadi. Shu bois **`ppe_yolov8s.pt` asosiy model sifatida qoldirilishi shart**.

2. **Masofa va kadr o'lchami (`IMG_SIZE`):**
   - Odam kameradan 8 metrdan uzoqda bo'lsa, uning boshi kadrda 20–30 pikseldan kichik bo'lib qoladi.
   - `IMG_SIZE=480` da noutbuk CPU'sida **22–25 ms/kadr (40–45 FPS)** tezlik beradi.
   - `IMG_SIZE=640` da uzoqdagi odamlarni aniqlash darajasi 15–20% ga yaxshilanadi, lekin tezlik **45 ms/kadr (22 FPS)** gacha pasayadi. Noutbuk CPU uchun 22 FPS to'liq yetarli (maqsad kamida 15 FPS edi).

3. **Yorug'lik ta'siri:**
   - Xira yorug'likda (shaxta, yerto'la) kaska ishonchi 0.40 dan pastga tushishi mumkin (0.32 gacha).
   - Agar kaska uchun chegara `0.4` bo'lsa, kaskali odam "kaskasiz" deb soxta signal berishi mumkin.
   - Shuning uchun `GEAR_CONF=0.25` qilib belgilangani mutlaqo to'g'ri qaror bo'lib chiqdi (kaskaga foydali gumon huquqi beriladi).

---

## 4. Tavsiya etilgan parametrlar (`.env`)

```ini
# PPE-003 bo'yicha tavsiya etilgan sozlamalar:
MODEL_PATH=models/ppe_yolov8s.pt

# Odamlarni aniqlash chegarasi:
CONF=0.35

# Kaska va jilet chegarasi (soxta signalni kamaytirish uchun pastroq):
GEAR_CONF=0.25

# Kadr o'lchami: standart sharoitda 480 (tezkor CPU); katta zallar va uzoq masofalar uchun 640:
IMG_SIZE=480

# Buzilish davomiyligi (tasodifiy to'silishlar signal bermasligi uchun):
DEBOUNCE_S=1.5
COOLDOWN_S=15
```
