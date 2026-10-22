# TraceOps: Evidence-First Data Incident Investigation

> **ExaThon India 2026 Exasol Open Build Challenge**  
> **Track 04:** The Work Behind the Work

TraceOps investigates synthetic data-pipeline incidents by correlating pipeline run events, dataset dependencies, data-quality checks, and business KPI snapshots. It separates empirical evidence from investigative hypotheses, identifies affected downstream reports and KPIs, and recommends concrete recovery actions.

---

## Architecture Overview

```
                                    +-----------------------------------+
                                    |       Vite Frontend (React)       |
                                    |       http://localhost:5173       |
                                    +-----------------+-----------------+
                                                      |
                                          HTTP / CORS | JSON
                                                      v
+-----------------------------------+       +---------+-------------------------+
|     Exasol Personal (Local)       |<----->|           TraceOps API            |
|       127.0.0.1:8563 (TLS)        |       |        FastAPI + PyExasol         |
+-----------------------------------+       |       http://127.0.0.1:8000       |
                                            +-----------------------------------+
```

---

## Current Status (Phase 1 & 2 Completed)

- [x] **FastAPI Backend Core**: Initialized with CORS configured for `http://localhost:5173`.
- [x] **Secure Exasol Connection Manager**: Reads credentials securely from `EXASOL_PASSWORD` or the local Starter Kit (`%USERPROFILE%\.exasol-starter-kit\credentials\personal_sys_password`).
- [x] **TLS & Self-Signed Handling**: Local TLS configuration enabled with self-signed certificate bypass strictly restricted to local development environments.
- [x] **Health Check Endpoints**: Verified operational via automated test suite.
- [x] **Credential Safety**: Secrets and connection passwords are never printed, committed, or exposed in error payloads.

---

## API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Service root with metadata and endpoint links |
| `GET` | `/api/health` | API service health status |
| `GET` | `/api/exasol/health` | Executes `SELECT 1 AS test_value` against Exasol |
| `GET` | `/docs` | Interactive Swagger UI API documentation |
| `GET` | `/redoc` | OpenAPI ReDoc specification |

---

## Quickstart & Local Verification

### 1. Prerequisites
- Python 3.10+ with virtual environment in `backend\.venv`
- Exasol Personal running locally at `127.0.0.1:8563`
- Windows PowerShell

### 2. Start the Backend API
Run using the virtual environment interpreter directly (bypassing PowerShell execution-policy restrictions):

```powershell
& .\backend\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --reload
```

### 3. Verify in Browser
- Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for Swagger UI.
- Open [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health) to verify API service.
- Open [http://127.0.0.1:8000/api/exasol/health](http://127.0.0.1:8000/api/exasol/health) to verify Exasol connectivity.

---

## Upcoming Roadmap

1. **Database Schema & Synthetic Incident Seeding**:
   - Pipeline run log events table
   - Dataset dependency DAG graph table
   - Data quality check assertions table
   - Business KPI metrics snapshot table
2. **Investigation Engine**:
   - Correlate failure cascades and anomaly timeline
   - Evidence-based root-cause ranking
   - Downstream blast radius analysis
3. **Frontend Dashboard (Vite + React)**:
   - Interactive incident investigation workbench
   - Evidence vs. hypothesis separation view
   - Impacted KPI & recovery action dashboard
