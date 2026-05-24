# General Ledger Forensic Audit Suite

A production-ready desktop tool that accepts General Ledger exports from Indian accounting software (Tally, SAP, Busy, Marg, CSV) and runs parallel forensic agents to detect duplicate payments, anomalies, and reconciliation variances.

## Features

1.  **Structure Detection**: Auto-detects column headers, date formats, and party divisions (column-based or row-header-based layouts).
2.  **FIFO Aging**: Matches credits and debits in sequence to age outstanding items into 6 buckets. Includes amount and count toggle views.
3.  **Duplicate Payment Detective**: Scans for exact matches, near-duplicates, same-day duplicates, and round numbers.
4.  **Forensic Anomalies**: Identifies ghost payments, holiday postings, same/next day reversals, split payments, round-trip transactions, etc.
5.  **Reconciliation Math Check**: Recalculates running balances from opening values, checks stated vs recalculated balances, and marks negative balance intervals.
6.  **Styled Excel Export & CA Memo**: Downloads formatted spreadsheets and generates Chartered Accountant style executive memos.

---

## Installation & Running Locally

### Prerequisites

-   Python 3.11+
-   Node.js 18+
-   Vite

### 1. Backend Server Setup

```bash
cd backend
python -m venv venv
source venv/Scripts/activate  # on Windows
pip install -r requirements.txt
```

Create a `.env` file in `/backend` to configure the LLM:
```env
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.openai.com/v1     # or DeepSeek, OpenRouter, etc.
LLM_MODEL=gpt-4-turbo                     # e.g., deepseek-chat, gpt-4o, etc.
```

Start the FastAPI server:
```bash
uvicorn main:app --reload --port 8000
```

### 2. Frontend Web Setup

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your web browser.

---

## Running with Docker Compose

To boot up backend + frontend containers together:

```bash
# Set your API key in the terminal session, or place it in .env
docker-compose up --build
```

Access the application at [http://localhost:5173](http://localhost:5173). All uploaded datasets and SQLite databases will remain persistent in `./backend/`.
