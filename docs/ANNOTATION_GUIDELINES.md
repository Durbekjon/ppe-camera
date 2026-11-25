# PPE-102: Kadrlarni belgilash (Annotation) yo'riqnomasi

**Ijrochi:** O'tkirbek  
**Sana:** 2026-11-25  
**Holat:** Bajarildi ✅  

---

## 1. Belgilash vositasi va formati

- **Tavsiya etilgan vosita:** CVAT (Computer Vision Annotation Tool) yoki Label Studio.
- **Eksport formati:** YOLO formati (`.txt` fayllar: `class_id center_x center_y width height` normallashtirilgan 0..1 oralig'ida).

---

## 2. Sinflar ro'yxati (Classes)

| Class ID | Nomi | Izoh va chegara qoidalari |
|---|---|---|
| `0` | `person` | Odamning butun tanasi (boshdan to oyoq barmoqlarigacha). Agar odam orqa fonda juda kichik bo'lsa (bo'yi < 20 px), belgilanmaydi. |
| `1` | `helmet` | Qattiq himoya kaskasi. Chegara aniq kaska chetlariga mos bo'lishi lozim. |
| `2` | `no_helmet` | Kaskasiz bosh (yalang'och soch, kal bosh, ro'mol, mato kepka, quloqchin). |
| `3` | `vest` | Yorug'lik qaytaruvchi himoya jileti (to'q sariq, och yashil/sariq tasmali). |
| `4` | `no_vest` | Jiletsiz tana qismi (oddiy kurtka, ko'ylak, futbolka). |

---

## 3. Muhim chegaralash qoidalari (Edge Cases)

1. **Kepka va qishki shapkalar:**
   - Hech qachon `helmet` deb belgilanmaydi!
   - Agar boshda qattiq himoya kaskasi bo'lmasa, u har doim `no_helmet` deb belgilanadi.
2. **Qisman to'silgan odamlar (Occlusion):**
   - Agar odamning 50% dan ko'prog'i ko'rinib tursa, ko'ringan tana qismini qamrab oladigan to'liq to'rtburchak chiziladi.
3. **Kaskani qo'lda ushlab turish:**
   - Kaska faqat boshga kiyilgan holatda `helmet` sinfiga kiritiladi. Agar ishchi kaskani qo'lida ushlab turgan bo'lsa, boshi `no_helmet` deb belgilanadi (kaskaning o'zi alohida `helmet_in_hand` yoki e'tiborga olinmaydi).
4. **Juda uzoqdagi ishchilar:**
   - Bosh qismi 10x10 pikseldan kichik bo'lgan va inson ko'zi bilan kaska bor-yo'qligini aniqlab bo'lmaydigan holatlarda bosh belgilanmaydi.

---

## 4. Datasetni taqsimlash qoidasi (Train / Val / Test Split)

> **Eng muhim qoida (Data Leakage oldini olish):**
> Kadrlar tasodifiy (random) aralashtirilmaydi! Bitta videoning yoki bitta ishchining kadrlari bir vaqtning o'zida ham Train, ham Test to'plamiga tushishi qat'iyan man etiladi.

- **Train (70%):** 1 va 2-kun olingan videolardan kadrlar.
- **Validation (15%):** 3-kun boshqa xonada/burchakda olingan kadrlar.
- **Test (15%):** Butunlay yangi 4-kun videosi (model ilgari ko'rmagan yangi ishchilar va boshqa yorug'lik).
