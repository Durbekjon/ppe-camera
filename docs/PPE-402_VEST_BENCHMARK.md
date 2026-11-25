# PPE-402: Jilet (Vest) nazoratini sinash va baholash hisoboti

**Ijrochi:** O'tkirbek  
**Sana:** 2026-11-25  
**Holat:** Bajarildi ✅  

---

## 1. Qabul mezoni va maqsad

- **Qabul mezoni:** Jiletli va jiletsiz real kadrlarda precision va recall o'lchangan.
- **Asosiy maqsad:** Tizimdagi ikkala model (`models/ppe_yolov8s.pt` va `models/ppe_yolov8n_alt.pt`) orqali xavfsizlik jiletlari (signal jileti / vest) aniqlash sifatini tahlil qilish, soxta signallar (False Positives) va o'tkazib yuborishlar (False Negatives) sonini aniqlash hamda ishlab chiqarishda `REQUIRE_VEST` sozlamasini yoqish bo'yicha asoslangan texnik xulosa berish.

---

## 2. Sinov metodologiyasi va vositasi

Sinov uchun `tools/eval_vest.py` maxsus baholash skripti ishlab chiqildi. Ushbu vosita mavjud real fotosuratlarni yuklab, undagi haqiqiy jiletlar soni (Ground Truth) bilan modellarning chiqargan natijalarini IoU va ishonch chegaralari (`CONF=0.4`, `GEAR_CONF=0.25`, `imgsz=480`) asosida taqqoslaydi.

### 2.1. Sinov kadrlari va Ground Truth

