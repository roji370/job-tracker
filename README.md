# 🎯 JobTracker — AI-Powered Job Matching System

An AI-powered job tracking application that scrapes Amazon Jobs, matches listings to your resume using sentence-transformers, displays results in a React dashboard, and sends WhatsApp + Email alerts automatically every 6 hours.

---

## 🗂️ Project Structure

```
job-tracker/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app + lifecycle + rate limiter
│   │   ├── config.py            # Pydantic settings with production validators
│   │   ├── database.py          # Async SQLAlchemy engine
│   │   ├── scheduler.py         # APScheduler (every 6h) with retry logic
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   ├── middleware/auth.py   # API key authentication dependency
│   │   ├── models/              # SQLAlchemy ORM models (with indexes)
│   │   ├── routes/              # API route handlers
│   │   ├── services/            # Pipeline orchestration
│   │   └── utils/               # Parser, matcher, scraper, notifier
│   ├── alembic/                 # Database migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_initial_schema.py
│   ├── tests/                   # Pytest unit + integration tests
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Root layout + router (includes 404)
│   │   ├── components/          # Sidebar, JobCard, UploadZone, StatCard
│   │   ├── pages/               # Dashboard, Matches, Jobs, Resume, Notifications, NotFound
│   │   └── utils/api.js         # Axios API client (tiered timeouts)
│   ├── nginx.conf               # Nginx SPA + API proxy + security headers
│   └── Dockerfile               # Multi-stage build
├── docker-compose.yml
├── nginx-https.conf.example     # Production HTTPS configuration template
├── .env.example
├── .gitignore
└── README.md
```

---

## ⚙️ Prerequisites

Before starting, generate the required secrets:

```bash
# API Key (clients must send X-API-Key: <value> header)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Secret Key
python -c "import secrets; print(secrets.token_hex(32))"

# Strong DB password
openssl rand -base64 32
```

---

## ⚡ Quick Start (Docker — Recommended)

### 1. Clone & configure environment

```bash
git clone <your-repo-url>
cd job-tracker
cp .env.example .env
nano .env   # Fill in ALL required values — see Environment Variables below
```

### 2. Launch everything

```bash
docker compose up --build
```

| Service   | URL                              |
|-----------|----------------------------------|
| Frontend  | http://localhost:3000            |
| Backend   | http://localhost:8000            |
| API Docs  | http://localhost:8000/api/docs   |

> **Note:** The first build is slow — it downloads Playwright + the sentence-transformer model (~800 MB total). Subsequent builds use Docker layer cache.

### 3. Stop

```bash
docker compose down
# To also remove data volumes:
docker compose down -v
```

---

## 🔐 Authentication

All API endpoints (except `GET /api/health`) require the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key-here" http://localhost:8000/api/jobs/
```

In **development only**, you can leave `API_KEY` empty in `.env` — auth will be disabled with a console warning. In production, `API_KEY` must be set or the server refuses to start.

---

## 🖥️ Local Development (No Docker)

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+

### Backend

```bash
cd backend

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium

# Configure environment
cp ../.env.example ../.env
# Edit .env — for local dev set ENVIRONMENT=development and leave API_KEY empty

# Run server (tables auto-created on first start)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Database Migrations (Alembic)

```bash
cd backend

# Apply all migrations (use this instead of create_all in production)
DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/jobtracker" \
  alembic upgrade head

# Auto-generate a new migration after model changes
alembic revision --autogenerate -m "add my new field"
alembic upgrade head
```

### Frontend

```bash
cd frontend

npm install

# Point to backend
echo "VITE_API_URL=http://localhost:8000" > .env.local

npm run dev
# → http://localhost:5173
```

---

## 🧪 Running Tests

```bash
cd backend

# Install test dependencies (already in requirements.txt)
pip install pytest pytest-asyncio anyio

# Run all tests
pytest

# Run with coverage
pip install pytest-cov
pytest --cov=app --cov-report=term-missing
```

---

## 🌍 Production Deployment

### Option A: Render (Easiest)

