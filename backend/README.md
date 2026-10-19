# Finance Complaints Medallion — Backend API

Modular FastAPI backend service for the Finance Complaints Medallion platform. It loads, validates, and serves analytics over CFPB financial consumer complaint records using in-memory pandas computations with strict schema boundaries.

---

## 1. Quickstart & Local Setup

### Prerequisites
- Python 3.12+
- Virtual environment tool (`venv`)

### Setup Steps
```bash
# 1. Navigate to backend directory
cd backend

# 2. Create and activate virtual environment
python -m venv .venv
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# 3. Install development dependencies
pip install -r requirements-dev.txt

# 4. Copy environment configuration
cp .env.example .env

# 5. Run automated test suite
python -m pytest

# 6. Start API server locally
python -m uvicorn app.main:app --reload --port 8000
```
Interactive OpenAPI documentation will be available at: `http://localhost:8000/docs`

---

## 2. Data Modes (`DATA_MODE`)

The backend abstracts data ingestion behind the `DataSource` protocol, supporting three operational modes:

| Mode | Configuration | Description |
| :--- | :--- | :--- |
| `fixture` (Default) | `DATA_MODE=fixture` | Loads ~40 hand-verified complaints from `tests/fixtures/tiny/`. Ideal for fast, offline unit testing without external data dependencies. |
| `local_snapshot` | `DATA_MODE=local_snapshot` | Loads full 62,516 complaints reproduced locally in `backend/.local_data/`. Generated via `python scripts/build_local_snapshot.py`. |
| `azure` | `DATA_MODE=azure` | Connects directly to Azure Data Lake Storage Gen2 (`financecomplaintssa`) via `DefaultAzureCredential` (production App Service) or connection string (dev). |

### Generating the Local Snapshot
To build the realistic offline dataset from the repository root Bronze CSVs:
```bash
python scripts/build_local_snapshot.py
python scripts/reconcile_with_gold.py
```

---

## 3. Testing and Code Quality Commands

All quality gates must pass before commits:

```bash
# Run pytest with code coverage
python -m pytest --cov=app --cov-report=term-missing

# Run Ruff linter
python -m ruff check .

# Run Ruff code formatter check
python -m ruff format --check .

# Run Mypy static type checker
python -m mypy app

# Probe Azure Data Lake Storage Gen2 access (requires Azure credentials)
python scripts/check_azure_access.py
```

---

## 4. Key Endpoints Implemented in Phase 2

- `GET /health/live`: Process liveness probe (returns HTTP 200 with `status: "alive"` and request ID).
- `GET /health/ready`: Data readiness probe (returns HTTP 200 with snapshot status, row count, and origin when valid data is loaded; HTTP 503 if data is unavailable).
