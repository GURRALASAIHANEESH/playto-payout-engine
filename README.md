
# Playto Payout Engine

Playto helps Indian agencies, freelancers, and online businesses collect international payments and receive INR payouts. This is the payout engine — merchants have balances, request payouts, and track payout status.

## Stack

- **Backend:** Django 5.1 + Django REST Framework
- **Frontend:** React 18 + Tailwind CSS
- **Database:** PostgreSQL 16
- **Background Jobs:** Celery + Redis
- **Money Format:** All values are integer paise (₹1 = 100 paise). No floats. No decimals.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose

## Project Structure

```
playto-payout-engine/
├── backend
│   ├── payouts
│   │   ├── management
│   │   │   ├── commands
│   │   │   │   ├── __init__.py
│   │   │   │   └── seed_data.py
│   │   │   └── __init__.py
│   │   ├── migrations
│   │   │   ├── 0001_initial.py
│   │   │   └── __init__.py
│   │   ├── tests
│   │   │   ├── __init__.py
│   │   │   ├── test_balance.py
│   │   │   ├── test_concurrency.py
│   │   │   ├── test_idempotency.py
│   │   │   ├── test_retry.py
│   │   │   └── test_state_machine.py
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── services.py
│   │   ├── state_machine.py
│   │   ├── tasks.py
│   │   ├── urls.py
│   │   └── views.py
│   ├── playto
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── celery.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── Procfile
│   ├── manage.py
│   └── requirements.txt
├── frontend
│   ├── src
│   │   ├── api
│   │   │   └── client.js
│   │   ├── components
│   │   │   ├── BalanceCard.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── LedgerTable.jsx
│   │   │   ├── PayoutForm.jsx
│   │   │   └── PayoutHistory.jsx
│   │   ├── hooks
│   │   │   └── usePolling.js
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── package-lock.json
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   └── vite.config.js
├── .gitignore
├── EXPLAINER.md
├── README.md
└── docker-compose.yml
```

## Setup

### 1. Start Infrastructure

```bash
docker-compose up -d
```

This starts PostgreSQL on port **5434** and Redis on port **6380**.

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Set environment variables (Linux/Mac):

```bash
export DB_PORT=5434
export CELERY_BROKER_URL=redis://localhost:6380/0
export CELERY_RESULT_BACKEND=redis://localhost:6380/0
```

Windows PowerShell:

```powershell
$env:DB_PORT="5434"
$env:CELERY_BROKER_URL="redis://localhost:6380/0"
$env:CELERY_RESULT_BACKEND="redis://localhost:6380/0"
```

Run migrations and seed data:

```bash
python manage.py migrate
python manage.py seed_data
```

Start the Django server:

```bash
python manage.py runserver 8001
```

### 3. Celery (two separate terminals, same env vars)

```bash
celery -A playto worker --loglevel=info --pool=solo
```

```bash
celery -A playto beat --loglevel=info
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

## API Endpoints

All endpoints are prefixed with `/api/v1/`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/merchants/<id>/balance/` | Available and held balance |
| GET | `/merchants/<id>/ledger/` | Credit and debit history |
| GET | `/merchants/<id>/payouts/` | All payouts for merchant |
| POST | `/payouts/` | Create a payout request |
| GET | `/payouts/<id>/` | Single payout detail |

### POST /payouts/

Headers:

| Header | Required | Description |
|--------|----------|-------------|
| Content-Type | Yes | `application/json` |
| X-Merchant-ID | Yes | Merchant ID |
| Idempotency-Key | Yes | Unique key per request (expires 24h) |

Body:

```json
{
  "amount_paise": 10000,
  "bank_account_id": 1
}
```

## Payout State Machine

```
pending → processing → completed
                     → failed
```

No other transitions are allowed.

## Background Jobs

| Task | Interval | Purpose |
|------|----------|---------|
| `process_pending_payouts` | Every 5s | Picks up pending payouts and processes them |
| `retry_stuck_payouts` | Every 10s | Finds processing payouts stuck longer than 30s |

Retries use exponential backoff (4s, 8s, 16s) with a max of 3 attempts. After 3 failed attempts, the payout is marked as failed and held funds are released.

## Seeded Merchants

| Merchant | Balance | Bank Account |
|----------|---------|--------------|
| Acme Freelancers | ₹1,00,000 | HDFC •••• 1234 |
| DesignStudio India | ₹1,00,000 | ICICI •••• 5678 |
| CodeCraft Agency | ₹1,60,000 | SBI •••• 9012 |

## Tests

```bash
cd backend
python manage.py test payouts.tests --verbosity=2
```

30 tests covering:

| Suite | Count | Coverage |
|-------|-------|----------|
| Balance calculation | 7 | Empty, credits, pending hold, processing hold, completed debit, failed release, mixed states |
| State machine | 11 | All valid transitions, all illegal transitions blocked, debit/no-debit on complete/fail |
| Retry logic | 6 | Retry completes, retry fails, max retries → fail, hold released, attempt count, skip non-processing |
| Concurrency | 2 | Two simultaneous payouts no overdraft, exact balance then reject |
| Idempotency | 4 | Same key same response, different keys, cross-merchant, key count unchanged |

## Architecture

See [EXPLAINER.md](EXPLAINER.md) for detailed explanations of:

- Ledger-based balance calculation with DB-level aggregation
- Row-level locking with SELECT FOR UPDATE for concurrency safety
- Idempotency key lifecycle including in-flight request handling
- State machine enforcement and atomic money movement