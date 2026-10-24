
"""
TraceOps API: Evidence-First Data Incident Investigation
ExaThon India 2026 ΓÇö Track 04
Demo fallback enabled when Exasol is unavailable.
"""

from datetime import datetime, timezone
import logging
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, status as http_status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import (
    check_exasol_health,
    get_incident_investigations,
    get_quality_checks,
)
from ranking import get_investigation_cases
from lineage import get_lineage_data

logger = logging.getLogger("traceops.api")

app = FastAPI(
    title="TraceOps API",
    description="Evidence-First Data Incident Investigation",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

default_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
    "https://trace-ops.vercel.app",
]

raw_origins = os.environ.get(
    "ALLOWED_ORIGINS", ",".join(default_origins)
)
origins = list(dict.fromkeys(
    [x.strip() for x in raw_origins.split(",") if x.strip()]
    + default_origins
))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------
# DEMO DATA
# These are illustrative records, not live Exasol evidence.
# ---------------------------------------------------------

DEMO_INVESTIGATIONS = [
    {
        "case_id": "CASE-RAW_ECOMMERCE_ORDERS",
        "title": "Upstream E-Commerce Timeout Causing GMV Shortfall",
        "flow_name": "E-Commerce Order Processing Flow",
        "root_dataset": "raw_ecommerce_orders",
        "severity": "CRITICAL",
        "status": "ACTIVE_INVESTIGATION",
        "first_observed_at": "2026-10-22T08:10:00+00:00",
        "last_observed_at": "2026-10-22T08:15:00+00:00",
        "silent_data_corruption": False,
        "affected_datasets": [
            "raw_ecommerce_orders",
            "stg_ecommerce_orders",
            "fct_daily_sales",
            "mart_revenue",
        ],
        "downstream_reports": [
            "Executive Revenue Dashboard",
            "Daily GMV Report",
        ],
        "associated_kpis": [
            {
                "kpi_name": "Gross Merchandise Value",
                "expected_value": 1250000,
                "actual_value": 790000,
                "deviation_percent": -36.8,
                "business_impact": "Revenue reporting may be incomplete.",
            }
        ],
        "confirmed_evidence": [
            {
                "evidence_id": "DEMO-EV-001",
                "evidence_type": "PIPELINE_EXECUTION",
                "component": "pipe_raw_ecommerce_orders",
                "status": "FAILED",
                "severity": "CRITICAL",
                "observed_at": "2026-10-22T08:10:00+00:00",
                "error_code": "ERR_DB_CONN_TIMEOUT",
                "details": "DEMO: Simulated upstream database timeout.",
            },
            {
                "evidence_id": "DEMO-EV-002",
                "evidence_type": "DATA_QUALITY_ASSERTION",
                "component": "stg_ecommerce_orders",
                "check_status": "FAILED",
                "severity": "CRITICAL",
                "observed_at": "2026-10-22T08:15:00+00:00",
                "details": "DEMO: Row count fell below the expected threshold.",
            },
        ],
        "inferred_hypotheses": [
            {
                "hypothesis_id": "DEMO-HYP-001",
                "candidate_root_cause": "pipe_raw_ecommerce_orders",
                "dataset_name": "raw_ecommerce_orders",
                "pipeline_name": "pipe_raw_ecommerce_orders",
                "confidence_score": 0.88,
                "confidence_level": "HIGH",
                "is_confirmed": False,
                "rank": 1,
                "reasoning": (
                    "[DEMO HYPOTHESIS] The upstream timeout may explain "
                    "the downstream row-count and revenue anomalies. "
                    "Operator verification is required."
                ),
                "score_breakdown": {
                    "raw_score": 92,
                    "max_raw_score": 100,
                    "confidence_score": 0.88,
                    "max_confidence_limit": 0.95,
                    "scoring_details": [
                        "DEMO: Upstream source candidate",
                        "DEMO: Earliest observed event",
                        "DEMO: Simulated failure evidence",
                        "DEMO: Downstream KPI impact",
                    ],
                },
            }
        ],
        "top_candidate_root_cause": "pipe_raw_ecommerce_orders",
        "top_confidence_score": 0.88,
        "recommended_recovery_actions": [
            "[Read-Only Verification] Check upstream database availability and connectivity.",
            "[Pipeline Audit] Inspect execution logs and the failed ingestion batch.",
            "[Validated Backfill] Reprocess the affected batch only after the source is healthy.",
        ],
        "data_mode": "demo",
    },
    {
        "case_id": "CASE-RAW_POS_TRANSACTIONS",
        "title": "Possible Currency Conversion Error in POS Sales",
        "flow_name": "Retail POS Transaction Flow",
        "root_dataset": "raw_pos_transactions",
        "severity": "HIGH",
        "status": "ACTIVE_INVESTIGATION",
        "first_observed_at": "2026-10-22T09:00:00+00:00",
        "last_observed_at": "2026-10-22T09:20:00+00:00",
        "silent_data_corruption": True,
        "affected_datasets": [
            "raw_pos_transactions",
            "stg_pos_transactions",
            "fct_daily_sales",
        ],
        "downstream_reports": ["Average Order Value Dashboard"],
        "associated_kpis": [
            {
                "kpi_name": "Average Order Value",
                "expected_value": 850,
                "actual_value": 1190,
                "deviation_percent": 40.0,
                "business_impact": "DEMO: Average order value is above baseline.",
            }
        ],
        "confirmed_evidence": [
            {
                "evidence_id": "DEMO-EV-003",
                "evidence_type": "DATA_QUALITY_ASSERTION",
                "component": "fct_daily_sales",
                "check_status": "FAILED",
                "severity": "HIGH",
                "observed_at": "2026-10-22T09:20:00+00:00",
                "details": "DEMO: A numeric distribution check exceeded its threshold.",
            }
        ],
        "inferred_hypotheses": [
            {
                "hypothesis_id": "DEMO-HYP-002",
                "candidate_root_cause": "pipe_pos_currency_conversion",
                "dataset_name": "raw_pos_transactions",
                "pipeline_name": "pipe_pos_currency_conversion",
                "confidence_score": 0.72,
                "confidence_level": "MEDIUM",
                "is_confirmed": False,
                "rank": 1,
                "reasoning": (
                    "[DEMO HYPOTHESIS] A conversion or aggregation issue "
                    "may explain the KPI deviation. Validate against source records."
                ),
                "score_breakdown": {
                    "raw_score": 76,
                    "max_raw_score": 100,
                    "confidence_score": 0.72,
                    "max_confidence_limit": 0.95,
                    "scoring_details": [
                        "DEMO: Candidate upstream dataset",
                        "DEMO: Numeric anomaly observed",
                        "DEMO: KPI deviation detected",
                    ],
                },
            }
        ],
        "top_candidate_root_cause": "pipe_pos_currency_conversion",
        "top_confidence_score": 0.72,
        "recommended_recovery_actions": [
            "[Calculation Audit] Verify currency conversion and unit multipliers.",
            "[Reconciliation] Compare a sample of source transactions with transformed values.",
            "[Controlled Reprocessing] Recompute affected aggregates after validation.",
        ],
        "data_mode": "demo",
    },
]