1. Create a **PostgreSQL** service on [Render](https://render.com)
2. Create a **Backend Web Service** with:
   - Runtime: Docker
   - Dockerfile: `backend/Dockerfile`
   - Health Path: `/api/health`
   - Port: `8000`
3. Add all `.env` variables in Render **Environment** tab (set `ENVIRONMENT=production`)
4. Create a **Frontend Web Service** with:
   - Runtime: Docker
   - Dockerfile: `frontend/Dockerfile`
   - Build arg: `VITE_API_URL=<backend-url>`
   - Port: `80`

### Option B: AWS EC2 with Docker + HTTPS

```bash
# 1. Launch EC2 (Ubuntu 22.04, t3.medium+)
# Open ports: 22, 80, 443
ssh -i your-key.pem ubuntu@<ec2-ip>

# 2. Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker ubuntu && newgrp docker
sudo apt install docker-compose-plugin nginx certbot python3-certbot-nginx -y

# 3. Deploy
git clone <your-repo-url> job-tracker
cd job-tracker
cp .env.example .env
nano .env   # Fill in everything — set ENVIRONMENT=production

docker compose up --build -d
docker compose logs backend --tail=50

# 4. Configure HTTPS with Let's Encrypt
sudo nano /etc/nginx/sites-available/jobtracker
# Use the template from: nginx-https.conf.example
# Replace "your-domain.com" with your actual domain

sudo ln -s /etc/nginx/sites-available/jobtracker /etc/nginx/sites-enabled/
sudo nginx -t

# Issue SSL certificate
sudo certbot --nginx -d your-domain.com

sudo systemctl restart nginx
```

---

## 🔧 Environment Variables

| Variable                   | Description                                       | Required     |
|----------------------------|---------------------------------------------------|--------------|
| `POSTGRES_DB`              | Database name                                     | ✅ Required  |
| `POSTGRES_USER`            | DB user                                           | ✅ Required  |
| `POSTGRES_PASSWORD`        | DB password (use a strong random value)           | ✅ Required  |
| `DATABASE_URL`             | PostgreSQL async URL (auto-built in Docker)       | ✅ Required  |
| `API_KEY`                  | API key for all endpoints (empty = dev-only mode) | ✅ Production|
| `SECRET_KEY`               | App secret key (64 random chars)                  | ✅ Production|
| `ENVIRONMENT`              | `development` or `production`                     | ✅ Required  |
| `ALLOWED_ORIGINS`          | Comma-separated CORS origins (no localhost in prod)| ✅ Required  |
| `TWILIO_ACCOUNT_SID`       | Twilio account SID                                | ⚠️ Optional  |
| `TWILIO_AUTH_TOKEN`        | Twilio auth token                                 | ⚠️ Optional  |
| `WHATSAPP_FROM`            | Twilio WhatsApp sender number                     | ⚠️ Optional  |
| `WHATSAPP_TO`              | Your WhatsApp number                              | ⚠️ Optional  |
| `EMAIL_HOST`               | SMTP host (default: `smtp.gmail.com`)             | ⚠️ Optional  |
| `EMAIL_PORT`               | SMTP port (default: `587`)                        | ⚠️ Optional  |
| `EMAIL_USER`               | SMTP email address                                | ⚠️ Optional  |
| `EMAIL_PASS`               | SMTP app password                                 | ⚠️ Optional  |
| `EMAIL_TO`                 | Notification recipient email                      | ⚠️ Optional  |
| `SCHEDULER_INTERVAL_HOURS` | How often the pipeline runs (default: `6`)        | ✅ Required  |
| `MATCH_THRESHOLD`          | Min score % for notifications (default: `70`)     | ✅ Required  |

> ⚠️ Optional = app works without them; AI matching still runs, notifications are skipped.

> 🔴 The server will **refuse to start** with `ENVIRONMENT=production` if `SECRET_KEY`, `API_KEY`, or `ALLOWED_ORIGINS` contain insecure default values.

---

## ⏰ How the Scheduler Works

APScheduler starts automatically on boot and runs the full pipeline every `SCHEDULER_INTERVAL_HOURS` hours.

```
1. Scrape Amazon Jobs  (Playwright headless Chromium)
   ↓
2. Load active resume from DB
   ↓
3. AI Matching (sentence-transformers cosine similarity — async thread pool)
   ↓
4. Store job + match records in PostgreSQL
   ↓
5. Send notifications for matches ≥ MATCH_THRESHOLD%
   → WhatsApp (Twilio)
   → Email (SMTP)
   ↓
6. Persist PipelineRun record (status, counts, errors)
```

**Retry logic:** If the pipeline fails (e.g., DB temporarily unavailable), it retries up to 3 times with exponential backoff (30s → 300s).

You can also trigger the pipeline manually:
- **Dashboard "Run Pipeline" button** in the frontend
- **POST** `/api/pipeline/run/sync` via API (waits for result — use for testing only)
- **POST** `/api/pipeline/run` (async, returns immediately)
- **GET** `/api/pipeline/last-run` — see last run result (read from DB)
- **GET** `/api/pipeline/history` — see last N run records

---

## 🧪 Manual Testing Checklist

```bash
API_KEY="your-api-key-here"
BASE="http://localhost:8000"

# 1. Health check (no auth required)
curl $BASE/api/health

# 2. Upload a resume (PDF)
curl -X POST $BASE/api/resumes/upload \
  -H "X-API-Key: $API_KEY" \
  -F "file=@/path/to/resume.pdf"

# 3. Trigger full pipeline (sync)
curl -X POST $BASE/api/pipeline/run/sync \
  -H "X-API-Key: $API_KEY"

# 4. View match results
curl "$BASE/api/matches/?min_score=0" \
  -H "X-API-Key: $API_KEY"

# 5. Trigger notifications manually
curl -X POST $BASE/api/notifications/trigger \
  -H "X-API-Key: $API_KEY"

# 6. View notification logs
curl $BASE/api/notifications/logs \
  -H "X-API-Key: $API_KEY"

# 7. View pipeline history
curl $BASE/api/pipeline/history \
  -H "X-API-Key: $API_KEY"
```

Browse **http://localhost:8000/api/docs** for the full interactive Swagger UI.

---

## 🛠️ Tech Stack

| Layer         | Technology                              |
|---------------|-----------------------------------------|
| Backend       | FastAPI, SQLAlchemy 2.0, asyncpg        |
| Database      | PostgreSQL 16 + Alembic migrations      |
| AI Matching   | sentence-transformers (MiniLM-L6)       |
| Scraping      | Playwright (headless Chromium)          |
| Scheduler     | APScheduler 3.x + tenacity (retry)      |
| Rate Limiting | slowapi                                 |
| Auth          | API key (X-API-Key header)              |
| Notifications | Twilio (WhatsApp), smtplib (Email)      |
| Resume Parse  | PyMuPDF, python-docx                    |
| Frontend      | React 18, Vite, Framer Motion, Recharts |
| Deployment    | Docker, Docker Compose, Nginx + HTTPS   |
