# PPE-605: Pilot ishga tushirish qo'llanmasi va muvaffaqiyat mezonlari

**Ijrochi:** O'tkirbek  
**Sana:** 2026-11-25  
**Holat:** Jarayonda: obyektga o'rnatish va pilot kuzatuvi kutilmoqda  

---

## 1. Pilot muvaffaqiyat mezonlari (KPI)

1. **Ishlash barqarorligi (Uptime):** Ish vaqti davomida kamida **98%** uzluksiz ishlash (`/api/health` tekshiruvi).
2. **Soxta signallar ulushi:** Kunlik jami hodisalarning **10% dan kam** qismi "Noto'g'ri signal" (PPE-202) sifatida belgilanishi.
3. **Tezlik:** Tanlangan qurilmada kamida **15 FPS** (yoki 2 kamera uchun 15+ FPS).

---

## 2. Operator qo'llanmasi (Qisqa)

1. **Kirish:** Brauzerda `https://<server-ip>:8443` manziliga kiring va login/parolni kiriting.
2. **Hodisalarni ko'rib chiqish:**
   - Yangi hodisalar ro'yxatda ko'rinadi.
   - Holatni o'zgartirish uchun nishonni bosing: `Yangi` ➔ `Ko'rildi` ➔ `Hal qilindi`.
   - Agar tizim xato signal bergan bo'lsa, **"Noto'g'ri signal"** tugmasini bosing (hisobotdan chiqariladi).
3. **Hisobot va Excel eksport:**
   - Pastki panelda kunlik hisobot va 7/30 kunlik trend grafigini ko'ring.
   - **"Excel (.xlsx)"** tugmasi orqali tanlangan davr hisobotini yuklab oling.
4. **Karnay ovozi (PPE-604):**
   - Serverda `LOCAL_AUDIO=1` yoqilgan bo'lsa, brauzer ochilmagan holda ham ogohlantirish karnaydan eshitiladi.
