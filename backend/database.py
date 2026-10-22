"""
Database connection module for TraceOps.
Provides reusable, secure connection handling for Exasol.
"""

from collections import defaultdict
from contextlib import contextmanager
import logging
import os
from pathlib import Path
import ssl
from typing import Any, Dict, Generator, List, Optional, Set
from dotenv import load_dotenv
import pyexasol
import time

# Configure logger
logger = logging.getLogger("traceops.database")

# Load environment variables from backend/.env or root .env
_current_dir = Path(__file__).resolve().parent
_root_dir = _current_dir.parent
load_dotenv(_current_dir / ".env")
load_dotenv(_root_dir / ".env")

# Default Starter Kit password file location on Windows
DEFAULT_STARTER_KIT_PASSWORD_PATH = (
    Path(os.environ.get("USERPROFILE", ""))
    / ".exasol-starter-kit"
    / "credentials"
    / "personal_sys_password"
)


def get_exasol_password() -> str:
    """
    Retrieve Exasol password securely.
    1. First check EXASOL_PASSWORD environment variable.
    2. Check EXASOL_PASSWORD_FILE path if specified.
    3. Fallback to Exasol Starter Kit personal_sys_password file.
    
    Raises:
        RuntimeError: If password is not found in environment or credential file.
    """
    # 1. Direct environment variable
    env_password = os.environ.get("EXASOL_PASSWORD")
    if env_password:
        return env_password.strip()

    # 2. Custom credentials file path
    custom_pw_path = os.environ.get("EXASOL_PASSWORD_FILE")
    if custom_pw_path:
        pw_file = Path(custom_pw_path)
        if pw_file.is_file():
            content = pw_file.read_text(encoding="utf-8").strip()
            if content:
                return content
        raise RuntimeError(f"Specified EXASOL_PASSWORD_FILE not found or empty: {custom_pw_path}")

    # 3. Default Starter Kit credentials file
    if DEFAULT_STARTER_KIT_PASSWORD_PATH.is_file():
        content = DEFAULT_STARTER_KIT_PASSWORD_PATH.read_text(encoding="utf-8").strip()
        if content:
            return content

    raise RuntimeError(
        "Exasol password could not be resolved. "
        "Please set EXASOL_PASSWORD environment variable or ensure local Starter Kit "
        "credentials exist at ~/.exasol-starter-kit/credentials/personal_sys_password."
    )


def is_local_or_dev_environment(dsn: str) -> bool:
    """
    Determine if target connection is local development environment.
    """
    env = os.environ.get("ENVIRONMENT", "development").lower()
    is_localhost = any(
        host in dsn.lower()
        for host in ("127.0.0.1", "localhost", "::1", "0.0.0.0")
    )
    return env in ("development", "dev", "test") or is_localhost


def get_connection_config() -> Dict[str, Any]:
    """
    Assemble sanitized configuration dictionary for Exasol connection.
    Does not log or expose the raw password.
    """
    dsn = os.environ.get("EXASOL_DSN", "127.0.0.1:8563").strip()
    user = os.environ.get("EXASOL_USER", "sys").strip()
    schema = os.environ.get("EXASOL_SCHEMA", "").strip()
    
    # Parse encryption flag (default: True)
    encryption_str = os.environ.get("EXASOL_ENCRYPTION", "true").lower()
    encryption = encryption_str in ("true", "1", "yes")

    # Determine TLS / self-signed certificate handling
    # Self-signed bypass is strictly confined to local development
    allow_self_signed_env = os.environ.get("EXASOL_ALLOW_SELF_SIGNED")
    if allow_self_signed_env is not None:
        allow_self_signed = allow_self_signed_env.lower() in ("true", "1", "yes")
    else:
        allow_self_signed = is_local_or_dev_environment(dsn)

    websocket_sslopt: Optional[Dict[str, Any]] = None
    if encryption and allow_self_signed:
        # Development mode bypass for local self-signed Exasol TLS certificate
        websocket_sslopt = {
            "cert_reqs": ssl.CERT_NONE,
            "check_hostname": False,
        }

    return {
        "dsn": dsn,
        "user": user,
        "schema": schema,
        "encryption": encryption,
        "websocket_sslopt": websocket_sslopt,
    }


