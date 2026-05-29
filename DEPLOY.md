# Panduan Deploy RSHU AI

## Pilihan Platform (Gratis)

| Platform    | Cocok untuk | Kelebihan | Kekurangan |
|-------------|-------------|-----------|------------|
| **Railway** | Produksi    | Mudah, stabil, tidak sleep | $5/bulan kredit |
| **Render**  | Demo/Test   | Mudah setup | Sleep 15 menit jika idle |
| **Fly.io**  | Produksi    | Paling fleksibel, tidak sleep | Lebih teknis |

---

## Opsi 1 — Railway.app (Direkomendasikan)

### Persyaratan
- Akun Railway (gratis di railway.app)
- Akun GitHub (untuk push kode)
- Git terinstall di komputer

### Langkah

**1. Siapkan repository GitHub**
```bash
# Di folder rshu_ai_demo
git init
git add .
git commit -m "RSHU AI v3.2"
# Buat repo baru di github.com, lalu:
git remote add origin https://github.com/USERNAME/rshu-ai.git
git push -u origin main
```

**2. Buat proyek di Railway**
- Login ke railway.app
- Klik "New Project" → "Deploy from GitHub repo"
- Pilih repo rshu-ai
- Railway otomatis deteksi Python dan install

**3. Tambah PostgreSQL**
- Di dashboard Railway → klik "+" → "Database" → "PostgreSQL"
- Railway otomatis set `DATABASE_URL` ke service kamu

**4. Jalankan schema dan import data**
```bash
# Install Railway CLI
npm install -g @railway/cli
railway login
railway run python scripts/import_sdki.py SDKI_import_ready_v2.xlsx --truncate
```

**5. Set environment variables**
Di Railway dashboard → Variables:
```
MAX_CONCURRENT=10
```

**6. Buka URL**
Railway memberi URL otomatis seperti `https://rshu-ai-production.up.railway.app`

---

## Opsi 2 — Render.com

**1. Push ke GitHub** (sama seperti Railway)

**2. Di Render dashboard**
- New → Web Service → Connect GitHub repo
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

**3. Tambah PostgreSQL**
- New → PostgreSQL → Free plan
- Copy "External Database URL" ke environment variable `DATABASE_URL`

**4. Import data** via Render Shell:
```bash
python scripts/import_sdki.py SDKI_import_ready_v2.xlsx --truncate
```

**Catatan**: Free plan akan sleep jika tidak ada request 15 menit.
Request pertama setelah sleep butuh ~30 detik untuk startup.

---

## Opsi 3 — Fly.io

**1. Install Fly CLI**
```bash
# Windows (PowerShell)
powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
```

**2. Login dan deploy**
```bash
fly auth login
fly launch          # ikuti wizard, pilih region Singapore (sin)
fly postgres create --name rshu-db
fly postgres attach rshu-db
fly deploy
```

**3. Import data**
```bash
fly ssh console
python scripts/import_sdki.py SDKI_import_ready_v2.xlsx --truncate
```

---

## Catatan Penting untuk Semua Platform

### File Excel tidak ikut deploy
`SDKI_import_ready_v2.xlsx` ada di `.gitignore`. Upload manual setelah deploy:

**Railway / Render:**
Gunakan SSH/Shell di dashboard untuk upload, atau jalankan import dari komputer lokal dengan `DATABASE_URL` yang mengarah ke database cloud.

**Cara import dari lokal ke database cloud:**
```bash
# Set DATABASE_URL ke database cloud
set DATABASE_URL=postgresql://user:pass@host:5432/rshu_ai
python scripts/import_sdki.py SDKI_import_ready_v2.xlsx --truncate
```

### Schema database
Jalankan `rshu_ai_schema_prod.sql` sekali di database cloud sebelum import.
Di Railway/Render bisa via pgAdmin dengan koneksi ke database eksternal mereka.

### Reload setelah import
Setelah import data, panggil endpoint reload agar pipeline memuat data baru:
```
POST https://your-app.railway.app/api/reload
```