DEMO_INCIDENTS = [
    {
        "incident_id": "DEMO-INC-001",
        "case_id": "CASE-RAW_ECOMMERCE_ORDERS",
        "title": "E-Commerce ingestion timeout",
        "dataset_name": "raw_ecommerce_orders",
        "severity": "CRITICAL",
        "status": "OPEN",
        "error_code": "ERR_DB_CONN_TIMEOUT",
        "description": "DEMO: Simulated upstream connectivity failure.",
        "observed_at": "2026-10-22T08:10:00+00:00",
    },
    {
        "incident_id": "DEMO-INC-002",
        "case_id": "CASE-RAW_POS_TRANSACTIONS",
        "title": "POS KPI deviation",
        "dataset_name": "fct_daily_sales",
        "severity": "HIGH",
        "status": "INVESTIGATING",
        "error_code": "WARN_SCHEMA_MISMATCH",
        "description": "DEMO: Simulated data-quality anomaly.",
        "observed_at": "2026-10-22T09:20:00+00:00",
    },
]


DEMO_LINEAGE = {
    "status": "success",
    "data_mode": "demo",
    "nodes": [
        {"id": "raw_ecommerce_orders", "label": "Raw E-Commerce Orders", "type": "source"},
        {"id": "stg_ecommerce_orders", "label": "Staging Orders", "type": "transformation"},
        {"id": "fct_daily_sales", "label": "Daily Sales Fact", "type": "transformation"},
        {"id": "mart_revenue", "label": "Revenue Mart", "type": "mart"},
        {"id": "raw_pos_transactions", "label": "Raw POS Transactions", "type": "source"},
        {"id": "stg_pos_transactions", "label": "Staging POS", "type": "transformation"},
    ],
    "edges": [
        {"source": "raw_ecommerce_orders", "target": "stg_ecommerce_orders"},
        {"source": "stg_ecommerce_orders", "target": "fct_daily_sales"},
        {"source": "fct_daily_sales", "target": "mart_revenue"},
        {"source": "raw_pos_transactions", "target": "stg_pos_transactions"},
        {"source": "stg_pos_transactions", "target": "fct_daily_sales"},
    ],
}