def get_exasol_connection(**overrides) -> pyexasol.ExaConnection:
    """
    Open and return a new Exasol connection.
    Caller is responsible for closing the connection or using `exasol_session()`.
    """
    config = get_connection_config()
    config.update(overrides)
    
    # Securely retrieve password
    password = config.pop("password", None) or get_exasol_password()

    try:
        connection = pyexasol.connect(
            dsn=config["dsn"],
            user=config["user"],
            password=password,
            schema=config.get("schema", ""),
            encryption=config.get("encryption", True),
            websocket_sslopt=config.get("websocket_sslopt"),
            client_name="TraceOps-Backend",
            autocommit=True,
        )
        return connection
    except Exception as exc:
        # Log clean error without exposing credentials
        logger.error("Failed to connect to Exasol at %s as user %s: %s", config["dsn"], config["user"], exc)
        raise


@contextmanager
def exasol_session(**overrides) -> Generator[pyexasol.ExaConnection, None, None]:
    """
    Context manager providing a managed Exasol connection session.
    Automatically closes the connection upon exit.
    """
    conn = get_exasol_connection(**overrides)
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


def check_exasol_health() -> Dict[str, Any]:
    """
    Run health check query 'SELECT 1 AS test_value' against Exasol.
    Returns sanitized status payload suitable for API response.
    Never exposes credentials or internal secret paths.
    """
    config = get_connection_config()
    dsn = config["dsn"]
    user = config["user"]

    try:
        with exasol_session() as conn:
            # Measure latency
            start_time = time.time()
            stmt = conn.execute("SELECT 1 AS test_value")
            rows = stmt.fetchall()
            latency_ms = int((time.time() - start_time) * 1000)
            test_val = rows[0][0] if rows and len(rows) > 0 and len(rows[0]) > 0 else None

        return {
            "status": "healthy",
            "database": "Exasol",
            "dsn": dsn,
            "user": user,
            "test_value": test_val,
            "latency_ms": latency_ms,
            "message": "Successfully connected to Exasol and executed test query.",
        }
    except Exception as exc:
        # Sanitize exception message so passwords/tokens are never leaked
        clean_error = str(exc)
        logger.warning("Exasol health check failed: %s", clean_error)
        return {
            "status": "unhealthy",
            "database": "Exasol",
            "dsn": dsn,
            "user": user,
            "error": "Failed to connect to Exasol database. Check service availability and credentials.",
            "detail": clean_error if "password" not in clean_error.lower() else "Authentication failed",
        }


