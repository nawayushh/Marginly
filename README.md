# Marginly

### AI-Powered Menu Profitability Analyzer for Indian Restaurants

Marginly helps restaurants understand menu performance by analyzing dish popularity and contribution margins, turning sales data into actionable business insights. It uses **Gemini AI** for real-time mandi commodity price alerts, recipe costing, and market intelligence.

## Features

- **Performance Analytics:** Track revenue, ingredient costs, and contribution profit per dish.
- **Menu Engineering Matrix:** Classify dishes as Stars, Plowhorses, Puzzles, or Dogs.
- **AI Recipe Capture:** Add recipes via voice (Hindi/English), photograph (OCR), or manual entry.
- **Real-Time Mandi Price Alerts:** Get live wholesale commodity price shifts via Gemini AI.
- **What-If Simulator:** Test menu price and volume changes before applying them.
- **Menu Layout Heatmap:** Visualize menu placement effectiveness.
- **Hindi / English Toggle:** Full bilingual UI.

## Tech Stack

- **Frontend:** HTML, Tailwind CSS, Vite, Chart.js
- **Backend:** Python, FastAPI, SQLite
- **AI:** Google Gemini 1.5 Flash (cloud), LM Studio + Qwen (optional, local)

---

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| **Python** | 3.10+ | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org/) |
| **Git** | any | [git-scm.com](https://git-scm.com/) |
| **Gemini API Key** | free tier works | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |

> **Optional:** [LM Studio](https://lmstudio.ai/) + Qwen 2.5 7B for local AI inference (not required — Gemini handles everything by default).

---

## Quick Start (After Cloning)

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/Marginly.git
cd Marginly
```

### 2. Set up the Backend

```bash
# Create a Python virtual environment
cd backend
python -m venv venv

# Activate it
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate.bat
# macOS / Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy the example env file
# Windows:
copy .env.example .env
# macOS / Linux:
cp .env.example .env
```

Now open `backend/.env` and set your **Gemini API key**:

```env
GEMINI_API_KEY=your-actual-gemini-api-key-here
GEMINI_MODEL=gemini-1.5-flash
```

> Get a free API key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### 4. Start the Backend Server

```bash
# From the backend/ directory, with venv activated:
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 5. Set up the Frontend (new terminal)

```bash
cd frontend
npm install
npm run dev
```

You should see:
```
VITE v5.x.x  ready in XXXms
➜  Local:   http://localhost:5173/
```

### 6. Open in Browser

Go to **http://localhost:5173/** — you'll see the login page. Register a new account to get started.

---

## Running Both Servers at Once

You need **two terminals** running simultaneously:

| Terminal | Directory | Command |
|----------|-----------|---------|
| Terminal 1 (Backend) | `backend/` | `python -m uvicorn app:app --host 127.0.0.1 --port 8000` |
| Terminal 2 (Frontend) | `frontend/` | `npm run dev` |

> **Tip:** Don't forget to activate the Python virtual environment in Terminal 1 before starting the backend.

---

## Project Structure

```
Marginly/
├── backend/
│   ├── app.py              # FastAPI server (routes, auth, CRUD)
│   ├── ai_service.py       # Gemini / LM Studio AI integration
│   ├── prompts.py          # AI prompt templates
│   ├── menu_analysis.py    # Menu engineering calculations
│   ├── config.py           # Environment config loader
│   ├── requirements.txt    # Python dependencies
│   ├── .env.example        # Environment template (copy to .env)
│   └── marginly.db         # SQLite database (auto-created on first run)
│
├── frontend/
│   ├── index.html           # Dashboard
│   ├── login.html           # Login page
│   ├── register.html        # Registration / onboarding
│   ├── marginly-core.js     # Shared UI logic (auth, nav, language, themes)
│   ├── vite.config.js       # Vite config
│   ├── package.json         # Node dependencies
│   └── menumitra_*/         # Feature pages (dishes, add recipe, alerts, etc.)
│
├── tests/                   # Pytest test suite
└── README.md
```

---

## Core Metrics

| Metric | Formula |
|--------|---------|
| Contribution Margin | Selling Price − Ingredient Cost |
| Revenue | Selling Price × Quantity Sold |
| Contribution Profit | Contribution Margin × Quantity Sold |
| Popularity % | Dish Quantity ÷ Total Units Sold |

---

## API Endpoints (Backend)

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/auth/login` | Login with username/password |
| POST | `/api/auth/register` | Register new restaurant account |
| GET | `/api/dishes` | List all dishes for the logged-in user |
| POST | `/api/dishes` | Add a new dish |
| GET | `/api/dashboard` | Dashboard KPIs and menu matrix |
| POST | `/api/alerts/sync-live-mandi` | Trigger Gemini mandi price scan |
| GET | `/api/alerts` | Get all price alerts |
| DELETE | `/api/alerts/{id}` | Dismiss a single alert |
| POST | `/api/chat` | General AI chat (recipe costing, etc.) |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError` on backend | Activate venv: `.\venv\Scripts\Activate.ps1` then `pip install -r requirements.txt` |
| Frontend shows blank page | Make sure backend is running on port 8000 |
| Gemini AI not responding | Check `GEMINI_API_KEY` in `backend/.env` |
| Port 8000 already in use | Kill the process: `netstat -ano \| findstr :8000` then `taskkill /PID <PID> /F` |
| Port 5173 already in use | Kill the process or use `npm run dev -- --port 5174` |

---

## License

This project is for educational and demonstration purposes.

**Know your menu. Understand your margins.**