DEMO_QUALITY_CHECKS = [
    {
        "check_id": "DEMO-QC-001",
        "dataset_name": "raw_ecommerce_orders",
        "check_type": "ROW_COUNT_THRESHOLD",
        "expected_value": 10000,
        "actual_value": 6200,
        "severity": "CRITICAL",
        "status": "FAILED",
        "check_status": "FAILED",
        "observed_at": "2026-10-22T08:15:00+00:00",
        "evidence_details": "DEMO: Row count is below the expected threshold.",
        "data_mode": "demo",
    },
    {
        "check_id": "DEMO-QC-002",
        "dataset_name": "fct_daily_sales",
        "check_type": "KPI_DEVIATION",
        "expected_value": 850,
        "actual_value": 1190,
        "severity": "HIGH",
        "status": "WARNING",
        "check_status": "WARNING",
        "observed_at": "2026-10-22T09:20:00+00:00",
        "evidence_details": "DEMO: Average order value differs from its baseline.",
        "data_mode": "demo",
    },
]


def filtered_demo_investigations(
    case_id=None, severity=None, status=None, limit=None
):
    cases = DEMO_INVESTIGATIONS[:]

    if case_id:
        cases = [c for c in cases if c["case_id"].upper() == case_id.upper()]
    if severity:
        cases = [c for c in cases if c["severity"].upper() == severity.upper()]
    if status:
        cases = [c for c in cases if c["status"].upper() == status.upper()]
    total = len(cases)

    if limit is not None and limit > 0:
        cases = cases[:limit]

    return {
        "status": "success",
        "data_mode": "demo",
        "total_investigations": len(cases),
        "investigations": cases,
        "summary": {
            "total_matching": total,
            "returned_count": len(cases),
            "critical_cases": sum(c["severity"] == "CRITICAL" for c in cases),
            "high_cases": sum(c["severity"] == "HIGH" for c in cases),
            "silent_corruption_cases": sum(
                c["silent_data_corruption"] for c in cases
            ),
            "total_hypotheses_generated": sum(
                len(c["inferred_hypotheses"]) for c in cases
            ),
            "total_confirmed_evidence_items": sum(
                len(c["confirmed_evidence"]) for c in cases
            ),
        },
        "global_summary": {
            "total_cases": len(DEMO_INVESTIGATIONS),
            "critical_cases": sum(
                c["severity"] == "CRITICAL" for c in DEMO_INVESTIGATIONS
            ),
            "high_cases": sum(
                c["severity"] == "HIGH" for c in DEMO_INVESTIGATIONS
            ),
            "silent_corruption_cases": sum(
                c["silent_data_corruption"] for c in DEMO_INVESTIGATIONS
            ),
        },
        "hypothesis_disclaimer": (
            "DEMO DATA: All records are illustrative, not live Exasol evidence. "
            "Hypotheses are unconfirmed and require operator verification."
        ),
    }


