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

from database import check_exasol_health, get_incident_investigations, get_quality_checks
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

# Configure CORS for Vite frontend and development clients
default_origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
]
raw_origins = os.environ.get("ALLOWED_ORIGINS", ",".join(default_origins))
origins = list(dict.fromkeys([origin.strip() for origin in raw_origins.split(",") if origin.strip()] + default_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["General"])
def root_endpoint() -> Dict[str, Any]:
    """
    Root endpoint providing service information and API navigation links.
    """
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
    """
    General API health check endpoint.
    Verifies that the FastAPI application is running and responsive.
    """
    return {
        "status": "ok",
        "service": "TraceOps API",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/exasol/health", tags=["Health"])
def exasol_health() -> JSONResponse:
    """
    Exasol database connectivity health check.
    Executes 'SELECT 1 AS test_value' and returns connection status.
    Does not expose sensitive credentials or tokens.
    """
    result = check_exasol_health()
    
    if result.get("status") == "healthy":
        return JSONResponse(
            status_code=http_status.HTTP_200_OK,
            content=result,
        )
    else:
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
    Retrieve evidence-first data incident investigations from Exasol.
    Combines failed or warning quality check anomalies, pipeline run issues,
    lineage dependencies, and business KPI deviations.
    """
    try:
        data = get_incident_investigations(
            severity=severity,
            status_filter=status,
            limit=limit,
        )
        return JSONResponse(
            status_code=http_status.HTTP_200_OK,
            content=data,
        )
    except Exception as exc:
        clean_error = str(exc)
        if "password" in clean_error.lower():
            clean_error = "Authentication failed"
        logger.error("Incident retrieval failed: %s", clean_error)
        return JSONResponse(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "message": "Failed to retrieve incident investigation data from Exasol database.",
                "detail": clean_error,
            },
        )


@app.get("/api/investigations", tags=["Investigations"])
def list_investigations(
    case_id: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
) -> JSONResponse:
    """
    Evidence-based root-cause ranking engine endpoint.
    Groups raw incidents into correlated investigation cases, ranks candidate root causes
    with explainable confidence scores, isolates confirmed evidence from inferred hypotheses,
    and returns blast radius and recovery actions.
    """
    try:
        data = get_investigation_cases(
            case_id=case_id,
            severity=severity,
            status=status,
            limit=limit,
        )
        return JSONResponse(
            status_code=http_status.HTTP_200_OK,
            content=data,
        )
    except Exception as exc:
        clean_error = str(exc)
        if "password" in clean_error.lower():
            clean_error = "Authentication failed"
        logger.error("Investigation cases retrieval failed: %s", clean_error)
        return JSONResponse(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "message": "Failed to retrieve investigation cases from Exasol database.",
                "detail": clean_error,
            },
        )


@app.get("/api/lineage", tags=["Lineage"])
def get_lineage() -> JSONResponse:
    """
    Retrieve interactive data lineage DAG directly from Exasol TRACEOPS.DATASET_DEPENDENCIES.
    Provides nodes (sources, transformations, downstream marts/reports), dependency edges,
    and investigation scenario mapping.
    """
    try:
        data = get_lineage_data()
        return JSONResponse(
            status_code=http_status.HTTP_200_OK,
            content=data,
        )
    except Exception as exc:
        clean_error = str(exc)
        if "password" in clean_error.lower():
            clean_error = "Authentication failed"
        logger.error("Lineage graph retrieval failed: %s", clean_error)
        return JSONResponse(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "message": "Failed to retrieve lineage DAG from Exasol database.",
                "detail": clean_error,
            },
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
    Retrieve empirical data quality checks and test assertions from Exasol.
    Correlates observations with the lineage DAG and active incident investigations.
    Supports parameter-safe filtering by status, severity, dataset, search text, and limit.
    """
    try:
        data = get_quality_checks(
            status=status,
            severity=severity,
            dataset=dataset,
            search=search,
            limit=limit,
        )
        return JSONResponse(
            status_code=http_status.HTTP_200_OK,
            content=data,
        )
    except Exception as exc:
        clean_error = str(exc)
        if "password" in clean_error.lower():
            clean_error = "Authentication failed"
        logger.error("Quality checks retrieval failed: %s", clean_error)
        return JSONResponse(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "message": "Failed to retrieve quality checks from Exasol database.",
                "detail": clean_error,
            },
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
