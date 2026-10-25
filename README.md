# TraceOps: Evidence-First Data Incident Investigation Platform

[![ExaThon India 2026](https://img.shields.io/badge/ExaThon_India-2026_Submission-blue?style=for-the-badge&logo=exasol)](https://github.com/sandhiyasri390/TraceOps)
[![Track 04](https://img.shields.io/badge/Track_04-The_Work_Behind_the_Work-orange?style=for-the-badge)](https://github.com/sandhiyasri390/TraceOps)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![Live Demo](https://img.shields.io/badge/Live_App-trace--ops.vercel.app-success?style=for-the-badge&logo=vercel)](https://trace-ops.vercel.app)
[![Demo Video](https://img.shields.io/badge/Demo_Video-Google_Drive-red?style=for-the-badge&logo=googledrive)](https://drive.google.com/file/d/1SASz2wZ4TwMLNJgy3J2Be0M6YX1tBfWW/view?usp=sharing)
[![Pitch Deck](https://img.shields.io/badge/Pitch_Deck-PDF-purple?style=for-the-badge&logo=adobeacrobatreader)](./TraceOps_Academic.pptx%20(1).pdf)

> **ExaThon India 2026 Exasol Open Build Challenge**  
> **Track 04:** The Work Behind the Work  
> **Author:** Sandhiyasri  
> **GitHub Repository:** [https://github.com/sandhiyasri390/TraceOps](https://github.com/sandhiyasri390/TraceOps)  
> **Public Web Application:** [https://trace-ops.vercel.app](https://trace-ops.vercel.app/)  
> **Backend API (Cloud):** [https://traceops-backend-x2mu.onrender.com](https://traceops-backend-x2mu.onrender.com/)  
> **Demo Walkthrough Video:** [Watch the TraceOps Demo on Google Drive](https://drive.google.com/file/d/1SASz2wZ4TwMLNJgy3J2Be0M6YX1tBfWW/view?usp=sharing)  
> **Pitch Deck (Root):** [View TraceOps Pitch Deck (Root Copy)](./TraceOps_Academic.pptx%20(1).pdf)  
> **Pitch Deck (Docs Folder):** [View TraceOps Pitch Deck (Docs Copy)](./docs/TraceOps_Academic.pdf)

---

## Executive Summary & Problem Statement

### The Problem
Modern enterprise data platforms consist of hundreds of interdependent data pipelines, message queues, staging transformations, dimensional models, and analytical dashboards. When pipelines fail, they rarely fail cleanly:
- **Silent Data Corruptions:** Upstream transformation logic errors (e.g., currency multiplier bugs, schema drifts) complete with a misleading `SUCCESS` exit status while corrupting financial aggregations downstream.
- **Cascading Failures:** A single database lock timeout in a raw warehouse staging layer triggers alert storms across dozens of downstream marts and executive reports.
- **Disjointed Telemetry:** Pipeline run logs, data-quality test assertions, dataset lineage graphs, and business KPI metrics reside in fragmented silos.

### Who Is Affected?
- **Data Engineers & Analytics Engineers:** Spend hours manually reading execution logs, reconstructing Directed Acyclic Graphs (DAGs), and identifying where data diverged.
- **Incident Responders & Data Platform Leads:** Must triage severity, identify blast radii, and decide whether to halt downstream ingestion or initiate backfills.
- **Business Stakeholders & Finance Leads:** Rely on executive KPI dashboards and suffer loss of trust when revenue or inventory metrics show erroneous numbers without explanation.

### Why It Matters
Without automated correlation, mean-time-to-detection (MTTD) and mean-time-to-resolution (MTTR) stretch from minutes to days. Finger-pointing occurs between ingestion teams and BI teams, and manual interventions risk secondary corruptions.

### The TraceOps Solution
**TraceOps** is an evidence-first automated data incident investigation workbench powered by **Exasol**. It correlates pipeline execution logs, dataset dependency graphs, automated data quality assertions, and business KPI metrics to:
1. **Strictly Separate Empirical Evidence from Investigative Hypotheses:** Every reported incident highlights confirmed facts (logged errors, failed assertions) versus probabilistic root-cause rankings.
2. **Prioritize Root Causes with Upstream Weighting:** Upstream ingestion sources are prioritized over downstream symptoms, avoiding the trap of treating downstream mart alerts as root causes.
3. **Map the Downstream Blast Radius:** Visualizes impacted analytical models and business KPIs across a 5-stage topological lineage DAG.
4. **Prescribe Safe, Read-Only Recovery Actions:** Generates concrete, non-destructive audit and remediation steps before any manual database intervention.

---

## Key Features

### 1. Root-Cause Ranking Engine
- Automated hypothesis evaluation using a multi-factor scoring model (topological depth, error severity, status anomalies, and assertion failures).
- Strict epistemic honesty: Confidence scores are mathematically bounded (maximum confidence capped at 0.95; no hypothesis claims 1.0 certainty prematurely).
- Distinguishes **Empirical Evidence** (concrete Exasol database records) from **Hypotheses** (inferred candidate root causes).

### 2. Topological Data Lineage & Blast-Radius Traversal
- Interactive Directed Acyclic Graph (DAG) covering **Stage 01: Raw Ingestion** through **Stage 05: Analytics & KPIs**.
- In-degree and out-degree analysis, topological ordering, and cycle detection.
- Visual distinction between direct component health and downstream blast-radius impact.
- Identifies silent corruption paths where healthy pipeline statuses propagate bad data into downstream nodes.

### 3. Enterprise Data Quality Workbench
- Full empirical catalog of 13 data quality assertion checks across core tables.
- Real-time filtering by status (`PASSED`, `FAILED`, `WARNING`), severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`), dataset name, and free-text search.
- Side-by-side inspection of expected vs. actual values, observed timestamps, and specific evidence descriptions.

### 4. 5 Realistic Enterprise Synthetic Incident Scenarios
TraceOps includes 5 curated, pre-seeded incident scenarios reflecting real-world data engineering crises:
1. `CASE-RAW_ECOMMERCE_ORDERS`: Ingestion pipeline timeout causing missing daily sales aggregates.
2. `CASE-RAW_CRM_EXPORT`: Duplicate primary keys triggering customer dimension join explosion.
3. `CASE-RAW_POS_TRANSACTIONS`: **Silent Corruption** — Pipeline reported `SUCCESS` but currency multiplier logic produced corrupted transaction sums.
4. `CASE-RAW_WEB_CLICKSTREAM`: Upstream schema drift / malformed JSON causing sessionization failures.
5. `CASE-RAW_WMS_BALANCES`: Database lock contention producing stale inventory snapshots and false stockout alerts.

### 5. Transparent Demo Data Mode
When deployed to public cloud environments where access to the private local database is restricted, TraceOps seamlessly and transparently activates an interactive **DEMO DATA** mode with explicit UI badges and warning banners, ensuring judges can evaluate every workflow without exposing private credentials or open ports.

---

## System Architecture

```
                             +-----------------------------------------------+
                             |             Vite + React Frontend             |
                             |           https://trace-ops.vercel.app        |
                             |   (Investigation Workbench, Lineage, Quality) |
                             +-----------------------+-----------------------+
                                                     |
                                         HTTPS / CORS | REST JSON
                                                     v
                             +-----------------------------------------------+
                             |               TraceOps API Engine             |
                             |                 FastAPI (Python)              |
                             |         Render Cloud / Local Uvicorn          |
                             +-----------------------+-----------------------+
                                                     |
                                     PyExasol Driver | TLS Encrypted
                                                     v
+----------------------------------------------------------------------------------------------------+
|                                    Exasol In-Memory Database                                       |
|                                       Schema: TRACEOPS                                             |
|                                                                                                    |
|  +--------------------+  +-----------------------+  +----------------------+  +-----------------+  |
|  |   PIPELINE_RUNS    |  | DATASET_DEPENDENCIES  |  | DATA_QUALITY_CHECKS  |  |   KPI_METRICS   |  |
|  |  (Telemetry/Logs)  |  |    (Lineage Graph)    |  |  (Assertion Checks)  |  | (Business Impact)| |
|  +--------------------+  +-----------------------+  +----------------------+  +-----------------+  |
+----------------------------------------------------------------------------------------------------+
```

---

## Role of Exasol in TraceOps

Exasol serves as the foundational high-performance analytical engine for TraceOps:
- **PyExasol Native Integration:** Communicates with Exasol using the native WebSocket protocol over TLS, leveraging Exasol's columnar in-memory speed.
- **Relational Lineage Modeling:** Stores graph nodes and dependency edges in `DATASET_DEPENDENCIES` with depth indices, in/out degrees, and criticality flags.
- **Telemetry & Quality Check Aggregation:** Evaluates empirical test assertions (`DATA_QUALITY_CHECKS`) and pipeline telemetry (`PIPELINE_RUNS`) in sub-second query latency.
- **Dynamic Blast-Radius Analysis:** Executes fast join operations across dependency paths to determine impacted KPIs and downstream tables during active incidents.
- **Secure Credential Discovery:** Implements zero-trust credential handling, reading passwords exclusively from `EXASOL_PASSWORD` or the local Exasol Starter Kit secure credential store (`%USERPROFILE%\.exasol-starter-kit\credentials\personal_sys_password`).

---

## Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Database** | **Exasol Personal** (Local in-memory analytical database), **PyExasol** |
| **Backend API** | **Python 3.10+**, **FastAPI**, **Uvicorn**, **Pydantic v2**, **NetworkX** (graph algorithms) |
| **Frontend UI** | **React 19**, **Vite**, **Vanilla Enterprise CSS** (glassmorphic theme, responsive layouts), **Lucide React** (icons) |
| **Validation & Testing** | **Python automated test suites** (`test_quality.py`, `test_lineage.py`, `test_investigations.py`) |
| **Deployment** | **Vercel** (Frontend static CDN), **Render** (Containerized FastAPI backend) |

---

## Submission Links & Artifacts

- **GitHub Repository:** [https://github.com/sandhiyasri390/TraceOps](https://github.com/sandhiyasri390/TraceOps)
- **Live Public Application:** [https://trace-ops.vercel.app](https://trace-ops.vercel.app/)
- **Public API Documentation (Swagger):** [https://traceops-backend-x2mu.onrender.com/docs](https://traceops-backend-x2mu.onrender.com/docs)
- **Demo Walkthrough Video:** [https://drive.google.com/file/d/1SASz2wZ4TwMLNJgy3J2Be0M6YX1tBfWW/view?usp=sharing](https://drive.google.com/file/d/1SASz2wZ4TwMLNJgy3J2Be0M6YX1tBfWW/view?usp=sharing)
- **Academic Pitch Deck (Root File):** [./TraceOps_Academic.pptx (1).pdf](./TraceOps_Academic.pptx%20(1).pdf)
- **Academic Pitch Deck (Docs Copy):** [./docs/TraceOps_Academic.pdf](./docs/TraceOps_Academic.pdf)
- **Open-Source License:** [MIT License](LICENSE)

---

## Deployment & Operational Status (Truthful Architecture Note)

To ensure full transparency during evaluation:

1. **Local Development Environment (Live Exasol Mode):**
   - Exasol Personal runs locally at `127.0.0.1:8563`.
   - The local backend connects directly to Exasol via PyExasol with TLS encryption.
   - Endpoint `GET /api/exasol/health` verifies live database execution (`SELECT 1 AS test_value`).
   - All 3 automated test suites pass against live schema assertions.

2. **Public Cloud Deployment (Interactive Demo Fallback Mode):**
   - The frontend is publicly accessible on **Vercel** (`https://trace-ops.vercel.app`).
   - The backend is deployed on **Render** (`https://traceops-backend-x2mu.onrender.com`).
   - Because Exasol Personal runs on a private workstation without a public ingress tunnel, Render's cloud backend reports connection refusal for `127.0.0.1:8563`.
   - **TraceOps handles this gracefully:** Rather than crashing or showing empty errors, the application displays an interactive **DEMO DATA** fallback mode with explicit amber badges. Judges and users can interactively explore the complete workbench, DAG lineage graphs, quality checks, and ranking algorithms safely without opening private database ports.

---

## Local Setup & Run Guide

### 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+** & `npm`
- **Exasol Personal** running locally on port `8563` (via Exasol Starter Kit)
- **Git**

### 2. Clone the Repository
```powershell
git clone https://github.com/sandhiyasri390/TraceOps.git
cd TraceOps
```

### 3. Backend Setup
Create and activate a virtual environment, install dependencies, and launch FastAPI:

```powershell
# Navigate to backend and create virtual environment
cd backend
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install required dependencies
pip install -r requirements.txt

# Start the FastAPI backend
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend API will be available at:
- Root API & Metadata: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Interactive Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- API Health Status: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)
- Exasol Live Connectivity: [http://127.0.0.1:8000/api/exasol/health](http://127.0.0.1:8000/api/exasol/health)

### 4. Frontend Setup
In a separate terminal window, start the React + Vite frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173/](http://localhost:5173/) in your browser to interact with the TraceOps dashboard.

### 5. Running the Verification Test Suites
TraceOps includes three comprehensive automated verification suites:

```powershell
# Run from project root

# 1. Validate Data Quality Checks (10 tests)
backend\.venv\Scripts\python.exe backend/test_quality.py

# 2. Validate Data Lineage & DAG Topology (9 tests)
backend\.venv\Scripts\python.exe backend/test_lineage.py

# 3. Validate Root-Cause Ranking Engine (10 tests)
backend\.venv\Scripts\python.exe backend/test_investigations.py
```

Expected output:
```text
==================================================================
ALL 10 QUALITY CHECK VALIDATION CHECKS PASSED WITH ZERO DEFECTS!
==================================================================
ALL 9 LINEAGE VALIDATION CHECKS PASSED WITH ZERO DEFECTS!
==================================================================
ALL 10 VERIFICATION CHECKS PASSED WITH ZERO DEFECTS!
==================================================================
```

---

## API Reference Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | API service root with metadata and navigation links |
| `GET` | `/api/health` | Service liveness health check |
| `GET` | `/api/exasol/health` | Live Exasol connectivity check (`SELECT 1`) |
| `GET` | `/api/investigations` | Incident cases with empirical evidence and ranked hypotheses |
| `GET` | `/api/lineage` | 5-stage dependency DAG graph, cycle checks, and summaries |
| `GET` | `/api/quality-checks` | Empirical quality checks with status, severity, and dataset filters |
| `GET` | `/docs` | Interactive OpenAPI Swagger UI documentation |

---

## License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.
