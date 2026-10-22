# TraceOps: Evidence-First Data Incident Investigation

> **ExaThon India 2026 Exasol Open Build Challenge**  
> **Track 04:** The Work Behind the Work

TraceOps investigates synthetic data-pipeline incidents by correlating pipeline run events, dataset dependencies, data-quality checks, and business KPI snapshots. It separates empirical evidence from investigative hypotheses, identifies affected downstream reports and KPIs, and recommends concrete recovery actions.

## Architecture Overview

```text
Vite Frontend (React)
http://localhost:5173
         |
         | HTTP / CORS / JSON
         v
TraceOps API (FastAPI + PyExasol)
http://127.0.0.1:8000
         |
         v
Exasol Personal (Local)
127.0.0.1:8563 (TLS)
```

## Current Status (Phase 1 & 2 Completed)

- [x] **FastAPI Backend Core:** Initialized with CORS configured for `http://localhost:5173`.
- [x] **Secure Exasol Connection Manager:** Reads credentials securely from `EXASOL_PASSWORD` or the local Starter Kit credentials file.
- [x] **TLS & Self-Signed Handling:** Local TLS configuration enabled with self-signed certificate bypass restricted to local development.
- [x] **Health Check Endpoints:** Verified through the automated test suite.
- [x] **Credential Safety:** Secrets and connection passwords are not intentionally printed, committed, or exposed in error payloads.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Service root with metadata and endpoint links |
| `GET` | `/api/health` | API service health status |
| `GET` | `/api/exasol/health` | Executes `SELECT 1 AS test_value` against Exasol |
| `GET` | `/docs` | Interactive Swagger UI API documentation |
| `GET` | `/redoc` | OpenAPI ReDoc specification |

## Quickstart & Local Verification

### 1. Prerequisites

- Python 3.10+ and a backend virtual environment
- Exasol Personal running locally at `127.0.0.1:8563`
- Windows PowerShell

### 2. Start the Backend API

Run from the project root:

```powershell
& .\backend\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --reload
```

### 3. Verify in a Browser

- Swagger UI: http://127.0.0.1:8000/docs
- API health: http://127.0.0.1:8000/api/health
- Exasol connectivity: http://127.0.0.1:8000/api/exasol/health

## Upcoming Roadmap

1. **Database Schema & Synthetic Incident Seeding**
   - Pipeline run log events table
   - Dataset dependency DAG graph table
   - Data quality check assertions table
   - Business KPI metrics snapshot table

2. **Investigation Engine**
   - Correlate failure cascades and anomaly timelines
   - Evidence-based root-cause ranking
   - Downstream blast-radius analysis

3. **Frontend Dashboard (Vite + React)**
   - Interactive incident investigation workbench
   - Evidence-versus-hypothesis separation view
   - Impacted KPI and recovery-action dashboard
