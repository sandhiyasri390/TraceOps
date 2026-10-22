<<<<<<< HEAD

"""
TraceOps API: Evidence-First Data Incident Investigation
FastAPI backend service for ExaThon India 2026 Exasol Open Build Challenge (Track 04).
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
    description="Evidence-First Data Incident Investigation backend service powered by Exasol",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for Vite frontend and deployed frontend
default_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
]

raw_origins = os.environ.get(
    "ALLOWED_ORIGINS",
    ",".join(default_origins),
)

origins = list(
    dict.fromkeys(
        [
            origin.strip()
            for origin in raw_origins.split(",")
            if origin.strip()
        ]
        + default_origins
    )
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["General"])
def root_endpoint() -> Dict[str, Any]:
    """Provide service information and API navigation links."""
    return {
        "service": "TraceOps API",
        "description": "Evidence-First Data Incident Investigation",
        "version": "0.1.0",
        "status": "online",
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
    """Check that the FastAPI application is running."""
    return {
        "status": "ok",
        "service": "TraceOps API",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/exasol/health", tags=["Health"])
def exasol_health() -> JSONResponse:
    """
    Check Exasol database connectivity.
    Does not expose sensitive credentials or tokens.
    """
    result = check_exasol_health()

    if result.get("status") == "healthy":
        return JSONResponse(
            status_code=http_status.HTTP_200_OK,
            content=result,
        )

    return JSONResponse(
        status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
        content=result,
    )


@app.get("/api/incidents", tags=["Incidents"])
def list_incidents(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
) -> JSONResponse:
    """
    Retrieve data incident investigations.
    Uses sample data if Exasol retrieval fails.
    """
    try:
        data = get_incident_investigations(
            severity=severity,
            status_filter=status,
            limit=limit,
        )
        data["data_source"] = "live"

    except Exception:
        logger.exception(
            "Failed to retrieve incidents from Exasol; using sample data."
        )
        from sample_data import get_sample_incidents

        data = get_sample_incidents(
            severity=severity,
            status=status,
            limit=limit,
        )
        data["data_source"] = "sample"

    return JSONResponse(
        status_code=http_status.HTTP_200_OK,
        content=data,
    )


@app.get("/api/investigations", tags=["Investigations"])
def list_investigations(
    case_id: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
) -> JSONResponse:
    """
    Rank candidate root causes and return investigation evidence,
    hypotheses, blast radius, and recovery actions.
    Uses sample data if live retrieval fails.
    """
    try:
        data = get_investigation_cases(
            case_id=case_id,
            severity=severity,
            status=status,
            limit=limit,
        )
        data["data_source"] = "live"

    except Exception:
        logger.exception(
            "Failed to retrieve investigations; using sample data."
        )
        from sample_data import get_sample_investigations

        data = get_sample_investigations(
            case_id=case_id,
            severity=severity,
            status=status,
            limit=limit,
        )
        data["data_source"] = "sample"

    return JSONResponse(
        status_code=http_status.HTTP_200_OK,
        content=data,
    )


@app.get("/api/lineage", tags=["Lineage"])
def get_lineage() -> JSONResponse:
    """
    Retrieve the data lineage graph and investigation scenarios.
    Uses sample data if live retrieval fails.
    """
    try:
        data = get_lineage_data()
        data["data_source"] = "live"

    except Exception:
        logger.exception(
            "Failed to retrieve lineage from Exasol; using sample data."
        )
        from sample_data import get_sample_lineage

        data = get_sample_lineage()
        data["data_source"] = "sample"

    return JSONResponse(
        status_code=http_status.HTTP_200_OK,
        content=data,
    )


@app.get("/api/quality-checks", tags=["Quality Checks"])
def list_quality_checks(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    dataset: Optional[str] = None,
    search: Optional[str] = None,
    limit: Optional[int] = None,
) -> JSONResponse:
    """
    Retrieve data quality checks and assertions.
    Uses sample data if live retrieval fails.
    """
    try:
        data = get_quality_checks(
            status=status,
            severity=severity,
            dataset=dataset,
            search=search,
            limit=limit,
        )
        data["data_source"] = "live"

    except Exception:
        logger.exception(
            "Failed to retrieve quality checks; using sample data."
        )
        from sample_data import get_sample_quality_checks

        data = get_sample_quality_checks(
            status=status,
            severity=severity,
            dataset=dataset,
            search=search,
            limit=limit,
        )
        data["data_source"] = "sample"

    return JSONResponse(
        status_code=http_status.HTTP_200_OK,
        content=data,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
=======
    {
        "case_id": "CASE-RAW_CUSTOMER_PROFILES",
        "title": "Customer Profile Data Freshness Breach",
        "flow_name": "Customer Profile Processing Flow",
        "root_dataset": "raw_customer_profiles",
        "severity": "HIGH",
        "status": "ACTIVE_INVESTIGATION",
        "first_observed_at": "2026-10-22T10:00:00+00:00",
        "last_observed_at": "2026-10-22T10:15:00+00:00",
        "silent_data_corruption": False,
        "affected_datasets": [
            "raw_customer_profiles",
            "stg_customer_profiles",
            "mart_customer_360"
        ],
        "downstream_reports": ["Customer 360 Dashboard"],
        "associated_kpis": [{
            "kpi_name": "Profile Data Freshness",
            "expected_value": 100,
            "actual_value": 68,
            "deviation_percent": -32,
            "business_impact": "Customer profiles may be outdated."
        }],
        "confirmed_evidence": [{
            "evidence_id": "DEMO-EV-004",
            "evidence_type": "DATA_QUALITY_ASSERTION",
            "component": "raw_customer_profiles",
            "check_status": "FAILED",
            "severity": "HIGH",
            "observed_at": "2026-10-22T10:15:00+00:00",
            "details": "DEMO: Customer profile freshness threshold was missed."
        }],
        "inferred_hypotheses": [{
            "hypothesis_id": "DEMO-HYP-003",
            "candidate_root_cause": "pipe_customer_profiles",
            "dataset_name": "raw_customer_profiles",
            "pipeline_name": "pipe_customer_profiles",
            "confidence_score": 0.79,
            "confidence_level": "MEDIUM",
            "is_confirmed": False,
            "rank": 1,
            "reasoning": "[DEMO HYPOTHESIS] A delayed upstream ingestion may explain stale profiles.",
            "score_breakdown": {
                "raw_score": 80,
                "max_raw_score": 100,
                "confidence_score": 0.79,
                "max_confidence_limit": 0.95,
                "scoring_details": ["DEMO: Freshness threshold missed"]
            }
        }],
        "top_candidate_root_cause": "pipe_customer_profiles",
        "top_confidence_score": 0.79,
        "recommended_recovery_actions": [
            "[Pipeline Audit] Check customer profile ingestion logs.",
            "[Validation] Compare source and target update timestamps."
        ],
        "data_mode": "demo"
    },
    {
        "case_id": "CASE-RAW_PAYMENT_EVENTS",
        "title": "Payment Event Ingestion Failure",
        "flow_name": "Payment Event Processing Flow",
        "root_dataset": "raw_payment_events",
        "severity": "CRITICAL",
        "status": "ACTIVE_INVESTIGATION",
        "first_observed_at": "2026-10-22T10:30:00+00:00",
        "last_observed_at": "2026-10-22T10:40:00+00:00",
        "silent_data_corruption": False,
        "affected_datasets": [
            "raw_payment_events",
            "stg_payment_events",
            "fct_payments"
        ],
        "downstream_reports": ["Payment Operations Dashboard"],
        "associated_kpis": [{
            "kpi_name": "Payment Event Volume",
            "expected_value": 10000,
            "actual_value": 6100,
            "deviation_percent": -39,
            "business_impact": "Payment reporting may be incomplete."
        }],
        "confirmed_evidence": [{
            "evidence_id": "DEMO-EV-005",
            "evidence_type": "PIPELINE_EXECUTION",
            "component": "pipe_raw_payment_events",
            "status": "FAILED",
            "severity": "CRITICAL",
            "observed_at": "2026-10-22T10:40:00+00:00",
            "details": "DEMO: Simulated payment event ingestion failure."
        }],
        "inferred_hypotheses": [{
            "hypothesis_id": "DEMO-HYP-004",
            "candidate_root_cause": "pipe_raw_payment_events",
            "dataset_name": "raw_payment_events",
            "pipeline_name": "pipe_raw_payment_events",
            "confidence_score": 0.86,
            "confidence_level": "HIGH",
            "is_confirmed": False,
            "rank": 1,
            "reasoning": "[DEMO HYPOTHESIS] An ingestion failure may explain the reduced payment event volume.",
            "score_breakdown": {
                "raw_score": 88,
                "max_raw_score": 100,
                "confidence_score": 0.86,
                "max_confidence_limit": 0.95,
                "scoring_details": ["DEMO: Simulated pipeline failure"]
            }
        }],
        "top_candidate_root_cause": "pipe_raw_payment_events",
        "top_confidence_score": 0.86,
        "recommended_recovery_actions": [
            "[Pipeline Audit] Inspect payment ingestion execution logs.",
            "[Reconciliation] Compare source event counts with target records."
        ],
        "data_mode": "demo"
    },
    {
        "case_id": "CASE-RAW_MARKETING_EVENTS",
        "title": "Duplicate Marketing Events Detected",
        "flow_name": "Marketing Event Processing Flow",
        "root_dataset": "raw_marketing_events",
        "severity": "MEDIUM",
        "status": "ACTIVE_INVESTIGATION",
        "first_observed_at": "2026-10-22T11:00:00+00:00",
        "last_observed_at": "2026-10-22T11:20:00+00:00",
        "silent_data_corruption": True,
        "affected_datasets": [
            "raw_marketing_events",
            "stg_marketing_events",
            "mart_campaign_performance"
        ],
        "downstream_reports": ["Campaign Performance Dashboard"],
        "associated_kpis": [{
            "kpi_name": "Unique Marketing Events",
            "expected_value": 50000,
            "actual_value": 63500,
            "deviation_percent": 27,
            "business_impact": "Campaign engagement metrics may be overstated."
        }],
        "confirmed_evidence": [{
            "evidence_id": "DEMO-EV-006",
            "evidence_type": "DATA_QUALITY_ASSERTION",
            "component": "stg_marketing_events",
            "check_status": "FAILED",
            "severity": "MEDIUM",
            "observed_at": "2026-10-22T11:20:00+00:00",
            "details": "DEMO: Duplicate event count exceeded the configured threshold."
        }],
        "inferred_hypotheses": [{
            "hypothesis_id": "DEMO-HYP-005",
            "candidate_root_cause": "pipe_marketing_events",
            "dataset_name": "raw_marketing_events",
            "pipeline_name": "pipe_marketing_events",
            "confidence_score": 0.74,
            "confidence_level": "MEDIUM",
            "is_confirmed": False,
            "rank": 1,
            "reasoning": "[DEMO HYPOTHESIS] Duplicate ingestion may explain inflated campaign metrics.",
            "score_breakdown": {
                "raw_score": 75,
                "max_raw_score": 100,
                "confidence_score": 0.74,
                "max_confidence_limit": 0.95,
                "scoring_details": ["DEMO: Duplicate event threshold exceeded"]
            }
        }],
        "top_candidate_root_cause": "pipe_marketing_events",
        "top_confidence_score": 0.74,
        "recommended_recovery_actions": [
            "[Deduplication Audit] Inspect event identifiers and ingestion retries.",
            "[Validation] Compare unique source events with transformed records."
        ],
        "data_mode": "demo"
    },
>>>>>>> origin/main