@app.get("/", tags=["General"])
def root_endpoint() -> Dict[str, Any]:
    return {
        "service": "TraceOps API",
        "description": "Evidence-First Data Incident Investigation",
        "version": "0.2.0",
        "status": "online",
        "timestamp": now_iso(),
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "api_health": "/api/health",
            "exasol_health": "/api/exasol/health",
            "incidents": "/api/incidents",
            "investigations": "/api/investigations",
            "lineage": "/api/lineage",
            "quality_checks": "/api/quality-checks",
        },
    }


@app.get("/api/health", tags=["Health"])
def api_health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "TraceOps API",
        "timestamp": now_iso(),
    }


@app.get("/api/exasol/health", tags=["Health"])
def exasol_health() -> JSONResponse:
    try:
        result = check_exasol_health()
        code = (
            http_status.HTTP_200_OK
            if result.get("status") == "healthy"
            else http_status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return JSONResponse(status_code=code, content=result)
    except Exception:
        logger.exception("Exasol health check failed")
        return JSONResponse(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "Exasol",
                "message": "Exasol is unavailable. Demo fallback is enabled for data endpoints.",
            },
        )


@app.get("/api/incidents", tags=["Incidents"])
def list_incidents(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
) -> JSONResponse:
    try:
        data = get_incident_investigations(
            severity=severity,
            status_filter=status,
            limit=limit,
        )
        return JSONResponse(status_code=200, content=data)
    except Exception:
        logger.exception("Using demo incident records because Exasol retrieval failed")
        items = DEMO_INCIDENTS[:]
        if severity:
            items = [x for x in items if x["severity"].upper() == severity.upper()]
        if status:
            items = [x for x in items if x["status"].upper() == status.upper()]
        if limit is not None and limit > 0:
            items = items[:limit]
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "data_mode": "demo",
                "total": len(items),
                "incidents": items,
                "message": "DEMO DATA: These incidents are illustrative, not live database records.",
            },
        )


@app.get("/api/investigations", tags=["Investigations"])
def list_investigations(
    case_id: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
) -> JSONResponse:
    try:
        data = get_investigation_cases(
            case_id=case_id,
            severity=severity,
            status=status,
            limit=limit,
        )
        return JSONResponse(status_code=200, content=data)
    except Exception:
        logger.exception("Using demo investigation cases because Exasol retrieval failed")
        return JSONResponse(
            status_code=200,
            content=filtered_demo_investigations(
                case_id=case_id,
                severity=severity,
                status=status,
                limit=limit,
            ),
        )


@app.get("/api/lineage", tags=["Lineage"])
def get_lineage() -> JSONResponse:
    try:
        data = get_lineage_data()
        return JSONResponse(status_code=200, content=data)
    except Exception:
        logger.exception("Using demo lineage because Exasol retrieval failed")
        return JSONResponse(status_code=200, content=DEMO_LINEAGE)


@app.get("/api/quality-checks", tags=["Quality Checks"])
def list_quality_checks(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    dataset: Optional[str] = None,
    search: Optional[str] = None,
    limit: Optional[int] = None,
) -> JSONResponse:
    try:
        data = get_quality_checks(
            status=status,
            severity=severity,
            dataset=dataset,
            search=search,
            limit=limit,
        )
        return JSONResponse(status_code=200, content=data)
    except Exception:
        logger.exception("Using demo quality checks because Exasol retrieval failed")
        items = DEMO_QUALITY_CHECKS[:]

        if status:
            items = [
                x for x in items
                if status.upper() in (
                    x["status"].upper(), x["check_status"].upper()
                )
            ]
        if severity:
            items = [x for x in items if x["severity"].upper() == severity.upper()]
        if dataset:
            items = [
                x for x in items
                if dataset.lower() in x["dataset_name"].lower()
            ]
        if search:
            items = [
                x for x in items
                if search.lower() in str(x).lower()
            ]
        if limit is not None and limit > 0:
            items = items[:limit]

        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "data_mode": "demo",
                "total": len(items),
                "quality_checks": items,
                "message": "DEMO DATA: These checks are illustrative, not live database results.",
            },
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
