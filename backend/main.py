
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
