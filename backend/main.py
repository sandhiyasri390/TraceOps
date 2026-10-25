
"""
TraceOps API: Evidence-First Data Incident Investigation
ExaThon India 2026 ΓÇö Track 04
Demo fallback enabled when Exasol is unavailable.
"""

from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import sys
from typing import Any, Dict, Optional

# Prioritize backend directory in sys.path to prevent module collisions
# with the top-level 'database' schema directory when run from project root.
_backend_dir = str(Path(__file__).resolve().parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
elif sys.path[0] != _backend_dir:
    sys.path.remove(_backend_dir)
    sys.path.insert(0, _backend_dir)

from fastapi import FastAPI, status as http_status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

try:
    from database import (
        check_exasol_health,
        get_incident_investigations,
        get_quality_checks,
    )
    from ranking import get_investigation_cases
    from lineage import get_lineage_data
except (ImportError, ModuleNotFoundError):
    from backend.database import (
        check_exasol_health,
        get_incident_investigations,
        get_quality_checks,
    )
    from backend.ranking import get_investigation_cases
    from backend.lineage import get_lineage_data

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

DEMO_INVESTIGATIONS = [{'case_id': 'CASE-RAW_ECOMMERCE_ORDERS',
  'title': 'Upstream E-Commerce Timeout Causing GMV Shortfall',
  'flow_name': 'E-Commerce Order Processing Flow',
  'root_dataset': 'raw_ecommerce_orders',
  'severity': 'CRITICAL',
  'status': 'ACTIVE_INVESTIGATION',
  'first_observed_at': '2026-10-22T08:10:00+00:00',
  'last_observed_at': '2026-10-22T08:15:00+00:00',
  'silent_data_corruption': False,
  'affected_datasets': ['raw_ecommerce_orders',
                        'stg_ecommerce_orders',
                        'fct_daily_sales',
                        'mart_revenue'],
  'downstream_reports': ['Executive Revenue Dashboard', 'Daily GMV Report'],
  'associated_kpis': [{'kpi_name': 'Gross Merchandise Value',
                       'expected_value': 1250000,
                       'actual_value': 790000,
                       'deviation_percent': -36.8,
                       'business_impact': 'Revenue reporting may be incomplete.'}],
  'confirmed_evidence': [{'evidence_id': 'DEMO-EV-001',
                          'evidence_type': 'PIPELINE_EXECUTION',
                          'component': 'pipe_raw_ecommerce_orders',
                          'status': 'FAILED',
                          'severity': 'CRITICAL',
                          'observed_at': '2026-10-22T08:10:00+00:00',
                          'error_code': 'ERR_DB_CONN_TIMEOUT',
                          'details': 'DEMO: Simulated upstream database timeout.'},
                         {'evidence_id': 'DEMO-EV-002',
                          'evidence_type': 'DATA_QUALITY_ASSERTION',
                          'component': 'stg_ecommerce_orders',
                          'check_status': 'FAILED',
                          'severity': 'CRITICAL',
                          'observed_at': '2026-10-22T08:15:00+00:00',
                          'details': 'DEMO: Row count fell below the expected threshold.'}],
  'inferred_hypotheses': [{'hypothesis_id': 'DEMO-HYP-001',
                           'candidate_root_cause': 'pipe_raw_ecommerce_orders',
                           'dataset_name': 'raw_ecommerce_orders',
                           'pipeline_name': 'pipe_raw_ecommerce_orders',
                           'confidence_score': 0.88,
                           'confidence_level': 'HIGH',
                           'is_confirmed': False,
                           'rank': 1,
                           'reasoning': '[Inferred Hypothesis] The upstream timeout may explain the '
                                        'downstream row-count and revenue anomalies. Operator '
                                        'verification is required.',
                           'score_breakdown': {'raw_score': 92,
                                               'max_raw_score': 100,
                                               'confidence_score': 0.88,
                                               'max_confidence_limit': 0.95,
                                               'scoring_details': ['DEMO: Upstream source '
                                                                   'candidate',
                                                                   'DEMO: Earliest observed event',
                                                                   'DEMO: Simulated failure '
                                                                   'evidence',
                                                                   'DEMO: Downstream KPI '
                                                                   'impact']}},
                          {'hypothesis_id': 'DEMO-HYP-001b',
                           'candidate_root_cause': 'pipe_stg_online_orders',
                           'dataset_name': 'stg_ecommerce_orders',
                           'pipeline_name': 'pipe_stg_online_orders',
                           'confidence_score': 0.61,
                           'confidence_level': 'MEDIUM',
                           'is_confirmed': False,
                           'rank': 2,
                           'reasoning': '[Inferred Hypothesis] Downstream staging failure may be a secondary effect.',
                           'score_breakdown': {'raw_score': 64,
                                               'max_raw_score': 100,
                                               'confidence_score': 0.61,
                                               'max_confidence_limit': 0.95,
                                               'scoring_details': ['DEMO: Downstream pipeline']}},
                          {'hypothesis_id': 'DEMO-HYP-001c',
                           'candidate_root_cause': 'pipe_fct_orders',
                           'dataset_name': 'fct_daily_sales',
                           'pipeline_name': 'pipe_fct_orders',
                           'confidence_score': 0.45,
                           'confidence_level': 'LOW',
                           'is_confirmed': False,
                           'rank': 3,
                           'reasoning': '[Inferred Hypothesis] Fact table shows cascaded impact from upstream failures.',
                           'score_breakdown': {'raw_score': 47,
                                               'max_raw_score': 100,
                                               'confidence_score': 0.45,
                                               'max_confidence_limit': 0.95,
                                               'scoring_details': ['DEMO: Fact table downstream']}}],
  'top_candidate_root_cause': 'pipe_raw_ecommerce_orders',
  'top_confidence_score': 0.88,
  'recommended_recovery_actions': ['[Read-Only Verification] Check upstream database availability '
                                   'and connectivity.',
                                   '[Pipeline Audit] Inspect execution logs and the failed '
                                   'ingestion batch.',
                                   '[Validated Backfill] Reprocess the affected batch only after '
                                   'the source is healthy.'],
  'data_mode': 'demo'},
 {'case_id': 'CASE-RAW_POS_TRANSACTIONS',
  'title': 'Possible Currency Conversion Error in POS Sales',
  'flow_name': 'Retail POS Transaction Flow',
  'root_dataset': 'raw_pos_transactions',
  'severity': 'HIGH',
  'status': 'ACTIVE_INVESTIGATION',
  'first_observed_at': '2026-10-22T09:00:00+00:00',
  'last_observed_at': '2026-10-22T09:20:00+00:00',
  'silent_data_corruption': True,
  'affected_datasets': ['raw_pos_transactions', 'stg_pos_transactions', 'fct_daily_sales'],
  'downstream_reports': ['Average Order Value Dashboard'],
  'associated_kpis': [{'kpi_name': 'Average Order Value',
                       'expected_value': 850,
                       'actual_value': 1190,
                       'deviation_percent': 40.0,
                       'business_impact': 'DEMO: Average order value is above baseline.'}],
  'confirmed_evidence': [{'evidence_id': 'DEMO-EV-003',
                          'evidence_type': 'DATA_QUALITY_ASSERTION',
                          'component': 'fct_daily_sales',
                          'check_status': 'FAILED',
                          'severity': 'HIGH',
                          'observed_at': '2026-10-22T09:20:00+00:00',
                          'details': 'DEMO: A numeric distribution check exceeded its threshold.'}],
  'inferred_hypotheses': [{'hypothesis_id': 'DEMO-HYP-002',
                           'candidate_root_cause': 'pipe_pos_transactions_etl',
                           'dataset_name': 'raw_pos_transactions',
                           'pipeline_name': 'pipe_pos_transactions_etl',
                           'confidence_score': 0.72,
                           'confidence_level': 'MEDIUM',
                           'is_confirmed': False,
                           'rank': 1,
                           'reasoning': '[Inferred Hypothesis] EUR/GBP currency multiplier bug in '
                                        'POS ETL may explain the average order value inflation. '
                                        'Operator verification required.',
                           'score_breakdown': {'raw_score': 76,
                                               'max_raw_score': 100,
                                               'confidence_score': 0.72,
                                               'max_confidence_limit': 0.95,
                                               'scoring_details': ['DEMO: Candidate upstream '
                                                                   'dataset',
                                                                   'DEMO: Numeric anomaly observed',
                                                                   'DEMO: KPI deviation '
                                                                   'detected']}}],
  'top_candidate_root_cause': 'pipe_pos_transactions_etl',
  'top_confidence_score': 0.72,
  'recommended_recovery_actions': ['[Calculation Audit] Verify currency conversion and unit '
                                   'multipliers (EUR/GBP multiplier suspected).',
                                   '[Reconciliation] Compare a sample of source transactions with '
                                   'transformed values.',
                                   '[Controlled Reprocessing] Recompute affected aggregates after '
                                   'validation.'],
  'data_mode': 'demo'},
 {'case_id': 'CASE-RAW_CRM_EXPORT',
  'title': 'Unannounced Schema Drift in CRM Feed Causing Postal Code Null Spike',
  'flow_name': 'CRM Customer Profile Enrichment Flow',
  'root_dataset': 'raw_crm_export',
  'severity': 'CRITICAL',
  'status': 'ACTIVE_INVESTIGATION',
  'first_observed_at': '2026-10-17T02:10:00+00:00',
  'last_observed_at': '2026-10-17T02:25:00+00:00',
  'silent_data_corruption': False,
  'affected_datasets': ['raw_crm_export', 'stg_crm_customers', 'dim_customers'],
  'downstream_reports': ['Customer Segmentation Report', 'Regional Revenue Dashboard'],
  'associated_kpis': [{'kpi_name': 'Postal Code Fill Rate',
                       'expected_value': 99.5,
                       'actual_value': 71.2,
                       'deviation_percent': -28.4,
                       'business_impact': 'Regional revenue attribution may be incorrect.'}],
  'confirmed_evidence': [{'evidence_id': 'DEMO-EV-004',
                          'evidence_type': 'DATA_QUALITY_ASSERTION',
                          'component': 'stg_crm_customers',
                          'check_status': 'FAILED',
                          'severity': 'CRITICAL',
                          'observed_at': '2026-10-17T02:10:00+00:00',
                          'details': 'DEMO: Postal code null rate spiked to 28.8% after CRM schema drift.'}],
  'inferred_hypotheses': [{'hypothesis_id': 'DEMO-HYP-003',
                           'candidate_root_cause': 'pipe_raw_crm_export',
                           'dataset_name': 'raw_crm_export',
                           'pipeline_name': 'pipe_raw_crm_export',
                           'confidence_score': 0.81,
                           'confidence_level': 'HIGH',
                           'is_confirmed': False,
                           'rank': 1,
                           'reasoning': '[Inferred Hypothesis] Unannounced CRM schema change '
                                        'dropped the postal_code column, causing null spike. '
                                        'Operator verification required.',
                           'score_breakdown': {'raw_score': 84,
                                               'max_raw_score': 100,
                                               'confidence_score': 0.81,
                                               'max_confidence_limit': 0.95,
                                               'scoring_details': ['DEMO: Schema drift detected',
                                                                   'DEMO: Null spike observed']}}],
  'top_candidate_root_cause': 'pipe_raw_crm_export',
  'top_confidence_score': 0.81,
  'recommended_recovery_actions': ['[Schema Audit] Compare current CRM feed schema with the '
                                   'registered DDL in the data catalog.',
                                   '[Null Analysis] Identify which records are missing postal_code '
                                   'and trace to source extraction batch.',
                                   '[Controlled Reprocessing] Re-ingest after schema contract is '
                                   'restored with the CRM provider.'],
  'data_mode': 'demo'},
 {'case_id': 'CASE-RAW_WEB_CLICKSTREAM',
  'title': 'Mobile Session Drop in Web Clickstream Cratered Conversion Funnel',
  'flow_name': 'Web Clickstream & Session Conversion Funnel',
  'root_dataset': 'raw_web_clickstream',
  'severity': 'CRITICAL',
  'status': 'ACTIVE_INVESTIGATION',
  'first_observed_at': '2026-10-17T03:50:00+00:00',
  'last_observed_at': '2026-10-17T04:10:00+00:00',
  'silent_data_corruption': False,
  'affected_datasets': ['raw_web_clickstream', 'stg_session_events', 'fct_conversion_funnel'],
  'downstream_reports': ['Conversion Funnel Dashboard', 'Mobile UX Report'],
  'associated_kpis': [{'kpi_name': 'Mobile Conversion Rate',
                       'expected_value': 4.2,
                       'actual_value': 1.9,
                       'deviation_percent': -54.8,
                       'business_impact': 'Marketing spend ROI may be significantly understated.'}],
  'confirmed_evidence': [{'evidence_id': 'DEMO-EV-005',
                          'evidence_type': 'DATA_QUALITY_ASSERTION',
                          'component': 'stg_session_events',
                          'check_status': 'FAILED',
                          'severity': 'CRITICAL',
                          'observed_at': '2026-10-17T04:05:00+00:00',
                          'details': 'DEMO: Mobile session record count dropped 64% vs 7-day avg.'}],
  'inferred_hypotheses': [{'hypothesis_id': 'DEMO-HYP-004',
                           'candidate_root_cause': 'pipe_raw_web_clickstream',
                           'dataset_name': 'raw_web_clickstream',
                           'pipeline_name': 'pipe_raw_web_clickstream',
                           'confidence_score': 0.85,
                           'confidence_level': 'HIGH',
                           'is_confirmed': False,
                           'rank': 1,
                           'reasoning': '[Inferred Hypothesis] Mobile tracker instrumentation '
                                        'failure caused session drop. Operator verification required.',
                           'score_breakdown': {'raw_score': 89,
                                               'max_raw_score': 100,
                                               'confidence_score': 0.85,
                                               'max_confidence_limit': 0.95,
                                               'scoring_details': ['DEMO: Session count anomaly',
                                                                   'DEMO: Mobile-only drop pattern']}}],
  'top_candidate_root_cause': 'pipe_raw_web_clickstream',
  'top_confidence_score': 0.85,
  'recommended_recovery_actions': ['[Tracker Audit] Check mobile event tracker SDK version and '
                                   'deployment state across app versions.',
                                   '[Session Reconciliation] Compare raw event counts from tracker '
                                   'logs vs ingested records.',
                                   '[Controlled Replay] Re-ingest missed mobile sessions from '
                                   'tracker buffer after source is validated.'],
  'data_mode': 'demo'},
 {'case_id': 'CASE-RAW_WMS_BALANCES',
  'title': 'Warehouse Lock Contention Inducing Supply Chain Stockout False Alarm',
  'flow_name': 'Inventory & WMS Balance Snapshot Flow',
  'root_dataset': 'raw_wms_balances',
  'severity': 'HIGH',
  'status': 'ACTIVE_INVESTIGATION',
  'first_observed_at': '2026-10-17T06:35:00+00:00',
  'last_observed_at': '2026-10-17T06:50:00+00:00',
  'silent_data_corruption': False,
  'affected_datasets': ['raw_wms_balances', 'stg_inventory_snapshots', 'dim_inventory_availability'],
  'downstream_reports': ['Inventory Availability Dashboard', 'Supply Chain Ops Report'],
  'associated_kpis': [{'kpi_name': 'In-Stock Availability Rate',
                       'expected_value': 97.8,
                       'actual_value': 84.1,
                       'deviation_percent': -14.0,
                       'business_impact': 'Supply chain may falsely trigger emergency restocking orders.'}],
  'confirmed_evidence': [{'evidence_id': 'DEMO-EV-006',
                          'evidence_type': 'PIPELINE_EXECUTION',
                          'component': 'pipe_raw_wms_balances',
                          'status': 'FAILED',
                          'severity': 'HIGH',
                          'observed_at': '2026-10-17T06:50:00+00:00',
                          'details': 'DEMO: WMS snapshot pipeline timed out due to lock contention.'}],
  'inferred_hypotheses': [{'hypothesis_id': 'DEMO-HYP-005',
                           'candidate_root_cause': 'pipe_raw_wms_balances',
                           'dataset_name': 'raw_wms_balances',
                           'pipeline_name': 'pipe_raw_wms_balances',
                           'confidence_score': 0.78,
                           'confidence_level': 'HIGH',
                           'is_confirmed': False,
                           'rank': 1,
                           'reasoning': '[Inferred Hypothesis] WMS lock contention caused stale '
                                        'balance snapshot, triggering false stockout. Operator '
                                        'verification required.',
                           'score_breakdown': {'raw_score': 81,
                                               'max_raw_score': 100,
                                               'confidence_score': 0.78,
                                               'max_confidence_limit': 0.95,
                                               'scoring_details': ['DEMO: Pipeline timeout detected',
                                                                   'DEMO: Stale snapshot inferred']}}],
  'top_candidate_root_cause': 'pipe_raw_wms_balances',
  'top_confidence_score': 0.78,
  'recommended_recovery_actions': ['[Lock Analysis] Inspect WMS database lock contention logs '
                                   'during the snapshot window.',
                                   '[Snapshot Validation] Compare WMS balance snapshot with '
                                   'physical inventory scan records.',
                                   '[Controlled Re-snapshot] Re-run WMS balance extraction after '
                                   'confirming lock contention is resolved.'],
  'data_mode': 'demo'}]


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
    "status": "ok",
    "data_mode": "demo",
    "summary": {
        "total_nodes": 6,
        "total_dependencies": 5,
        "is_acyclic": True,
        "source_datasets": 2,
        "transformations": 3,
        "downstream_datasets": 1,
        "critical_dependencies": 0,
        "direct_critical_count": 0,
        "silent_corruption_count": 0,
    },
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
    "scenarios": [],
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
                "host": "127.0.0.1:8563",
                "latency_ms": None,
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

        # Helper: treat None, blank, and "ALL" (any case) as "no filter"
        def _active(val: Optional[str]) -> bool:
            return bool(val and val.strip() and val.strip().upper() != "ALL")

        if _active(status):
            target_status = status.strip().upper()
            items = [
                x for x in items
                if x.get("check_status", x.get("status", "")).upper() == target_status
            ]
        if _active(severity):
            target_sev = severity.strip().upper()
            items = [x for x in items if x.get("severity", "").upper() == target_sev]
        if _active(dataset):
            target_ds = dataset.strip().lower()
            items = [x for x in items if target_ds in x.get("dataset_name", "").lower()]
        if search and search.strip():
            q = search.strip().lower()
            items = [x for x in items if q in str(x).lower()]
        if limit is not None and limit > 0:
            items = items[:limit]


        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "data_mode": "demo",
                "total": len(items),
                "total_matching": len(items),
                "checks": [
                    {
                        **item,
                        "check_status": item.get("check_status", item.get("status", "UNKNOWN")),
                        "check_type": item.get("check_type", "GENERAL"),
                    }
                    for item in items
                ],
                "summary": {
                    "total_matching": len(items),
                    "passed_count": sum(1 for x in items if x.get("check_status", x.get("status", "")) == "PASSED"),
                    "failed_count": sum(1 for x in items if x.get("check_status", x.get("status", "")) == "FAILED"),
                    "warning_count": sum(1 for x in items if x.get("check_status", x.get("status", "")) == "WARNING"),
                    "critical_count": sum(1 for x in items if x.get("severity", "") == "CRITICAL"),
                    "high_count": sum(1 for x in items if x.get("severity", "") == "HIGH"),
                },
                "global_summary": {
                    "total_checks": len(DEMO_QUALITY_CHECKS),
                    "passed_checks": sum(1 for x in DEMO_QUALITY_CHECKS if x.get("check_status", x.get("status", "")) == "PASSED"),
                    "failed_checks": sum(1 for x in DEMO_QUALITY_CHECKS if x.get("check_status", x.get("status", "")) == "FAILED"),
                    "warning_checks": sum(1 for x in DEMO_QUALITY_CHECKS if x.get("check_status", x.get("status", "")) == "WARNING"),
                    "critical_checks": sum(1 for x in DEMO_QUALITY_CHECKS if x.get("severity", "") == "CRITICAL"),
                    "high_checks": sum(1 for x in DEMO_QUALITY_CHECKS if x.get("severity", "") == "HIGH"),
                    "medium_checks": sum(1 for x in DEMO_QUALITY_CHECKS if x.get("severity", "") == "MEDIUM"),
                    "low_checks": sum(1 for x in DEMO_QUALITY_CHECKS if x.get("severity", "") == "LOW"),
                },
                "message": "DEMO DATA: These checks are illustrative, not live database results.",
            },
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
