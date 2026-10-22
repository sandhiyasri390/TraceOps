"""
TraceOps Data Lineage Engine
Extracts and builds the directed acyclic graph (DAG) of datasets and pipeline dependencies
directly from Exasol's TRACEOPS.DATASET_DEPENDENCIES, PIPELINE_RUN_EVENTS, DATA_QUALITY_CHECKS,
and BUSINESS_KPI_SNAPSHOTS.

Features:
1. Strict acyclic verification via Kahn's algorithm (zero invented/hardcoded edges).
2. Explicit topological layering (Stage 01 to Stage 05) with explicit handling for unmappable nodes.
3. Strict separation of direct dataset health (assertions/pipeline errors/silent corruption)
   from downstream operational impact (KPI deviations / cascade blast radius).
4. Full scenario reachability mapping across all 5 incident workflows.
"""

from collections import defaultdict, deque
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from database import exasol_session, get_connection_config

logger = logging.getLogger("traceops.lineage")


def check_dag_cycles(dataset_names: Set[str], edges: List[Dict[str, Any]]) -> Tuple[bool, List[str], List[str]]:
    """
    Kahn's algorithm for cycle detection on dataset dependency graph.
    Returns (is_acyclic, topo_order, cycle_nodes).
    """
    adj: Dict[str, List[str]] = defaultdict(list)
    in_degree: Dict[str, int] = {ds: 0 for ds in dataset_names}

    for e in edges:
        u, v = e["source"], e["target"]
        if u in in_degree and v in in_degree:
            adj[u].append(v)
            in_degree[v] += 1

    zero_in_queue = deque([ds for ds, deg in in_degree.items() if deg == 0])
    topo_order: List[str] = []
    in_deg_tracker = dict(in_degree)

    while zero_in_queue:
        curr = zero_in_queue.popleft()
        topo_order.append(curr)
        for nxt in adj[curr]:
            in_deg_tracker[nxt] -= 1
            if in_deg_tracker[nxt] == 0:
                zero_in_queue.append(nxt)

    is_acyclic = (len(topo_order) == len(dataset_names))
    cycle_nodes = [ds for ds in dataset_names if in_deg_tracker[ds] > 0]
    return is_acyclic, topo_order, cycle_nodes


