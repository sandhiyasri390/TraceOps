# Sample data module for TraceOps backend fallback
# Provides deterministic in‑memory data structures matching the live API responses.
# This module is imported only when Exasol connectivity fails.

from typing import Any, Dict, List, Optional


def get_sample_incidents(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Return a small static list of incident dictionaries.
    The shape mirrors ``database.get_incident_investigations``.
    Filtering logic is applied to keep the fallback behavior reasonable.
    """
    all_incidents: List[Dict[str, Any]] = [
        {
            "incident_id": "INC-001",
            "check_id": "CHK-1001",
            "run_id": "RUN-2001",
            "pipeline_name": "pipe_raw_ecommerce_orders",
            "pipeline_status": "FAILED",
            "dataset_name": "raw_ecommerce_orders",
            "check_type": "ROW_COUNT",
            "severity": "CRITICAL",
            "check_status": "FAILED",
            "expected_value": 1000000,
            "actual_value": 950000,
            "evidence_details": "Row count below expected threshold",
            "observed_at": "2026-10-20T08:15:00Z",
            "error_code": "ERR_DB_CONN_TIMEOUT",
            "error_message": "Connection timed out",
            "kpi_name": "Daily GMV",
            "report_name": "GMV Dashboard",
            "deviation_percent": 5.0,
            "business_impact": "Potential revenue loss",
            "associated_kpis": [],
            "downstream_datasets": ["stg_ecommerce_orders", "fct_daily_sales"],
        },
        {
            "incident_id": "INC-002",
            "check_id": "CHK-1002",
            "run_id": "RUN-2002",
            "pipeline_name": "pipe_raw_pos_transactions",
            "pipeline_status": "WARNING",
            "dataset_name": "raw_pos_transactions",
            "check_type": "VALUE_RANGE",
            "severity": "HIGH",
            "check_status": "WARNING",
            "expected_value": "0-100",
            "actual_value": "-5",
            "evidence_details": "Negative transaction amount detected",
            "observed_at": "2026-10-21T14:30:00Z",
            "error_code": None,
            "error_message": None,
            "kpi_name": "Average Order Value",
            "report_name": "POS Metrics",
            "deviation_percent": 12.5,
            "business_impact": "Skewed AOV reporting",
            "associated_kpis": [],
            "downstream_datasets": ["stg_pos_transactions", "fct_daily_sales"],
        },
    ]
    def matches(item: Dict[str, Any]) -> bool:
        if severity and item.get("severity", "").upper() != severity.upper():
            return False
        if status and item.get("pipeline_status", "").upper() != status.upper():
            return False
        return True
    filtered = [i for i in all_incidents if matches(i)]
    limited = filtered[:limit] if limit and limit > 0 else filtered
    summary = {
        "total_matching": len(filtered),
        "returned_count": len(limited),
        "critical_count": sum(1 for i in filtered if i.get("severity") == "CRITICAL"),
        "high_count": sum(1 for i in filtered if i.get("severity") == "HIGH"),
        "medium_count": sum(1 for i in filtered if i.get("severity") == "MEDIUM"),
        "low_count": sum(1 for i in filtered if i.get("severity") == "LOW"),
        "failed_count": sum(1 for i in filtered if i.get("pipeline_status") == "FAILED"),
        "warning_count": sum(1 for i in filtered if i.get("pipeline_status") == "WARNING"),
    }
    global_summary = {
        "total_incidents": len(all_incidents),
        "critical_count": sum(1 for i in all_incidents if i.get("severity") == "CRITICAL"),
        "high_count": sum(1 for i in all_incidents if i.get("severity") == "HIGH"),
    }
    return {
        "status": "success",
        "total_incidents": len(limited),
        "incidents": limited,
        "summary": summary,
        "global_summary": global_summary,
    }