| Tasvir fayli | Holat / Muhit | Haqiqiy odamlar | Haqiqiy jiletlar (GT) | Izoh |
|---|---|---|---|---|
| `testdata/images/amsterdam_workers_cc0.jpg` | Ochiq havo, quyoshli qurilish maydoni | 2 | **2 ta** | 2 ishchi ham sariq/to'q sariq signal jiletida |
| `testdata/images/bus.jpg` | Oddiy ko'cha muhiti, bekat | 3 | **0 ta** | Oddiy fuqarolik kiyimidagi odamlar, jiletsiz |
| `testdata/images/hardhat_worker_pd.jpg` | Yaqin masofa (1.5 m), kaskali ishchi | 1 | **0 ta** | Ishchi kaskada, lekin signal jiletsiz (oddiy ishchi ko'ylagi) |
| `testdata/images/metro_shaft_group.jpg` | Shaxta / tunnel, xira yorug'lik | 4 | **0 ta** | Shaxta ishchilari qorong'i ish kiyimida, yorug'lik qaytaruvchi jiletsiz |
| `testdata/images/zidane.jpg` | Kaskasiz, oddiy kostyum/sport kiyim | 2 | **0 ta** | Signal jiletsiz oddiy kiyim |

---

## 3. Sinov natijalari

### 3.1. Asosiy model: `models/ppe_yolov8s.pt`

CLI sinov buyrug'i:
```bash
PYTHONPATH=. .venv/bin/python tools/eval_vest.py models/ppe_yolov8s.pt
```

Natijalar jadvali:
```text
=== PPE-402: Jilet (Vest) Sinovi: ppe_yolov8s.pt (imgsz=480, conf=0.4, gear_conf=0.25) ===
Tasvir                       Haqiqiy jilet   Topilgan jilet   Ishonch darajalari       
----------------------------------------------------------------------------------------
amsterdam_workers_cc0.jpg    2               2                vest:[0.84, 0.77] no_vest:[]
bus.jpg                      0               0                vest:[] no_vest:[0.77]
hardhat_worker_pd.jpg        0               0                vest:[] no_vest:[]
metro_shaft_group.jpg        0               0                vest:[] no_vest:[0.79, 0.72, 0.69, 0.66]
zidane.jpg                   0               0                vest:[] no_vest:[]
----------------------------------------------------------------------------------------
📊 Xulosa Metrikalari:
  • True Positives (TP):  2
  • False Positives (FP): 0
  • False Negatives (FN): 0
  • Precision:            100.00% (1.000)
  • Recall:               100.00% (1.000)
  • F1-Score:             1.000
```

### 3.2. Alternativ model: `models/ppe_yolov8n_alt.pt`

CLI sinov buyrug'i:
```bash
PYTHONPATH=. .venv/bin/python tools/eval_vest.py models/ppe_yolov8n_alt.pt
```

Natijalar jadvali:
```text
=== PPE-402: Jilet (Vest) Sinovi: ppe_yolov8n_alt.pt (imgsz=480, conf=0.4, gear_conf=0.25) ===
Tasvir                       Haqiqiy jilet   Topilgan jilet   Ishonch darajalari       
----------------------------------------------------------------------------------------
amsterdam_workers_cc0.jpg    2               2                vest:[0.93, 0.90] no_vest:[]
bus.jpg                      0               0                vest:[] no_vest:[0.75]
hardhat_worker_pd.jpg        0               0                vest:[] no_vest:[0.87]
metro_shaft_group.jpg        0               6                vest:[0.88, 0.82, 0.76, 0.71, 0.41, 0.41] no_vest:[0.65]
zidane.jpg                   0               0                vest:[] no_vest:[0.75, 0.69]
----------------------------------------------------------------------------------------
📊 Xulosa Metrikalari:
  • True Positives (TP):  2
  • False Positives (FP): 6
  • False Negatives (FN): 0
  • Precision:            25.00% (0.250)
  • Recall:               100.00% (1.000)
  • F1-Score:             0.400
```

---

## 4. Metrikalar taqqosi

| Model | Hajmi | TP | FP | FN | Precision | Recall | F1-Score | Xulosa |
|---|---|---|---|---|---|---|---|---|
| **`ppe_yolov8s.pt`** (Asosiy) | 22.5 MB | **2** | **0** | **0** | **100.0%** | **100.0%** | **1.000** | A'lo natija, soxta signal yo'q ✅ |
| **`ppe_yolov8n_alt.pt`** (Alternativ) | 6.2 MB | **2** | **6** | **0** | **25.0%** | **100.0%** | **0.400** | O'ta ko'p soxta signal beradi ❌ |

---

## 5. Xatolar tahlili (Error Analysis)

1. **Shaxta va qorong'i kiyimlar muammosi (`metro_shaft_group.jpg`):**
   - Kichik model (`ppe_yolov8n_alt.pt`) xira yorug'likdagi oddiy kombinezon va qora/kulrang kiyimlarni yuqori ishonch bilan (**0.88, 0.82, 0.76**) "vest" deb topdi (6 ta soxta ijobiy signal!). Natijada precision 25% ga tushib ketdi.
   - Asosiy model (`ppe_yolov8s.pt`) esa ularni aniq ajrata oldi: jilet deb topmadi, aksincha ularga `no_vest` (**0.79, 0.72, 0.69, 0.66**) yorlig'ini qo'ydi.

2. **Haqiqiy jiletlarni tanish:**
   - Har ikkala model ham ochiq havodagi haqiqiy signal jiletlarini 100% aniqlikda (Recall = 1.0) topdi (`amsterdam_workers_cc0.jpg`).

---

## 6. Ishlab chiqarish (Production) uchun texnik tavsiyalar

1. **`REQUIRE_VEST` sozlamasi bo'yicha:**
   - `REQUIRE_VEST=1` faqat va faqat **`ppe_yolov8s.pt`** modeli bilan yoqilishi lozim.
   - Agar cheklangan apparat resursi tufayli kichik `ppe_yolov8n_alt.pt` modeli ishlatilsa, **`REQUIRE_VEST=0`** holatida qoldirilishi shart, aks holda shaxta va omborlardagi ishchilar uchun soxta signallar ko'payib ketadi.
2. **Chegara ko'rsatkichlari:**
   - Kaska uchun tavsiya etilgan parametrlar jilet uchun ham o'zini oqladi: `CONF=0.4`, `GEAR_CONF=0.25`, `IMG_SIZE=480`.
   - Agar ob'ektda signal jileti nazorati majburiy bo'lsa, xiralashtirilgan / xira yorug'likli kameralarda qo'shimcha yoritish yoki `ppe_yolov8s.pt` dan foydalanish qat'iy talab etiladi.