def get_lineage_data() -> Dict[str, Any]:
    """
    Query Exasol TRACEOPS.DATASET_DEPENDENCIES and related operational tables
    to construct an interactive directed lineage graph without inventing edges.
    """
    config = get_connection_config()
    schema = config.get("schema") or "TRACEOPS"

    with exasol_session() as conn:
        # 1. Fetch exact dependency edges from Exasol
        dep_rows = conn.execute(f"""
            SELECT DEPENDENCY_ID, UPSTREAM_DATASET, DOWNSTREAM_DATASET, DEPENDENCY_TYPE, IS_CRITICAL
            FROM {schema}.DATASET_DEPENDENCIES
            ORDER BY DEPENDENCY_ID
        """).fetchall()

        # 2. Fetch pipeline runs for execution telemetry & component health
        run_rows = conn.execute(f"""
            SELECT RUN_ID, PIPELINE_NAME, STATUS, ERROR_CODE, ERROR_MESSAGE, EXECUTION_DURATION_SECONDS
            FROM {schema}.PIPELINE_RUN_EVENTS
            ORDER BY START_TIME DESC
        """).fetchall()

        # 3. Fetch empirical quality assertions
        chk_rows = conn.execute(f"""
            SELECT CHECK_ID, RUN_ID, DATASET_NAME, CHECK_TYPE, CHECK_STATUS, SEVERITY, EVIDENCE_DETAILS
            FROM {schema}.DATA_QUALITY_CHECKS
            ORDER BY OBSERVED_AT DESC
        """).fetchall()

        # 4. Fetch business KPI deviations
        kpi_rows = conn.execute(f"""
            SELECT SNAPSHOT_ID, KPI_NAME, REPORT_NAME, DATASET_NAME, DEVIATION_PERCENT, BUSINESS_IMPACT
            FROM {schema}.BUSINESS_KPI_SNAPSHOTS
            WHERE ABS(DEVIATION_PERCENT) >= 1.0
            ORDER BY SNAPSHOT_TIME DESC
        """).fetchall()

        # Build graph adjacency maps
        downstream_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        upstream_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        parents_map: Dict[str, List[str]] = defaultdict(list)
        all_dataset_names: Set[str] = set()

        edges: List[Dict[str, Any]] = []
        for dep_id, u, d, dep_type, is_crit in dep_rows:
            all_dataset_names.add(u)
            all_dataset_names.add(d)
            edge_obj = {
                "dependency_id": dep_id,
                "source": u,
                "target": d,
                "dependency_type": dep_type,
                "is_critical": bool(is_crit),
            }
            edges.append(edge_obj)
            downstream_map[u].append(edge_obj)
            upstream_map[d].append(edge_obj)
            parents_map[d].append(u)

        # ---------------------------------------------------------------------
        # Kahn's Algorithm: Cycle Detection & Exact Topological Depth Computation
        # ---------------------------------------------------------------------
        is_acyclic, topo_order, cycle_nodes = check_dag_cycles(all_dataset_names, edges)
        if not is_acyclic:
            logger.error("Cycle detected in TRACEOPS.DATASET_DEPENDENCIES involving: %s", cycle_nodes)

        # Topological layer / depth (longest path from root source)
        depth_map: Dict[str, Optional[int]] = {}
        for n in topo_order:
            if not parents_map[n]:
                depth_map[n] = 0
            else:
                p_depths = [depth_map[p] for p in parents_map[n] if p in depth_map and depth_map[p] is not None]
                depth_map[n] = (1 + max(p_depths)) if p_depths else 0

        # Mark any unresolved or cyclic nodes explicitly as None
        for ds in all_dataset_names:
            if ds not in depth_map:
                depth_map[ds] = None

        # Build full upstream ancestor map for cascade impact evaluation
        ancestors_map: Dict[str, Set[str]] = defaultdict(set)
        for ds in all_dataset_names:
            queue_anc = list(parents_map[ds])
            while queue_anc:
                p = queue_anc.pop(0)
                if p not in ancestors_map[ds]:
                    ancestors_map[ds].add(p)
                    queue_anc.extend(parents_map[p])

        # ---------------------------------------------------------------------
        # Index Assertions, Pipeline Runs, and KPIs
        # ---------------------------------------------------------------------
        checks_by_dataset: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for c in chk_rows:
            checks_by_dataset[c[2]].append({
                "check_id": c[0],
                "run_id": c[1],
                "dataset_name": c[2],
                "check_type": c[3],
                "check_status": c[4],
                "severity": c[5],
                "evidence_details": c[6],
            })

        kpis_by_dataset: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for k in kpi_rows:
            kpis_by_dataset[k[3]].append({
                "snapshot_id": k[0],
                "kpi_name": k[1],
                "report_name": k[2],
                "dataset_name": k[3],
                "deviation_percent": float(k[4]) if k[4] is not None else None,
                "business_impact": k[5],
            })

        # Map runs to datasets via check associations and name correlation
        run_to_ds: Dict[str, Set[str]] = defaultdict(set)
        for c in chk_rows:
            if c[1] and c[2]:
                run_to_ds[c[1]].add(c[2])

        runs_by_dataset: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for r in run_rows:
            r_obj = {
                "run_id": r[0],
                "pipeline_name": r[1],
                "status": r[2],
                "error_code": r[3],
                "error_message": r[4],
                "duration_seconds": float(r[5]) if r[5] is not None else None,
            }
            rid = r[0]
            pname = r[1]
            mapped_targets = set(run_to_ds.get(rid, set()))
            clean_pname = pname.replace("pipe_", "")
            for ds in all_dataset_names:
                if (
                    ds == clean_pname
                    or ds.replace("raw_", "") == clean_pname.replace("raw_", "")
                    or clean_pname in ds
                    or ds in clean_pname
                ):
                    mapped_targets.add(ds)

            for target_ds in mapped_targets:
                runs_by_dataset[target_ds].append(r_obj)

        # ---------------------------------------------------------------------
        # Scenario Reachability Mapping
        # ---------------------------------------------------------------------
        scenario_roots = {
            "CASE-RAW_ECOMMERCE_ORDERS": {
                "title": "Upstream E-Commerce Database Timeout Cascading to GMV Shortfall",
                "flow_name": "E-Commerce Online Order Processing Flow",
                "root_dataset": "raw_ecommerce_orders",
                "severity": "CRITICAL",
            },
            "CASE-RAW_POS_TRANSACTIONS": {
                "title": "Silent Currency Multiplier Bug Artificially Inflating Average Order Value",
                "flow_name": "Retail POS In-Store Sales Transaction Flow",
                "root_dataset": "raw_pos_transactions",
                "severity": "CRITICAL",
            },
            "CASE-RAW_CRM_EXPORT": {
                "title": "Unannounced Schema Drift in CRM Feed Causing Postal Code Null Spike",
                "flow_name": "CRM Customer Profile Enrichment Flow",
                "root_dataset": "raw_crm_export",
                "severity": "CRITICAL",
            },
            "CASE-RAW_WEB_CLICKSTREAM": {
                "title": "Mobile Session Drop in Web Clickstream Cratered Conversion Funnel",
                "flow_name": "Web Clickstream & Session Conversion Funnel",
                "root_dataset": "raw_web_clickstream",
                "severity": "CRITICAL",
            },
            "CASE-RAW_WMS_BALANCES": {
                "title": "Warehouse Lock Contention Inducing Supply Chain Stockout False Alarm",
                "flow_name": "Inventory & WMS Balance Snapshot Flow",
                "root_dataset": "raw_wms_balances",
                "severity": "HIGH",
            },
        }

        def get_all_downstream(start_ds: str) -> Set[str]:
            reach: Set[str] = {start_ds}
            bfs = [start_ds]
            while bfs:
                curr = bfs.pop(0)
                for edge in downstream_map.get(curr, []):
                    nxt = edge["target"]
                    if nxt not in reach:
                        reach.add(nxt)
                        bfs.append(nxt)
            return reach

        scenario_datasets_map: Dict[str, Set[str]] = {}
        for cid, meta in scenario_roots.items():
            scenario_datasets_map[cid] = get_all_downstream(meta["root_dataset"])

        dataset_cases_map: Dict[str, List[str]] = defaultdict(list)
        for cid, reach_set in scenario_datasets_map.items():
            for ds in reach_set:
                dataset_cases_map[ds].append(cid)

        # ---------------------------------------------------------------------
        # Direct Health vs Downstream Impact Classification
        # ---------------------------------------------------------------------
        direct_health_map: Dict[str, str] = {}
        direct_issues_map: Dict[str, List[str]] = defaultdict(list)
        silent_corruption_set: Set[str] = set()

        for ds in sorted(list(all_dataset_names)):
            ds_checks = checks_by_dataset.get(ds, [])
            ds_runs = runs_by_dataset.get(ds, [])

            failed_checks = [c for c in ds_checks if c["check_status"] == "FAILED"]
            critical_checks = [c for c in failed_checks if c["severity"] == "CRITICAL"]
            high_failed_checks = [c for c in failed_checks if c["severity"] == "HIGH"]
            warn_checks = [c for c in ds_checks if c["check_status"] == "WARNING"]
            failed_runs = [r for r in ds_runs if r["status"] == "FAILED"]
            warn_runs = [r for r in ds_runs if r["status"] == "WARNING"]

            for c in failed_checks:
                direct_issues_map[ds].append(
                    f"Failed Quality Check: {c['check_type']} ({c['severity']}) - {c['evidence_details']}"
                )
            for c in warn_checks:
                direct_issues_map[ds].append(
                    f"Warning Quality Check: {c['check_type']} ({c['severity']}) - {c['evidence_details']}"
                )
            for r in failed_runs:
                err_code = r.get("error_code") or "ERROR"
                err_msg = f": {r['error_message']}" if r.get("error_message") else ""
                direct_issues_map[ds].append(
                    f"Pipeline Execution Failed: {r['pipeline_name']} ({err_code}){err_msg}"
                )
            for r in warn_runs:
                err_code = r.get("error_code") or "WARNING"
                err_msg = f": {r['error_message']}" if r.get("error_message") else ""
                direct_issues_map[ds].append(
                    f"Pipeline Execution Warning: {r['pipeline_name']} ({err_code}){err_msg}"
                )

            # Silent corruption check: pipeline reported SUCCESS or no failure, but output failed empirical quality assertions
            has_success_run = any(r["status"] == "SUCCESS" for r in ds_runs)
            has_failed_check = len(failed_checks) > 0
            has_failed_run = len(failed_runs) > 0
            if has_failed_check and not has_failed_run:
                silent_corruption_set.add(ds)
                direct_issues_map[ds].append(
                    "Silent Data Corruption: Associated pipeline reported SUCCESS/no failure, but output failed empirical quality assertions"
                )

            # Direct Health determination:
            # A dataset is NEVER labeled HEALTHY if it has failed checks, failed runs, warning checks, or warning runs
            if len(critical_checks) > 0 or len(failed_runs) > 0:
                direct_health_map[ds] = "CRITICAL"
            elif len(failed_checks) > 0:
                direct_health_map[ds] = "CRITICAL" if len(high_failed_checks) > 0 else "WARNING"
            elif len(warn_checks) > 0 or len(warn_runs) > 0:
                direct_health_map[ds] = "WARNING"
            else:
                direct_health_map[ds] = "HEALTHY"

        # ---------------------------------------------------------------------
        # Construct Nodes Payload with Explicit Layering & Health Separation
        # ---------------------------------------------------------------------
        nodes: List[Dict[str, Any]] = []
        for ds in sorted(list(all_dataset_names)):
            in_deg = len(upstream_map[ds])
            out_deg = len(downstream_map[ds])
            raw_depth = depth_map.get(ds)

            if in_deg == 0 or ds.startswith("raw_"):
                node_type = "SOURCE_DATASET"
                tier = "source"
            elif out_deg == 0 or ds.startswith("rpt_"):
                node_type = "DOWNSTREAM_DATASET"
                tier = "report"
            else:
                node_type = "TRANSFORMATION"
                if ds.startswith("stg_"):
                    tier = "staging"
                elif ds.startswith("dim_"):
                    tier = "dimension"
                elif ds.startswith("fct_"):
                    tier = "fact"
                else:
                    tier = "transformation"

            dh = direct_health_map.get(ds, "HEALTHY")
            ds_kpis = kpis_by_dataset.get(ds, [])
            has_upstream_failure = any(direct_health_map.get(anc) in ("CRITICAL", "WARNING") for anc in ancestors_map.get(ds, []))

            if len(ds_kpis) > 0:
                downstream_impact = "CRITICAL_KPI_DEVIATION"
            elif has_upstream_failure:
                downstream_impact = "AFFECTED_BY_UPSTREAM"
            else:
                downstream_impact = "NONE"

            # Overall display status (Requirement 5)
            if dh == "CRITICAL":
                overall_status = "CRITICAL"
            elif dh == "WARNING":
                overall_status = "WARNING"
            elif downstream_impact == "CRITICAL_KPI_DEVIATION":
                overall_status = "IMPACTED"
            elif downstream_impact == "AFFECTED_BY_UPSTREAM":
                overall_status = "CASCADE_DEGRADED"
            else:
                overall_status = "HEALTHY"

            pipeline_names = list(dict.fromkeys(r["pipeline_name"] for r in runs_by_dataset.get(ds, [])))

            # Stage mapping (Stages 1 through 5)
            # Stage 1: Ingestion Sources (Depth 0)
            # Stage 2: Staging & Master Dims (Depth 1)
            # Stage 3: Dimensional Core (Depth 2)
            # Stage 4: Fact Marts & Operational Radars (Depth 3)
            # Stage 5: Consolidated Marts & Executive Reports (Depth 4 & 5)
            stage_idx: Optional[int] = None
            stage_name: Optional[str] = None

            if raw_depth is not None:
                if raw_depth == 0:
                    stage_idx = 1
                    stage_name = "STAGE 01: Ingestion Sources"
                elif raw_depth == 1:
                    stage_idx = 2
                    stage_name = "STAGE 02: Staging & Master Dims"
                elif raw_depth == 2:
                    stage_idx = 3
                    stage_name = "STAGE 03: Dimensional Core"
                elif raw_depth == 3:
                    stage_idx = 4
                    stage_name = "STAGE 04: Fact Marts & Operational Radars"
                else:
                    stage_idx = 5
                    stage_name = "STAGE 05: Consolidated Marts & Executive Rollup"
            else:
                stage_idx = None
                stage_name = "UNMAPPED: Unresolved Topology"

            node_obj = {
                "id": ds,
                "name": ds,
                "node_type": node_type,
                "tier": tier,
                "depth": raw_depth,
                "stage_idx": stage_idx,
                "stage_name": stage_name,
                "is_unmapped": (raw_depth is None),
                "in_degree": in_deg,
                "out_degree": out_deg,
                "upstream_dependencies": [e["source"] for e in upstream_map.get(ds, [])],
                "downstream_dependents": [e["target"] for e in downstream_map.get(ds, [])],
                "direct_health": dh,
                "downstream_impact": downstream_impact,
                "health_status": overall_status,
                "is_silent_corruption": (ds in silent_corruption_set),
                "direct_issues": direct_issues_map.get(ds, []),
                "associated_pipelines": pipeline_names,
                "recent_runs": runs_by_dataset.get(ds, [])[:3],
                "quality_checks": checks_by_dataset.get(ds, []),
                "kpis": ds_kpis,
                "related_cases": dataset_cases_map.get(ds, []),
            }
            nodes.append(node_obj)

        scenarios_list: List[Dict[str, Any]] = []
        for cid, meta in scenario_roots.items():
            scenarios_list.append({
                "case_id": cid,
                "title": meta["title"],
                "flow_name": meta["flow_name"],
                "root_dataset": meta["root_dataset"],
                "severity": meta["severity"],
                "datasets": sorted(list(scenario_datasets_map[cid])),
                "node_count": len(scenario_datasets_map[cid]),
            })

        return {
            "status": "ok",
            "summary": {
                "total_nodes": len(nodes),
                "total_dependencies": len(edges),
                "is_acyclic": is_acyclic,
                "max_topological_depth": max((d for d in depth_map.values() if d is not None), default=0),
                "source_datasets": sum(1 for n in nodes if n["node_type"] == "SOURCE_DATASET"),
                "transformations": sum(1 for n in nodes if n["node_type"] == "TRANSFORMATION"),
                "downstream_datasets": sum(1 for n in nodes if n["node_type"] == "DOWNSTREAM_DATASET"),
                "critical_dependencies": sum(1 for e in edges if e["is_critical"]),
                "direct_critical_count": sum(1 for n in nodes if n["direct_health"] == "CRITICAL"),
                "silent_corruption_count": len(silent_corruption_set),
            },
            "nodes": nodes,
            "edges": edges,
            "scenarios": scenarios_list,
        }