def get_incident_investigations(
    severity: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Retrieve evidence-first data incident investigations from Exasol.
    Queries TRACEOPS.PIPELINE_RUN_EVENTS, TRACEOPS.DATASET_DEPENDENCIES,
    TRACEOPS.DATA_QUALITY_CHECKS, and TRACEOPS.BUSINESS_KPI_SNAPSHOTS.

    Correlates pipeline execution anomalies, quality check observations,
    and business KPI deviations via the lineage graph.
    Supports parameter-safe filtering by severity, status, and limit.
    """
    config = get_connection_config()
    schema = config.get("schema") or "TRACEOPS"

    with exasol_session() as conn:
        # 1. Fetch lineage DAG from DATASET_DEPENDENCIES
        dep_query = f"SELECT UPSTREAM_DATASET, DOWNSTREAM_DATASET, DEPENDENCY_TYPE, IS_CRITICAL FROM {schema}.DATASET_DEPENDENCIES"
        dep_rows = conn.execute(dep_query).fetchall()

        dag: Dict[str, Set[str]] = defaultdict(set)
        for u, d, _, _ in dep_rows:
            dag[u].add(d)

        def get_downstream_datasets(dataset: str) -> List[str]:
            visited: Set[str] = set()
            queue = [dataset]
            while queue:
                curr = queue.pop(0)
                for nxt in dag.get(curr, []):
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append(nxt)
            return sorted(list(visited))

        # 2. Fetch business KPI deviations from BUSINESS_KPI_SNAPSHOTS
        # Wrapped in parentheses to prevent operator precedence ambiguity
        kpi_query = f"""
            SELECT SNAPSHOT_ID, KPI_NAME, REPORT_NAME, DATASET_NAME, SNAPSHOT_TIME,
                   EXPECTED_VALUE, ACTUAL_VALUE, DEVIATION_PERCENT, BUSINESS_IMPACT
            FROM {schema}.BUSINESS_KPI_SNAPSHOTS
            WHERE (ABS(DEVIATION_PERCENT) >= 1.0)
            ORDER BY SNAPSHOT_TIME DESC
        """
        kpi_rows = conn.execute(kpi_query).fetchall()
        kpis_by_dataset: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for k in kpi_rows:
            kpis_by_dataset[k[3]].append({
                "snapshot_id": k[0],
                "kpi_name": k[1],
                "report_name": k[2],
                "dataset_name": k[3],
                "snapshot_time": str(k[4]) if k[4] is not None else None,
                "expected_value": float(k[5]) if k[5] is not None else None,
                "actual_value": float(k[6]) if k[6] is not None else None,
                "deviation_percent": float(k[7]) if k[7] is not None else None,
                "business_impact": k[8],
            })

        # 3. Fetch all pipeline run events from PIPELINE_RUN_EVENTS
        run_query = f"""
            SELECT RUN_ID, PIPELINE_NAME, START_TIME, END_TIME, STATUS, ROWS_PROCESSED,
                   ERROR_CODE, ERROR_MESSAGE, EXECUTION_DURATION_SECONDS
            FROM {schema}.PIPELINE_RUN_EVENTS
        """
        run_rows = conn.execute(run_query).fetchall()
        runs_by_id: Dict[str, Dict[str, Any]] = {}
        anomalous_runs: List[Dict[str, Any]] = []
        for r in run_rows:
            r_dict = {
                "run_id": r[0],
                "pipeline_name": r[1],
                "start_time": str(r[2]) if r[2] is not None else None,
                "end_time": str(r[3]) if r[3] is not None else None,
                "status": r[4],
                "rows_processed": int(r[5]) if r[5] is not None else 0,
                "error_code": r[6],
                "error_message": r[7],
                "execution_duration_seconds": float(r[8]) if r[8] is not None else None,
            }
            runs_by_id[r[0]] = r_dict
            # Explicit grouping to prevent AND/OR precedence issues
            if ((r[4] in ("FAILED", "WARNING")) or (r[6] is not None)):
                anomalous_runs.append(r_dict)

        # 4. Fetch quality check observations from DATA_QUALITY_CHECKS
        # Explicit grouping with parentheses to guarantee precedence integrity
        chk_query = f"""
            SELECT CHECK_ID, RUN_ID, DATASET_NAME, CHECK_TYPE, EXPECTED_VALUE, ACTUAL_VALUE,
                   SEVERITY, CHECK_STATUS, OBSERVED_AT, EVIDENCE_DETAILS
            FROM {schema}.DATA_QUALITY_CHECKS
            WHERE (CHECK_STATUS IN ('FAILED', 'WARNING'))
            ORDER BY OBSERVED_AT DESC
        """
        chk_rows = conn.execute(chk_query).fetchall()

        all_incidents: List[Dict[str, Any]] = []
        covered_run_ids: Set[str] = set()

        # Combine quality check evidence with associated pipeline runs and downstream KPIs
        for c in chk_rows:
            check_id = c[0]
            run_id = c[1]
            dataset_name = c[2]
            check_type = c[3]
            expected_val = c[4]
            actual_val = c[5]
            sev = c[6]
            chk_status = c[7]
            observed_at = str(c[8]) if c[8] is not None else None
            evidence_details = c[9]

            run_info = runs_by_id.get(run_id, {})
            if run_id:
                covered_run_ids.add(run_id)

            downstream = get_downstream_datasets(dataset_name)
            candidate_datasets = [dataset_name] + downstream

            matched_kpis: List[Dict[str, Any]] = []
            for ds in candidate_datasets:
                matched_kpis.extend(kpis_by_dataset.get(ds, []))

            primary_kpi = matched_kpis[0] if matched_kpis else {}

            all_incidents.append({
                "incident_id": f"INC-{check_id}",
                "check_id": check_id,
                "run_id": run_id,
                "pipeline_name": run_info.get("pipeline_name"),
                "pipeline_status": run_info.get("status"),
                "dataset_name": dataset_name,
                "check_type": check_type,
                "severity": sev,
                "check_status": chk_status,
                "expected_value": expected_val,
                "actual_value": actual_val,
                "evidence_details": evidence_details,
                "observed_at": observed_at,
                "error_code": run_info.get("error_code"),
                "error_message": run_info.get("error_message"),
                "kpi_name": primary_kpi.get("kpi_name"),
                "report_name": primary_kpi.get("report_name"),
                "deviation_percent": primary_kpi.get("deviation_percent"),
                "business_impact": primary_kpi.get("business_impact"),
                "associated_kpis": matched_kpis,
                "downstream_datasets": downstream,
            })

        # Include standalone anomalous pipeline runs not referenced by check rows
        for r_dict in anomalous_runs:
            r_id = r_dict["run_id"]
            if r_id in covered_run_ids:
                continue

            pipe_name = r_dict["pipeline_name"]
            inferred_ds = pipe_name.replace("pipe_", "")
            downstream = get_downstream_datasets(inferred_ds)
            candidate_datasets = [inferred_ds] + downstream

            matched_kpis = []
            for ds in candidate_datasets:
                matched_kpis.extend(kpis_by_dataset.get(ds, []))
            primary_kpi = matched_kpis[0] if matched_kpis else {}

            run_sev = "CRITICAL" if r_dict["status"] == "FAILED" else "HIGH"

            all_incidents.append({
                "incident_id": f"INC-{r_id}",
                "check_id": None,
                "run_id": r_id,
                "pipeline_name": pipe_name,
                "pipeline_status": r_dict["status"],
                "dataset_name": inferred_ds,
                "check_type": "PIPELINE_EXECUTION_FAILURE" if r_dict["status"] == "FAILED" else "PIPELINE_EXECUTION_WARNING",
                "severity": run_sev,
                "check_status": r_dict["status"],
                "expected_value": "SUCCESS",
                "actual_value": r_dict["status"],
                "evidence_details": r_dict["error_message"] or f"Pipeline ended with error code {r_dict['error_code']}",
                "observed_at": r_dict["start_time"],
                "error_code": r_dict["error_code"],
                "error_message": r_dict["error_message"],
                "kpi_name": primary_kpi.get("kpi_name"),
                "report_name": primary_kpi.get("report_name"),
                "deviation_percent": primary_kpi.get("deviation_percent"),
                "business_impact": primary_kpi.get("business_impact"),
                "associated_kpis": matched_kpis,
                "downstream_datasets": downstream,
            })

        # ---------------------------------------------------------------------
        # Precise Filtering: severity, status, and limit
        # ---------------------------------------------------------------------
        target_sev = severity.strip().upper() if severity else None
        target_stat = status_filter.strip().upper() if status_filter else None

        filtered_incidents: List[Dict[str, Any]] = []
        for inc in all_incidents:
            # 1. Ensure severity matches exactly
            if target_sev and (inc.get("severity") or "").upper() != target_sev:
                continue

            # 2. Ensure status matches either check_status or pipeline_status
            if target_stat:
                chk_stat = (inc.get("check_status") or "").upper()
                pipe_stat = (inc.get("pipeline_status") or "").upper()
                if (chk_stat != target_stat) and (pipe_stat != target_stat):
                    continue

            filtered_incidents.append(inc)

        # 3. Apply limit strictly AFTER filtering
        limited_incidents: List[Dict[str, Any]]
        if limit is not None and limit > 0:
            limited_incidents = filtered_incidents[:limit]
        else:
            limited_incidents = filtered_incidents

        # 4. Recalculate summary from the filtered incident records
        filtered_summary = {
            "total_matching": len(filtered_incidents),
            "returned_count": len(limited_incidents),
            "critical_count": sum(1 for inc in filtered_incidents if inc.get("severity") == "CRITICAL"),
            "high_count": sum(1 for inc in filtered_incidents if inc.get("severity") == "HIGH"),
            "medium_count": sum(1 for inc in filtered_incidents if inc.get("severity") == "MEDIUM"),
            "low_count": sum(1 for inc in filtered_incidents if inc.get("severity") == "LOW"),
            "failed_count": sum(
                1 for inc in filtered_incidents
                if (inc.get("check_status") or "").upper() == "FAILED"
                or (inc.get("pipeline_status") or "").upper() == "FAILED"
            ),
            "warning_count": sum(
                1 for inc in filtered_incidents
                if (inc.get("check_status") or "").upper() == "WARNING"
                or (inc.get("pipeline_status") or "").upper() == "WARNING"
            ),
        }

        # Clear separation: also include global summary of overall system baseline
        global_summary = {
            "total_incidents": len(all_incidents),
            "critical_count": sum(1 for inc in all_incidents if inc.get("severity") == "CRITICAL"),
            "high_count": sum(1 for inc in all_incidents if inc.get("severity") == "HIGH"),
            "medium_count": sum(1 for inc in all_incidents if inc.get("severity") == "MEDIUM"),
            "low_count": sum(1 for inc in all_incidents if inc.get("severity") == "LOW"),
            "total_failed_checks": len(chk_rows),
            "total_anomalous_runs": len(anomalous_runs),
            "total_kpi_deviations": len(kpi_rows),
        }

        return {
            "status": "success",
            "total_incidents": len(limited_incidents),
            "incidents": limited_incidents,
            "summary": filtered_summary,
            "global_summary": global_summary,
        }


def get_quality_checks(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    dataset: Optional[str] = None,
    search: Optional[str] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Retrieve empirical quality checks and test assertions from Exasol.
    Queries TRACEOPS.DATA_QUALITY_CHECKS and correlates with TRACEOPS.DATASET_DEPENDENCIES
    to map assertions to active root-cause investigation cases.
    Supports parameter-safe filtering by status, severity, dataset, search text, and limit.
    """
    config = get_connection_config()
    schema = config.get("schema") or "TRACEOPS"

    with exasol_session() as conn:
        # 1. Fetch Lineage DAG to map datasets to investigation cases
        dep_rows = conn.execute(
            f"SELECT UPSTREAM_DATASET, DOWNSTREAM_DATASET, DEPENDENCY_TYPE FROM {schema}.DATASET_DEPENDENCIES"
        ).fetchall()

        upstream_map: Dict[str, Set[str]] = defaultdict(set)
        for u, d, t in dep_rows:
            if t != "LOOKUP":
                upstream_map[d].add(u)

        def get_upstream_roots(ds: str) -> Set[str]:
            visited: Set[str] = set()
            queue = [ds]
            roots: Set[str] = set()
            while queue:
                curr = queue.pop(0)
                parents = upstream_map.get(curr, set())
                if not parents:
                    roots.add(curr)
                else:
                    for p in parents:
                        if p not in visited:
                            visited.add(p)
                            queue.append(p)
            return roots or {ds}

        # 2. Fetch all empirical quality checks
        query = f"""
            SELECT CHECK_ID, RUN_ID, DATASET_NAME, CHECK_TYPE, EXPECTED_VALUE,
                   ACTUAL_VALUE, SEVERITY, CHECK_STATUS, OBSERVED_AT, EVIDENCE_DETAILS
            FROM {schema}.DATA_QUALITY_CHECKS
            ORDER BY OBSERVED_AT DESC
        """
        chk_rows = conn.execute(query).fetchall()

        all_checks: List[Dict[str, Any]] = []
        for r in chk_rows:
            cid = r[0]
            run_id = r[1]
            ds_name = r[2]
            ctype = r[3]
            exp_val = r[4]
            act_val = r[5]
            sev = (r[6] or "INFO").upper()
            cstatus = (r[7] or "UNKNOWN").upper()
            obs_at = str(r[8]) if r[8] is not None else None
            details = r[9]

            # Resolve associated investigation case ID
            roots = get_upstream_roots(ds_name)
            chosen_root = sorted(list(roots))[0] if roots else ds_name
            associated_case = f"CASE-{chosen_root.upper()}" if chosen_root else None

            all_checks.append({
                "check_id": cid,
                "run_id": run_id,
                "dataset_name": ds_name,
                "check_type": ctype,
                "expected_value": exp_val,
                "actual_value": act_val,
                "severity": sev,
                "check_status": cstatus,
                "observed_at": obs_at,
                "evidence_details": details,
                "associated_case_id": associated_case,
            })

        # Global summary statistics derived strictly from real database records
        global_summary = {
            "total_checks": len(all_checks),
            "passed_checks": sum(1 for c in all_checks if c["check_status"] == "PASSED"),
            "failed_checks": sum(1 for c in all_checks if c["check_status"] == "FAILED"),
            "warning_checks": sum(1 for c in all_checks if c["check_status"] == "WARNING"),
            "critical_checks": sum(1 for c in all_checks if c["severity"] == "CRITICAL"),
            "high_checks": sum(1 for c in all_checks if c["severity"] == "HIGH"),
            "medium_checks": sum(1 for c in all_checks if c["severity"] == "MEDIUM"),
            "low_checks": sum(1 for c in all_checks if c["severity"] == "LOW"),
            "unique_datasets": len(set(c["dataset_name"] for c in all_checks)),
        }

        # Apply user filters
        filtered_checks = all_checks

        if status and status.upper() != "ALL":
            target_status = status.upper().strip()
            filtered_checks = [c for c in filtered_checks if c["check_status"] == target_status]

        if severity and severity.upper() != "ALL":
            target_sev = severity.upper().strip()
            filtered_checks = [c for c in filtered_checks if c["severity"] == target_sev]

        if dataset and dataset.strip() and dataset.upper() != "ALL":
            target_ds = dataset.strip().lower()
            filtered_checks = [c for c in filtered_checks if c["dataset_name"].lower() == target_ds]

        if search and search.strip():
            q = search.strip().lower()
            filtered_checks = [
                c for c in filtered_checks
                if q in c["check_id"].lower()
                or q in c["check_type"].lower()
                or q in c["dataset_name"].lower()
                or q in (c["run_id"] or "").lower()
                or q in c["evidence_details"].lower()
                or q in (c["expected_value"] or "").lower()
                or q in (c["actual_value"] or "").lower()
            ]

        # Apply limit if requested
        limited_checks = filtered_checks[:limit] if (limit and limit > 0) else filtered_checks

        filtered_summary = {
            "total_matching": len(filtered_checks),
            "passed_count": sum(1 for c in filtered_checks if c["check_status"] == "PASSED"),
            "failed_count": sum(1 for c in filtered_checks if c["check_status"] == "FAILED"),
            "warning_count": sum(1 for c in filtered_checks if c["check_status"] == "WARNING"),
            "critical_count": sum(1 for c in filtered_checks if c["severity"] == "CRITICAL"),
            "high_count": sum(1 for c in filtered_checks if c["severity"] == "HIGH"),
        }

        return {
            "status": "success",
            "total_matching": len(limited_checks),
            "total_all": len(all_checks),
            "checks": limited_checks,
            "summary": filtered_summary,
            "global_summary": global_summary,
        }


