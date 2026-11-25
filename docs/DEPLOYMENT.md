# PPE-601: Docker va avtomatik qayta ishga tushish (Deployment)

**Ijrochi:** O'tkirbek  
**Sana:** 2026-11-25  
**Holat:** Jarayonda (Docker va systemd tayyorlandi, toza kompyuterda qayta yuklash sinovi kutilmoqda)  

---

## 1. Docker Compose orqali o'rnatish (Tavsiya etiladi)

Kompyuter qayta yoqilganda (reboot) konteyner `restart: unless-stopped` qoidasi tufayli avtomatik ravishda qayta ishga tushadi. Xavfsizlik maqsadida port faqat `127.0.0.1:8000` ga bog'langan (lokal tarmoqqa ochiq emas).

### 1.1. Ishga tushirish

```bash
# 1. Sozlamalarni tekshiring yoki .env yarating
cp .env.example .env

# 2. Konteynerni orqa fonda yig'ish va ishga tushirish
docker compose up -d --build

# 3. Loglarni kuzatish
docker compose logs -f
```

### 1.2. Birinchi kirish va foydalanuvchi yaratish (create_user)

Tizimga kirish uchun kamida bitta admin foydalanuvchi bo'lishi shart. Konteyner ishga tushgach, quyidagi buyruq bilan foydalanuvchi yarating:

```bash
# Docker konteyneri ichida admin yaratish:
docker compose exec ppe-camera python -m tools.create_user admin --role admin

# Yoki kuzatuvchi (supervisor) roli bilan:
docker compose exec ppe-camera python -m tools.create_user watcher --role supervisor
```
*(Buyruq bajarilganda parol so'raladi, parol uzunligi kamida 8 ta belgi bo'lishi lozim).*

### 1.3. Veb-panelga kirish (HTTPS)

Dastur avtomatik ravishda o'z-o'zidan imzolangan (self-signed) TLS sertifikatini yaratadi va faqat xavfsiz HTTPS orqali xizmat ko'rsatadi:

- **Brauzerdagi manzil:** **`https://127.0.0.1:8000`** (yoki `https://localhost:8000`).
- **Sertifikat ogohlantirishi:** Sertifikat lokal ravishda yaratilgani uchun brauzer "Your connection is not private" deb ogohlantirishi tabiiy. Brauzerda **Advanced -> Proceed to 127.0.0.1 (unsafe)** tugmasini bosib o'ting.
- **Terminal orqali tekshirish:**
  ```bash
  curl -k https://127.0.0.1:8000/api/health
  ```

### 1.4. Qayta ishga tushishni tekshirish
- Tizimni qayta yuklang (`sudo reboot`).
- Kompyuter yoqilishi bilanoq dastur avtomatik ravishda `https://127.0.0.1:8000` da ishlayotgan bo'ladi.
- Ma'lumotlar bazasi va suratlar `./data` jildida saqlanib qoladi (Data Persistence).

---

## 2. Linux Systemd orqali o'rnatish (Dockersiz to'g'ridan-to'g'ri OS da)

Agar dastur mini-PC yoki serverning o'zida Docker'siz ishga tushirilishi kerak bo'lsa:

```bash
# 1. Loyihani /opt/ppe-camera ga joylashtirish
sudo cp -r . /opt/ppe-camera
cd /opt/ppe-camera

# 2. Virtual muhit va kutubxonalarni o'rnatish
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. Service faylini tizimga nusxalash
sudo cp deploy/ppe-camera.service /etc/systemd/system/

# 4. Servisni faollashtirish va ishga tushirish
sudo systemctl daemon-reload
sudo systemctl enable ppe-camera    # Tizim yoqilganda o'zi ishga tushadi
sudo systemctl start ppe-camera     # Hozir ishga tushirish

# 5. Holatni tekshirish
sudo systemctl status ppe-camera
```

Dastur biror sabab bilan to'xtab qolsa ham (`SIGKILL` yoki kutilmagan xatolik), `systemd` uni **5 soniya ichida avtomatik ravishda qayta yoqadi** (`Restart=always`).
