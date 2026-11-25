# PPE-404: Olov va tutunni aniqlash (Prototip tadqiqoti)

**Ijrochi:** O'tkirbek  
**Sana:** 2026-11-25  
**Holat:** Jarayonda: olov/tutun model og'irliklari va test videolarida o'lchov kutilmoqda  

---

## ⚠️ Muhim ogohlantirish (Cheklov)

> **Ushbu dasturiy modul sertifikatlangan yong'in signalizatsiyasi (EN 54 / GOST) o'rnini BOSMAYDI.**  
> Video tahlil faqat qo'shimcha vizual ogohlantirish vositasi bo'lib, yong'in xavfsizligi bo'yicha asosiy sensorlar (tutun/issiqlik datchiklari) o'rnida ishlatilishi qat'iyan taqiqlanadi.

---

## 1. Model nomzodlari (yakuniy tanlov emas)

| Nomzod | Arxitektura | Litsenziya | Afzalligi | Kamchiligi |
|---|---|---|---|---|
| **D-Fire YOLOv8s** (dastlabki nomzod) | YOLOv8s (2 sinf: `fire`, `smoke`) | **Tasdiqlanmagan** (aniq og'irlik fayli va manbasi ko'rsatilmagan); Ultralytics bilan ishlatilsa AGPL-3.0 masalasi ham bor (PPE-501) | Mavjud `ppe-camera` pipeline'i bilan bir xil runtime (`ultralytics`) | Payvandlash uchquni va bug'da soxta signal berishi mumkin |
| **OpenCV HSV + Motion** | Klassik rang/harakat | Apache-2.0 | Juda tez (<2 ms) | Quyosh nuri, sariq jilet va changni olov/tutun bilan adashtiradi |

**Dastlabki nomzod:** mavjud `ultralytics` kodiga mosligi sababli **YOLOv8s (fire/smoke)**. Aniqligi o'lchanmagan. Yakuniy tanlov aniq og'irlik fayli, uning manba havolasi va litsenziyasi tekshirilib, test videolarida o'lchangandan keyin qilinadi.

---

## 2. Keyingi qadamlar

1. Ochiq D-Fire / BoWFire test videolarini yig'ish.
2. `tools/eval_fire.py` orqali CPU FPS va soxta signallarni (payvandlash, chang, bug') o'lchash.
