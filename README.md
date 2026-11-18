<div align="center">

# 🔍 PhisLens

**Local-first, evidence-grounded phishing email analysis.**

Paste an email or drop in an `.eml` file and get an explainable risk score, where every point traces back to a specific piece of evidence. Nothing leaves your machine.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-7-646CFF?logo=vite&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-experiment-F7931E?logo=scikitlearn&logoColor=white)
![Local only](https://img.shields.io/badge/data-stays%20local-2ea44f)


</div>

---

##Screenshots

<img width="1871" height="922" alt="Screenshot 2026-11-19 002840" src="https://github.com/user-attachments/assets/0a1ffbba-3406-45aa-a3dd-61f2b4c2a375" />
<img width="1511" height="788" alt="Screenshot 2026-11-19 002934" src="https://github.com/user-attachments/assets/d7b5a258-8ccd-4723-a1a3-9d2af082b2d9" />
<img width="1583" height="892" alt="Screenshot 2026-11-19 003030" src="https://github.com/user-attachments/assets/387e7ae4-33a1-4653-8ca9-1de75d7e2c25" />


---

## Overview

Most phishing "detectors" hand a single opaque score to the user. PhisLens takes the opposite approach: a **transparent, rule-based analyzer** that lists each finding, the evidence behind it, and the points it contributed to the final score, so you can see *why* a message looks suspicious and decide for yourself.

A scikit-learn text model is included as a **separate, clearly labeled experiment**. It never influences the risk score.

## Features

- **Explainable scoring**: every finding shows its evidence and point contribution.
- **Two input modes**: paste raw email text or upload an `.eml` file.
- **Header-aware**: reads SPF, DKIM, and DMARC results when they are already present in pasted headers.
- **Fully local**: the UI talks only to a FastAPI service bound to `127.0.0.1`.
- **No persistence**: email content is never written to disk or a database.
- **No external calls**: no threat-intelligence lookups, no AI provider APIs, no telemetry.
- **Safe by design**: attachments are never opened or executed.
- **Separate ML experiment**: a text classifier trained at startup on fictional sample data, kept apart from the score.

## Privacy model

| Question | Answer |
| --- | --- |
| Where is email content sent? | Only from the browser to `127.0.0.1:8000` on your own computer. |
| Is anything stored? | No. No files, no database. |
| Are third-party services contacted? | No. No threat-intel feeds, no AI APIs. |
| Is network access needed? | Only on first run, to download software dependencies. Email content is never part of that. |

## How it works

```
 ┌──────────────────────────┐      /api (proxied)      ┌──────────────────────────────┐
 │  React + Vite frontend   │ ───────────────────────▶ │  FastAPI backend (127.0.0.1) │
 │  127.0.0.1:5173          │ ◀─────────────────────── │  127.0.0.1:8000              │
 └──────────────────────────┘      JSON results        │                              │
                                                       │  ├─ Email / .eml parsing     │
                                                       │  ├─ Rule engine → risk score │
                                                       │  └─ ML experiment (separate) │
                                                       └──────────────────────────────┘
```

1. The frontend sends pasted text or raw `.eml` bytes to the local API.
2. The backend parses the message and runs explicit detection rules.
3. Each triggered rule returns its **evidence** and **point contribution**.
4. The score is the sum of those contributions. The ML model's output is reported on its own and is **not** part of the score.

<!-- TODO: add a table of your detection rules, e.g.

### Detection rules

| Rule | What it looks for | Points |
| --- | --- | --- |
| ... | ... | ... |
-->

## Getting started

### Prerequisites

- **Python** 3.10 or newer
- **Node.js** 20.19 or newer (includes `npm`)

### Windows (one click)

1. Clone the repository and open the project folder.
2. Double-click **`start.bat`**.
3. On first run it creates a project-local virtual environment and installs Python and JavaScript dependencies (internet required for this step only).
4. The app opens at **http://127.0.0.1:5173**. Keep both server windows open while using it.

### macOS / Linux (manual)

```bash
# 1. Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

```bash
# 2. Frontend (in a second terminal)
npm install
npm run dev
```

Then open **http://127.0.0.1:5173**.

### Windows (manual)

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

```powershell
npm run dev
```

> Both servers bind to the local machine only. PhisLens is a local development app, not a static-site deployment.

## Development

| Task | Command |
| --- | --- |
| Run the frontend dev server | `npm run dev` |
| Build a production frontend bundle | `npm run build` |
| Preview the production build | `npm run preview` |
| Run backend tests (Windows) | `.\.venv\Scripts\python.exe -m unittest discover -s backend -p "test_*.py"` |
| Run backend tests (macOS/Linux) | `python -m unittest discover -s backend -p "test_*.py"` |

## Project structure

```
PhisLens/
├── backend/            # FastAPI service, parsing, rule engine, ML experiment, tests
├── src/                # React frontend (entry: main.jsx)
├── index.html          # Vite HTML entry point
├── vite.config.js      # Dev server + /api proxy to the backend
├── requirements.txt    # Python dependencies
├── package.json        # JavaScript dependencies and scripts
├── start.bat           # Windows one-click launcher
└── README.md
```

## Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, Vite 7 |
| Backend | Python, FastAPI, Uvicorn |
| ML experiment | scikit-learn |
| Testing | Python `unittest` |


