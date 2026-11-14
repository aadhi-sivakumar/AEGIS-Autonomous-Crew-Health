# AEGIS — Autonomous Crew Health

Crew-facing readiness assistant for long-duration missions (and Earth analogs). AEGIS compares **today’s signals against each astronaut’s personal baseline**, helps you **measure cognition**, and gives an **advisory go / caution / no-go** for high-stakes work.

---

## What problem it solves

On deep-space or remote missions, communication delay means crews must notice health and performance changes themselves — early enough to protect EVA, docking, and maintenance.

AEGIS supports that loop:

1. **Check in** — log sleep, fatigue, mood  
2. **Assess** — short in-browser reaction-time test  
3. **Decide** — Ready / Caution / Not recommended before high-stakes tasks  

Cabin context can use **NASA OSDR RR-1 historical environmental data** (2014 hardware environment — not astronaut medical telemetry). Crew health series are simulated from published ranges for privacy.

---

## Quick start

Run **both** processes locally.

### 1. Backend (port 8000)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: http://127.0.0.1:8000/docs

### 2. Frontend (port 3000)

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:3000

---

## How to use the app

### Fastest path for a demo

1. Open http://localhost:3000  
2. In the sidebar, click **Start guided demo**  
   - Sets **Emerging Decline** (CDR-01)  
   - Switches **Env Data Source** to **NASA Historical** (imports RR-1 if needed)  
   - Opens **Today**  
3. Follow **How to use AEGIS today**: Check in → Assessment → Readiness Gate  

### Daily crew loop

| Step | Screen | What you do |
|------|--------|-------------|
| 1 | **Today** | Review status vs personal baseline; complete check-in |
| 2 | **Assessments** | Run reaction-time trials; optional symptom checklist |
| 3 | **Readiness Gate** | See Ready / Caution / Not recommended for EVA, docking, maintenance |

### Additional features

| Screen | Purpose |
|--------|---------|
| **Trends & Forecasts** | Metric history + illustrative next-day forecast |
| **Digital Twin** | Zone indicators, baselines, 24h cognitive forecast |
| **What-If Simulator** | Explore sleep / fatigue / CO₂ effects on projected RT |
| **NASA Mission Replay** | Playback RR-1 cabin env + radiation + statistical anomalies |
| **Telemetry & Relay** | Local encrypted health reports + simulated Mars relay window |

### Sidebar controls

- **Start guided demo** — Emerging Decline + NASA Historical in one click  
- **Env Data Source** — Simulated Mission Data vs NASA Historical Data  
- **Demo Scenario** — Stable Mission / Emerging Decline / Recovery After Assessment  
- **Reset Demo** — Wipes check-ins, assessments, and seeded health; reseeds SQLite. **Keeps** NASA RR-1 cache  

---

## Stack

- **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS, Recharts  
- **Backend:** FastAPI, SQLAlchemy, SQLite, pandas / NumPy / scikit-learn, cryptography (AES-GCM)  
- **Data:** Local SQLite under `/data` (+ optional NASA RR-1 cache)

---

## Data provenance

| Source | Label |
|--------|--------|
| Seeded crew health | Simulated crew data |
| Cabin environment (default) | Synthetic fixtures until NASA mode is on |
| NASA OSDR EDA RR-1 | Historical cabin env + radiation (2014); offline after cache |
| Browser reaction-time task | Measured in browser |

---

## Offline use

1. Start backend + frontend once (so RR-1 can cache if the network is available).  
2. Disconnect from the internet.  
3. Continue using Today, Assessment, Readiness Gate, Digital Twin, Trends, What-If, Replay, and Telemetry from the local cache / SQLite.

---

## Tests

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest -q
```

Prototype decision rules: [`data/PROTOTYPE_THRESHOLDS.md`](data/PROTOTYPE_THRESHOLDS.md) — demo thresholds only, not clinical or official NASA medical limits.

---

## Project layout

```
/frontend   Next.js UI
/backend    FastAPI services + routers
/data       SQLite, fixtures, NASA cache, keys, encrypted reports
```
