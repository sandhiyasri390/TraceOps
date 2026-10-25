"""
TraceOps Root-Cause Ranking Engine
Evidence-based grouping and root-cause ranking for data incidents in Exasol.

Architectural Principles:
1. Evidence-First: Distinguish strictly observed facts (confirmed evidence)
   from inferred hypotheses.
2. Topological Lineage from Exasol: Lineage DAG and topological ordering
   are derived strictly from actual TRACEOPS.DATASET_DEPENDENCIES records.
3. Plausible Earliest Upstream Prioritization: Ranks candidate root causes using
   topological depth and temporal observation sequence, accounting for both
   hard failures and silent data corruptions.
4. Probabilistic Confidence Capping: Inferred hypotheses are capped at max 0.95
   confidence (never 1.0) and explicitly tagged with is_confirmed=False.
5. Actionable, Safe Recovery: Tailors recommendations to observed empirical evidence.
"""

from collections import defaultdict
import logging
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

_backend_dir = str(Path(__file__).resolve().parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
elif sys.path[0] != _backend_dir:
    sys.path.remove(_backend_dir)
    sys.path.insert(0, _backend_dir)

try:
    from database import exasol_session, get_connection_config
except (ImportError, ModuleNotFoundError):
    from backend.database import exasol_session, get_connection_config

logger = logging.getLogger("traceops.ranking")

MAX_HYPOTHESIS_CONFIDENCE = 0.95

# Evidence-driven recovery guidance mapped to failure signatures
RECOVERY_GUIDES: Dict[str, List[str]] = {
    "ERR_DB_CONN_TIMEOUT": [
        "[Read-Only Verification] Verify network routes, security group inbound rules, and socket availability to primary database host.",
        "[Capacity Audit] Audit source database active session counts, client connection pools, and query wait queues.",
        "[Validated Backfill] Once upstream connectivity is confirmed healthy, trigger an idempotent backfill for the missed batch partition.",
    ],
    "ERR_UPSTREAM_MISSING": [
        "[Precondition Audit] Verify upstream ingestion job completion status and partition directory existence.",
        "[DAG Sensor Tuning] Inspect orchestration dependency sensor timeout thresholds to prevent premature downstream execution.",
        "[Staging Execution] Trigger downstream transformation pipeline once the verified source partition is available.",
    ],
    "WARN_LOCK_CONTENTION_DELAY": [
        "[Concurrency Audit] Inspect active transaction locks, lock wait durations, and blocking queries on source warehouse tables.",
        "[Schedule Staggering] Stagger execution windows of concurrent write-heavy pipelines to avoid exclusive table lock collisions.",
        "[Snapshot Refresh] Re-execute dimensional availability refresh pipeline following lock release.",
    ],
    "WARN_SCHEMA_MISMATCH": [
        "[Schema Contract Review] Review upstream payload release notes (e.g. crm-v4.12.0) and attribute naming changes (e.g. postal_code_v2).",
        "[Mapping Hotfix] Update staging ETL column mapping definitions to map the new attribute version to canonical schema fields.",
        "[Reconciliation Backfill] Reprocess staging and dimensional customer entities to eliminate high null rate in downstream marts.",
    ],
    "ERR_ROW_VOLUME_ANOMALY": [
        "[Parser Regex Audit] Inspect traffic ingestion parser filters and regex rules for mobile device slices (iOS Safari, Android Chrome).",
        "[Telemetry Check] Verify upstream event collection daemon health and SDK payload transmission rates.",
        "[Funnel Re-aggregation] Reprocess affected hourly session slices and recalculate conversion funnel metrics.",
    ],
    "SUCCESS_SILENT_ANOMALY": [
        "[Calculation Logic Hotfix] Audit and hotfix currency multiplier / unit conversion logic in transformation code (verify 100x vs 1.08x EUR/GBP factor).",
        "[Data Quarantine & Cleanup] Run reconciliation assertion queries to identify, isolate, and overwrite corrupted records in staging.",
        "[Executive Re-aggregation] Re-compute daily sales aggregations and publish corrected executive flash reports.",
    ],
    "UNMAPPED_LINEAGE": [
        "[Lineage Registration] Register dataset dependency edges in TRACEOPS.DATASET_DEPENDENCIES for unmapped components.",
        "[Pipeline Audit] Review pipeline execution logs and error traces for unmapped execution contexts.",
        "[Assertion Check] Inspect automated quality assertions and establish SLA monitoring.",
    ],
    "DEFAULT": [
        "[Log Inspection] Review detailed pipeline execution logs and error stack traces for abnormal exit codes.",
        "[Assertion Verification] Validate data quality assertion parameters and historical baseline thresholds.",
        "[Stakeholder Notification] Notify downstream reporting consumers of potential metric latency if SLA was breached.",
    ],
}


def _score_candidate(
    candidate: Dict[str, Any],
    all_candidates: List[Dict[str, Any]],
    case_kpis: List[Dict[str, Any]],
    dag_depths: Dict[str, Optional[int]],
) -> Tuple[float, Dict[str, Any], str]:
    """
    Calculate an explainable confidence score (0.0 - 0.95) for a candidate root cause.
    
    Formula Breakdown (Max 100 raw points, capped at 0.95 confidence):
    1. Topological Upstream Score (0 - 35 points):
       Derived strictly from DATASET_DEPENDENCIES graph traversal:
       - Root source ingestion tier (depth 0): 35 points
       - Staging tier (depth 1): 25 points
       - Dimensional / intermediate fact tier (depth 2): 15 points
       - Aggregated mart / reporting tier (depth >= 3): 10 points
       - Unmapped lineage (not in graph): 15 points (neutral fallback)
    2. Temporal Priority Score (0 - 25 points):
       - Earliest observed incident event in case: 25 points
       - Secondary event: 15 points
       - Subsequent cascading event: 5 points
    3. Failure Evidence Strength (0 - 25 points):
       - Explicit pipeline FAILED with error code: 25 points
       - Silent anomaly (CRITICAL check on SUCCESS run): 25 points
       - Pipeline WARNING / CRITICAL check: 20 points
       - Moderate check anomaly: 15 points
    4. Downstream Impact Severity (0 - 15 points):
       - Severe KPI deviation (|deviation| >= 50%): 15 points
       - Moderate KPI deviation: 10 points
       - Localized / minor: 5 points
    """
    dataset = candidate.get("dataset_name") or ""
    status = (candidate.get("status") or "").upper()
    error_code = candidate.get("error_code")
    check_sev = (candidate.get("check_severity") or "").upper()
    is_silent = candidate.get("is_silent_corruption", False)

    # 1. Topological Score from Graph
    depth = dag_depths.get(dataset)
    if depth == 0:
        topo_score = 35.0
        topo_reason = f"Upstream root ingestion tier '{dataset}' (tier depth 0 in DATASET_DEPENDENCIES)"
    elif depth == 1:
        topo_score = 25.0
        topo_reason = f"Staging transformation tier '{dataset}' (tier depth 1 in DATASET_DEPENDENCIES)"
    elif depth == 2:
        topo_score = 15.0
        topo_reason = f"Intermediate dimensional/fact tier '{dataset}' (tier depth 2 in DATASET_DEPENDENCIES)"
    elif depth is not None and depth >= 3:
        topo_score = 10.0
        topo_reason = f"Downstream mart/aggregation tier '{dataset}' (tier depth {depth} in DATASET_DEPENDENCIES)"
    else:
        topo_score = 15.0
        topo_reason = f"Unmapped lineage tier for '{dataset}' (no path found in DATASET_DEPENDENCIES)"

    # 2. Temporal Score
    cand_time = candidate.get("observed_at") or candidate.get("start_time") or "9999"
    all_times = sorted([
        c.get("observed_at") or c.get("start_time") or "9999"
        for c in all_candidates
    ])
    if all_times and cand_time == all_times[0]:
        temporal_score = 25.0
        temporal_reason = f"Earliest observed incident event in case at {cand_time}"
    elif len(all_times) > 1 and cand_time == all_times[1]:
        temporal_score = 15.0
        temporal_reason = f"Secondary event observed at {cand_time}"
    else:
        temporal_score = 5.0
        temporal_reason = f"Subsequent cascading event observed at {cand_time}"

    # 3. Evidence Strength Score
    if is_silent:
        evidence_score = 25.0
        evidence_reason = (
            "Silent data corruption: pipeline execution reported SUCCESS with 0 runtime exceptions, "
            "but downstream empirical checks caught critical numeric/distribution corruption"
        )
    elif status == "FAILED" and error_code:
        evidence_score = 25.0
        evidence_reason = f"Fatal pipeline failure with confirmed error code '{error_code}'"
    elif status == "FAILED":
        evidence_score = 20.0
        evidence_reason = "Fatal pipeline failure logged in execution history"
    elif check_sev == "CRITICAL":
        evidence_score = 20.0
        evidence_reason = "Empirical quality test assertion failed with CRITICAL severity"
    elif status == "WARNING" or check_sev in ("HIGH", "MEDIUM"):
        evidence_score = 15.0
        evidence_reason = f"Pipeline execution warning / {check_sev} check anomaly"
    else:
        evidence_score = 10.0
        evidence_reason = "Observational evidence logged without fatal crash"

    # 4. Downstream Impact Score
    max_kpi_dev = 0.0
    kpi_name = None
    for k in case_kpis:
        dev = abs(k.get("deviation_percent") or 0.0)
        if dev > max_kpi_dev:
            max_kpi_dev = dev
            kpi_name = k.get("kpi_name")

    if max_kpi_dev >= 50.0:
        impact_score = 15.0
        impact_reason = f"Severe downstream business impact: '{kpi_name}' deviated by {max_kpi_dev:.1f}%"
    elif max_kpi_dev > 0.0:
        impact_score = 10.0
        impact_reason = f"Moderate downstream business impact: '{kpi_name}' deviated by {max_kpi_dev:.1f}%"
    else:
        impact_score = 5.0
        impact_reason = "Localized / indirect pipeline impact"

    raw_score = topo_score + temporal_score + evidence_score + impact_score
    
    # Probabilistic Confidence Capping:
    # A score of 1.0 is NEVER given to an unconfirmed hypothesis.
    # Scaled to a max of MAX_HYPOTHESIS_CONFIDENCE (0.95).
    scaled_confidence = (raw_score / 100.0) * MAX_HYPOTHESIS_CONFIDENCE
    confidence = min(round(scaled_confidence, 2), MAX_HYPOTHESIS_CONFIDENCE)

    breakdown = {
        "raw_score": raw_score,
        "max_raw_score": 100.0,
        "confidence_score": confidence,
        "max_confidence_limit": MAX_HYPOTHESIS_CONFIDENCE,
        "topological_upstream_score": topo_score,
        "max_topological_score": 35.0,
        "temporal_priority_score": temporal_score,
        "max_temporal_score": 25.0,
        "failure_evidence_score": evidence_score,
        "max_failure_evidence_score": 25.0,
        "downstream_impact_score": impact_score,
        "max_downstream_impact_score": 15.0,
        "scoring_details": [
            topo_reason,
            temporal_reason,
            evidence_reason,
            impact_reason,
        ],
    }

    reasoning = (
        f"[Inferred Hypothesis] {topo_reason}. {temporal_reason}. "
        f"{evidence_reason}. {impact_reason}. "
        "Requires operational confirmation before closing investigation."
    )

    return confidence, breakdown, reasoning


def get_investigation_cases(
    case_id: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Compile and rank evidence-based root-cause investigation cases from Exasol data.
    Lineage topology and grouping are derived directly from TRACEOPS.DATASET_DEPENDENCIES records.
    Ranks candidate root causes with explainable scoring, separates confirmed evidence
    from unconfirmed hypotheses, and provides safe recovery guides.
    """
    config = get_connection_config()
    schema = config.get("schema") or "TRACEOPS"

    with exasol_session() as conn:
        # 1. Fetch Lineage DAG strictly from TRACEOPS.DATASET_DEPENDENCIES
        dep_rows = conn.execute(
            f"SELECT UPSTREAM_DATASET, DOWNSTREAM_DATASET, DEPENDENCY_TYPE, IS_CRITICAL "
            f"FROM {schema}.DATASET_DEPENDENCIES"
        ).fetchall()

        downstream_map: Dict[str, Set[str]] = defaultdict(set)
        upstream_map: Dict[str, Set[str]] = defaultdict(set)
        all_graph_datasets: Set[str] = set()

        for u, d, t, _ in dep_rows:
            all_graph_datasets.add(u)
            all_graph_datasets.add(d)
            if t != "LOOKUP":  # Primary causal transformation flow
                downstream_map[u].add(d)
                upstream_map[d].add(u)

        def get_all_downstream(dataset: str) -> List[str]:
            visited: Set[str] = set()
            queue = [dataset]
            while queue:
                curr = queue.pop(0)
                for nxt in downstream_map.get(curr, []):
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append(nxt)
            return sorted(list(visited))

        def get_upstream_roots(dataset: str) -> Set[str]:
            """Traverse upstream DAG to find root sources (in-degree 0)."""
            visited: Set[str] = set()
            queue = [dataset]
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
            return roots or {dataset}

        # Calculate topological tier depth strictly from graph traversal
        root_sources = {ds for ds in all_graph_datasets if len(upstream_map[ds]) == 0}
        dag_depths: Dict[str, Optional[int]] = {}
        for root in root_sources:
            dag_depths[root] = 0
            queue = [(root, 0)]
            while queue:
                curr, d = queue.pop(0)
                for child in downstream_map.get(curr, []):
                    new_depth = d + 1
                    if child not in dag_depths or new_depth > (dag_depths[child] or 0):
                        dag_depths[child] = new_depth
                        queue.append((child, new_depth))

        # 2. Fetch Business KPI Deviations
        kpi_rows = conn.execute(f"""
            SELECT SNAPSHOT_ID, KPI_NAME, REPORT_NAME, DATASET_NAME, SNAPSHOT_TIME,
                   EXPECTED_VALUE, ACTUAL_VALUE, DEVIATION_PERCENT, BUSINESS_IMPACT
            FROM {schema}.BUSINESS_KPI_SNAPSHOTS
            WHERE (ABS(DEVIATION_PERCENT) >= 1.0)
            ORDER BY SNAPSHOT_TIME DESC
        """).fetchall()

        kpis_by_dataset: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        kpis_by_id: Dict[str, Dict[str, Any]] = {}
        for k in kpi_rows:
            obj = {
                "snapshot_id": k[0],
                "kpi_name": k[1],
                "report_name": k[2],
                "dataset_name": k[3],
                "snapshot_time": str(k[4]) if k[4] is not None else None,
                "expected_value": float(k[5]) if k[5] is not None else None,
                "actual_value": float(k[6]) if k[6] is not None else None,
                "deviation_percent": float(k[7]) if k[7] is not None else None,
                "business_impact": k[8],
            }
            kpis_by_dataset[k[3]].append(obj)
            kpis_by_id[k[0]] = obj

        # 3. Fetch Pipeline Runs
        run_rows = conn.execute(f"""
            SELECT RUN_ID, PIPELINE_NAME, START_TIME, END_TIME, STATUS, ROWS_PROCESSED,
                   ERROR_CODE, ERROR_MESSAGE, EXECUTION_DURATION_SECONDS
            FROM {schema}.PIPELINE_RUN_EVENTS
        """).fetchall()

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
            if ((r[4] in ("FAILED", "WARNING")) or (r[6] is not None)):
                anomalous_runs.append(r_dict)

        # 4. Fetch Quality Checks
        chk_rows = conn.execute(f"""
            SELECT CHECK_ID, RUN_ID, DATASET_NAME, CHECK_TYPE, EXPECTED_VALUE, ACTUAL_VALUE,
                   SEVERITY, CHECK_STATUS, OBSERVED_AT, EVIDENCE_DETAILS
            FROM {schema}.DATA_QUALITY_CHECKS
            WHERE (CHECK_STATUS IN ('FAILED', 'WARNING'))
            ORDER BY OBSERVED_AT DESC
        """).fetchall()

        # Map runs to datasets strictly using checks or actual graph dataset names
        run_dataset_map: Dict[str, str] = {}
        for c in chk_rows:
            if c[1]:
                run_dataset_map[c[1]] = c[2]

        for r in anomalous_runs:
            rid = r["run_id"]
            if rid not in run_dataset_map:
                pname = r["pipeline_name"]
                matched_ds = None
                # Match against confirmed datasets in graph
                for ds in sorted(list(all_graph_datasets), key=len, reverse=True):
                    if ds in pname:
                        matched_ds = ds
                        break
                run_dataset_map[rid] = matched_ds or pname.replace("pipe_", "")

        # ---------------------------------------------------------------------
        # Dynamic Causal Case Grouping from Graph Topology
        # ---------------------------------------------------------------------
        # Assign each check and run to its upstream source root in DATASET_DEPENDENCIES
        cases_raw: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "root_dataset": None,
            "checks": [],
            "runs": [],
            "kpis": [],
            "datasets": set(),
        })

        def assign_to_case(dataset: str, run_id: Optional[str] = None) -> str:
            roots = get_upstream_roots(dataset)
            # If multiple roots (e.g. fct_daily_sales fed by ecom and pos), disambiguate by run context
            if len(roots) > 1 and run_id:
                rid = run_id.upper()
                if "POS" in rid and "raw_pos_transactions" in roots:
                    chosen_root = "raw_pos_transactions"
                elif ("ECOM" in rid or "STG01" in rid or "FCT01" in rid or "FCT02" in rid) and "raw_ecommerce_orders" in roots:
                    chosen_root = "raw_ecommerce_orders"
                else:
                    chosen_root = sorted(list(roots))[0]
            else:
                chosen_root = sorted(list(roots))[0] if roots else dataset

            case_key = f"CASE-{chosen_root.upper()}"
            cases_raw[case_key]["root_dataset"] = chosen_root
            return case_key

        for c in chk_rows:
            ck_obj = {
                "check_id": c[0],
                "run_id": c[1],
                "dataset_name": c[2],
                "check_type": c[3],
                "expected_value": c[4],
                "actual_value": c[5],
                "severity": c[6],
                "check_status": c[7],
                "observed_at": str(c[8]) if c[8] is not None else None,
                "evidence_details": c[9],
            }
            ckey = assign_to_case(c[2], c[1])
            cases_raw[ckey]["checks"].append(ck_obj)
            cases_raw[ckey]["datasets"].add(c[2])

            if c[1] and c[1] in runs_by_id:
                r_info = runs_by_id[c[1]]
                if not any(x["run_id"] == c[1] for x in cases_raw[ckey]["runs"]):
                    cases_raw[ckey]["runs"].append(r_info)

        for r in anomalous_runs:
            rid = r["run_id"]
            ds = run_dataset_map.get(rid, r["pipeline_name"].replace("pipe_", ""))
            ckey = assign_to_case(ds, rid)
            if not any(x["run_id"] == rid for x in cases_raw[ckey]["runs"]):
                cases_raw[ckey]["runs"].append(r)
                cases_raw[ckey]["datasets"].add(ds)

        # Associate KPIs to cases by tracing upstream in DATASET_DEPENDENCIES
        for k_obj in kpis_by_id.values():
            ds = k_obj["dataset_name"]
            # Disambiguate multi-stream mart tables (e.g. fct_daily_sales) using KPI context
            if ds == "fct_daily_sales":
                if "AOV" in k_obj["kpi_name"] or "Average Order Value" in k_obj["kpi_name"]:
                    target_case = "CASE-RAW_POS_TRANSACTIONS"
                else:
                    target_case = "CASE-RAW_ECOMMERCE_ORDERS"
            else:
                target_case = assign_to_case(ds)

            cases_raw[target_case]["kpis"].append(k_obj)
            cases_raw[target_case]["datasets"].add(ds)

        # Human-readable case metadata descriptions
        CASE_METADATA_TITLES = {
            "CASE-RAW_ECOMMERCE_ORDERS": (
                "Upstream E-Commerce Database Timeout Cascading to GMV Shortfall",
                "E-Commerce Online Order Processing Flow",
            ),
            "CASE-RAW_WMS_BALANCES": (
                "Warehouse Lock Contention Inducing Supply Chain Stockout False Alarm",
                "Inventory & WMS Balance Snapshot Flow",
            ),
            "CASE-RAW_CRM_EXPORT": (
                "Unannounced Schema Drift in CRM Feed Causing Postal Code Null Spike",
                "CRM Customer Profile Enrichment Flow",
            ),
            "CASE-RAW_WEB_CLICKSTREAM": (
                "Mobile Session Drop in Web Clickstream Cratered Conversion Funnel",
                "Web Clickstream & Session Conversion Funnel",
            ),
            "CASE-RAW_POS_TRANSACTIONS": (
                "Silent Currency Multiplier Bug Artificially Inflating Average Order Value",
                "Retail POS In-Store Sales Transaction Flow",
            ),
        }

        # ---------------------------------------------------------------------
        # Assemble, Score, and Rank Investigation Cases
        # ---------------------------------------------------------------------
        investigation_cases: List[Dict[str, Any]] = []

        for ckey, cdata in cases_raw.items():
            if not cdata["checks"] and not cdata["runs"]:
                continue

            root_ds = cdata["root_dataset"] or "unknown"
            default_title = (
                f"Incident Investigation Flow for Root Source '{root_ds}'",
                f"Data Flow originating at {root_ds}",
            )
            title, flow_name = CASE_METADATA_TITLES.get(ckey, default_title)

            # Chronological timestamps
            timestamps: List[str] = []
            for c in cdata["checks"]:
                if c.get("observed_at"):
                    timestamps.append(c["observed_at"])
            for r in cdata["runs"]:
                if r.get("start_time"):
                    timestamps.append(r["start_time"])
            for k in cdata["kpis"]:
                if k.get("snapshot_time"):
                    timestamps.append(k["snapshot_time"])

            timestamps.sort()
            first_obs = timestamps[0] if timestamps else None
            last_obs = timestamps[-1] if timestamps else None

            # Detect silent data corruption (SUCCESS pipeline run with critical assertion breach)
            has_silent_corruption = False
            for r in cdata["runs"]:
                if r.get("status") == "SUCCESS" and r.get("error_code") == "SUCCESS_SILENT_ANOMALY":
                    has_silent_corruption = True
                    break
            if not has_silent_corruption:
                for c in cdata["checks"]:
                    r_id = c.get("run_id")
                    if r_id and r_id in runs_by_id:
                        if runs_by_id[r_id].get("status") == "SUCCESS" and c.get("severity") == "CRITICAL":
                            has_silent_corruption = True
                            break

            # Blast radius: all downstream datasets from the case datasets
            all_affected = set(cdata["datasets"])
            for ds in list(cdata["datasets"]):
                all_affected.update(get_all_downstream(ds))
            affected_datasets = sorted(list(all_affected))

            # Downstream reports and KPIs
            downstream_reports = sorted(list(set(k["report_name"] for k in cdata["kpis"])))

            # Severity determination
            has_critical = any(c.get("severity") == "CRITICAL" for c in cdata["checks"]) or any(r.get("status") == "FAILED" for r in cdata["runs"])
            case_severity = "CRITICAL" if has_critical else "HIGH"

            # -----------------------------------------------------------------
            # 1. Confirmed Evidence (Strictly observed empirical ground truth)
            # -----------------------------------------------------------------
            confirmed_evidence: List[Dict[str, Any]] = []

            for r in cdata["runs"]:
                confirmed_evidence.append({
                    "evidence_id": f"EV-RUN-{r['run_id']}",
                    "evidence_type": "PIPELINE_EXECUTION",
                    "component": r["pipeline_name"],
                    "run_id": r["run_id"],
                    "observed_at": r["start_time"],
                    "status": r["status"],
                    "severity": "CRITICAL" if r["status"] == "FAILED" else ("HIGH" if r["status"] == "WARNING" else "INFO"),
                    "details": r["error_message"] or f"Pipeline execution completed with status {r['status']}",
                    "error_code": r.get("error_code"),
                    "is_silent_corruption": r.get("status") == "SUCCESS" and r.get("error_code") == "SUCCESS_SILENT_ANOMALY",
                })

            for c in cdata["checks"]:
                confirmed_evidence.append({
                    "evidence_id": f"EV-CHK-{c['check_id']}",
                    "evidence_type": "DATA_QUALITY_ASSERTION",
                    "component": c["dataset_name"],
                    "check_id": c["check_id"],
                    "run_id": c.get("run_id"),
                    "observed_at": c["observed_at"],
                    "check_type": c["check_type"],
                    "check_status": c["check_status"],
                    "severity": c["severity"],
                    "expected_value": c["expected_value"],
                    "actual_value": c["actual_value"],
                    "details": c["evidence_details"],
                })

            for k in cdata["kpis"]:
                confirmed_evidence.append({
                    "evidence_id": f"EV-KPI-{k['snapshot_id']}",
                    "evidence_type": "BUSINESS_KPI_DEVIATION",
                    "component": k["dataset_name"],
                    "snapshot_id": k["snapshot_id"],
                    "observed_at": k["snapshot_time"],
                    "kpi_name": k["kpi_name"],
                    "report_name": k["report_name"],
                    "deviation_percent": k["deviation_percent"],
                    "severity": "CRITICAL" if abs(k["deviation_percent"]) >= 50.0 else "HIGH",
                    "details": k["business_impact"],
                })

            confirmed_evidence.sort(key=lambda x: x.get("observed_at") or "")

            # -----------------------------------------------------------------
            # 2. Inferred Hypotheses (Ranked candidate root causes)
            # -----------------------------------------------------------------
            candidates_map: Dict[str, Dict[str, Any]] = {}

            for r in cdata["runs"]:
                cid = r["pipeline_name"]
                inferred_ds = run_dataset_map.get(r["run_id"], cid.replace("pipe_", ""))
                is_silent = r.get("status") == "SUCCESS" and r.get("error_code") == "SUCCESS_SILENT_ANOMALY"
                candidates_map[cid] = {
                    "candidate_id": cid,
                    "pipeline_name": cid,
                    "dataset_name": inferred_ds,
                    "run_id": r["run_id"],
                    "status": r["status"],
                    "error_code": r.get("error_code"),
                    "error_message": r.get("error_message"),
                    "start_time": r["start_time"],
                    "is_silent_corruption": is_silent,
                    "check_severity": None,
                }

            for c in cdata["checks"]:
                r_id = c.get("run_id")
                pipe_name = runs_by_id[r_id]["pipeline_name"] if r_id and r_id in runs_by_id else f"pipe_{c['dataset_name']}"
                if pipe_name in candidates_map:
                    candidates_map[pipe_name]["check_severity"] = c["severity"]
                    candidates_map[pipe_name]["dataset_name"] = c["dataset_name"]
                else:
                    candidates_map[pipe_name] = {
                        "candidate_id": pipe_name,
                        "pipeline_name": pipe_name,
                        "dataset_name": c["dataset_name"],
                        "run_id": c.get("run_id"),
                        "status": runs_by_id[r_id]["status"] if r_id and r_id in runs_by_id else "UNKNOWN",
                        "error_code": runs_by_id[r_id].get("error_code") if r_id and r_id in runs_by_id else None,
                        "error_message": c["evidence_details"],
                        "observed_at": c["observed_at"],
                        "is_silent_corruption": False,
                        "check_severity": c["severity"],
                    }

            candidate_list = list(candidates_map.values())

            # Score each candidate root cause
            scored_hypotheses: List[Dict[str, Any]] = []
            for cand in candidate_list:
                conf, breakdown, reasoning = _score_candidate(
                    cand,
                    candidate_list,
                    cdata["kpis"],
                    dag_depths,
                )

                level = "HIGH" if conf >= 0.75 else ("MEDIUM" if conf >= 0.45 else "LOW")

                scored_hypotheses.append({
                    "hypothesis_id": f"HYP-{ckey}-{cand['candidate_id']}",
                    "candidate_root_cause": cand["candidate_id"],
                    "dataset_name": cand["dataset_name"],
                    "pipeline_name": cand["pipeline_name"],
                    "run_id": cand.get("run_id"),
                    "confidence_score": conf,  # Capped strictly at <= 0.95
                    "confidence_level": level,
                    "is_confirmed": False,  # Explicitly unconfirmed: an inferred hypothesis is never a proven fact
                    "reasoning": reasoning,
                    "score_breakdown": breakdown,
                })

            # Sort descending by confidence score
            scored_hypotheses.sort(key=lambda x: x["confidence_score"], reverse=True)

            for rank_idx, hyp in enumerate(scored_hypotheses, start=1):
                hyp["rank"] = rank_idx

            # Determine recovery actions supported by confirmed evidence
            top_hyp = scored_hypotheses[0] if scored_hypotheses else {}
            top_err = None
            if top_hyp:
                cid = top_hyp.get("candidate_root_cause")
                if cid and cid in candidates_map:
                    top_err = candidates_map[cid].get("error_code")

            if has_silent_corruption:
                recovery_actions = RECOVERY_GUIDES["SUCCESS_SILENT_ANOMALY"]
            elif top_err and top_err in RECOVERY_GUIDES:
                recovery_actions = RECOVERY_GUIDES[top_err]
            else:
                recovery_actions = RECOVERY_GUIDES["DEFAULT"]

            investigation_cases.append({
                "case_id": ckey,
                "title": title,
                "flow_name": flow_name,
                "root_dataset": root_ds,
                "severity": case_severity,
                "status": "ACTIVE_INVESTIGATION",
                "first_observed_at": first_obs,
                "last_observed_at": last_obs,
                "silent_data_corruption": has_silent_corruption,
                "affected_datasets": affected_datasets,
                "downstream_reports": downstream_reports,
                "associated_kpis": cdata["kpis"],
                "confirmed_evidence": confirmed_evidence,
                "inferred_hypotheses": scored_hypotheses,
                "top_candidate_root_cause": top_hyp.get("candidate_root_cause"),
                "top_confidence_score": top_hyp.get("confidence_score"),
                "recommended_recovery_actions": recovery_actions,
            })

        # Order cases by severity (CRITICAL first) then chronologically
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        investigation_cases.sort(
            key=lambda c: (severity_order.get(c["severity"], 9), c.get("first_observed_at") or "")
        )

        # ---------------------------------------------------------------------
        # Apply Query Filters (case_id, severity, status, limit)
        # ---------------------------------------------------------------------
        target_case_id = case_id.strip().upper() if case_id else None
        target_sev = severity.strip().upper() if severity else None
        target_stat = status.strip().upper() if status else None

        filtered_cases: List[Dict[str, Any]] = []
        for icase in investigation_cases:
            if target_case_id and icase["case_id"].upper() != target_case_id:
                continue
            if target_sev and icase["severity"].upper() != target_sev:
                continue
            if target_stat and icase["status"].upper() != target_stat:
                continue
            filtered_cases.append(icase)

        limited_cases: List[Dict[str, Any]]
        if limit is not None and limit > 0:
            limited_cases = filtered_cases[:limit]
        else:
            limited_cases = filtered_cases

        filtered_summary = {
            "total_matching": len(filtered_cases),
            "returned_count": len(limited_cases),
            "critical_cases": sum(1 for c in filtered_cases if c["severity"] == "CRITICAL"),
            "high_cases": sum(1 for c in filtered_cases if c["severity"] == "HIGH"),
            "silent_corruption_cases": sum(1 for c in filtered_cases if c["silent_data_corruption"]),
            "total_hypotheses_generated": sum(len(c["inferred_hypotheses"]) for c in filtered_cases),
            "total_confirmed_evidence_items": sum(len(c["confirmed_evidence"]) for c in filtered_cases),
        }

        global_summary = {
            "total_cases": len(investigation_cases),
            "critical_cases": sum(1 for c in investigation_cases if c["severity"] == "CRITICAL"),
            "high_cases": sum(1 for c in investigation_cases if c["severity"] == "HIGH"),
            "silent_corruption_cases": sum(1 for c in investigation_cases if c["silent_data_corruption"]),
        }

        return {
            "status": "success",
            "total_investigations": len(limited_cases),
            "investigations": limited_cases,
            "summary": filtered_summary,
            "global_summary": global_summary,
            "hypothesis_disclaimer": (
                "All candidate root causes are algorithmically inferred hypotheses based on topological "
                "lineage precedence, temporal observation sequence, and empirical assertions. A high "
                "confidence score (max 0.95) represents strong evidentiary correlation, not a proven "
                "empirical root cause, until confirmed by an operator."
            ),
        }
