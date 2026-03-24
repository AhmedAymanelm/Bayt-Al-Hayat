<div align="center">
  <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white" alt="OpenAI" />
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  
  <h1>🏛️ Bayt Al Hayat — Mental Wellness & Astrology App</h1>
  <p>A comprehensive backend for AI-powered astrology, psychology, and neuroscience analysis with a fully-featured Admin Dashboard and payment integration.</p>
</div>

---

## 📝 Project Overview

**Bayt Al Hayat (House of Life)** is an AI-driven personality insights platform. It analyzes users through multiple lenses—psychological, neurological, and astrological—to generate deeply personalized reports. These reports are then transformed into cinematic, AI-generated video journeys, proving a unique and immersive self-discovery experience.

---

## ✨ Features

### 🧠 Core Sciences Analysis
- **Psychology:** 7-question mental health evaluation mapped to deep psychological profiles.
- **Neuroscience:** Analysis of nervous system responses (Fight, Flight, Freeze, Fawn).
- **Astrology:** Real-time planetary placements and insights.
- **Letter Science:** Ancient Arabic name-number (Abjad) analysis combined with age cycles.

### 🎥 AI Video Generation
- Generates dynamic narration scripts via **GPT-4o**.
- Text-to-Speech (TTS) via **OpenAI HD Voices**.
- Dynamic, segment-specific imagery generated via **Stability AI**.
- Automatic montage stitching with Ken Burns effects via **FFmpeg**.

### 🛠️ Complete Admin Dashboard
- **Analytics:** Key Performance Indicators (KPIs) and user journey tracking.
- **User Management:** View, ban, or delete users. Check their assessment history.
- **Payment Gateway:** Kashier integration with a dynamic transaction dashboard.
- **System Settings:** Update API keys, manage gateway modes, and toggle admin access securely from the UI.
- **Notification System:** Push and in-app notifications targeting all or specific users with read tracking.

### 🔐 Security & Auth
- JWT based authentication for Users and Admins.
- Secure standard password hashing (bcrypt).
- Cloudinary integration for user avatars.
- Rate-limiting enabled via `slowapi` to prevent abuse.

---

## 🚀 Tech Stack

- **Backend:** Python 3.12, FastAPI, Uvicorn, SQLAlchemy (AsyncPG)
- **Database:** PostgreSQL (Neon DB recommended)
- **GenAI APIs:** OpenAI (GPT-4o, TTS), Stability AI 
- **Media Processing:** FFmpeg, Cloudinary
- **Emails:** Brevo HTTP API
- **Deployment:** Railway / Docker / Nixpacks

---

## 📦 Local Setup & Installation

### 1. Prerequisites
- Python 3.12+
- PostgreSQL database
- FFmpeg installed locally (`brew install ffmpeg` on Mac, `apt install ffmpeg` on Linux)

### 2. Clone the repository
```bash
git clone https://github.com/your-org/bayt-al-hayat.git
cd bayt-al-hayat
```

### 3. Setup Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Environment Variables
Create a `.env` file in the root. Refer to `.env.example` if available, and ensure you have at minimum:
```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname

# Security
SECRET_KEY=your_super_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# APIs
OPENAI_API_KEY=sk-...
STABILITY_API_KEY=sk-...

# 3rd Party
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
BREVO_API_KEY=...
KASHIER_API_KEY=...
KASHIER_MERCHANT_ID=...
```

### 6. Create Initial Admin
To access the Dashboard, you need an admin user:
```bash
python create_admin.py
```
*(This will create `admin@baytalhayat.com` with password `123456`)*

### 7. Run the Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
- **API Docs (Swagger):** `http://localhost:8000/docs`
- **Admin Dashboard:** `http://localhost:8000/admin-ui/`

---

## 🚂 Deployment (Railway)

This repository is optimized for deployment on **Railway**. All configuration files (`railway.toml`, `Procfile`, `runtime.txt`) are already included.

### Steps to Deploy:
1. Push this repository to your GitHub account.
2. Go to [Railway.app](https://railway.app/).
3. Click **New Project** -> **Deploy from GitHub repo**.
4. Select your repository.
5. In the Railway project dashboard, go to **Variables** and paste the contents of your `.env` file (Make sure to remove the `+asyncpg` from Railway's default database string if connecting a Railway Postgres plugin, or just copy the raw string directly into `DATABASE_URL`).
6. Railway will automatically detect the Python environment via `nixpacks` and install FFmpeg automatically.
7. Once deployed, generate a public domain in Railway settings.
8. **Done!**

---

## 📂 Project Structure

```text
baytalhayat/
├── main.py                 # FastAPI Application Entry
├── create_admin.py         # Utility to seed the database with an Admin
├── requirements.txt        # Python packages
├── railway.toml / Procfile # Deployment instructions
├── dashboard-admin/        # Static HTML/JS files for the Admin UI
├── videos/                 # Temporarily storage for generated videos
├── app/
│   ├── auth/               # User registration, login, JWT logic
│   ├── database.py         # SQLAlchemy Setup & DB Init
│   ├── models/             # SQLAlchemy DB schemas
│   ├── routes/             # FastAPI Route Definitions
│   ├── schemas/            # Pydantic validation schemas
│   └── services/           # Heavy lifting (AI logic, Video Gen, DB ops)
```

---

<div align="center">
  <p><i>Developed with ❤️ for the future of mental well-being and personal insight.</i></p>
</div>
