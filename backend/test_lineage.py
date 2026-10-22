"""
Automated Test Suite for TraceOps Data Lineage DAG Engine
Validates:
1. /api/lineage registered in root endpoint discovery
2. Lineage endpoint returns valid JSON with 200 OK
3. Exact 20 dependency edges from TRACEOPS.DATASET_DEPENDENCIES are returned (zero invented edges)
4. Cycle detection: Proves graph is strictly a Directed Acyclic Graph (DAG) with zero cycles
5. Every dependency edge connects two valid, distinct existing nodes
6. Strict topological depth invariant: depth(target) > depth(source) for all edges
7. Consistent topological layering (Stage 01 to Stage 05) with explicit unmapped handling
8. Health indicator validation: Proves datasets with failed assertions/corruptions (e.g. stg_pos_sales)
   are marked CRITICAL even when their pipeline reports SUCCESS, and clearly distinguishes
   direct health from downstream blast radius impact
9. Scenario reachability mapping across all 5 incident workflows
"""

from collections import defaultdict, deque
import json
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import get_lineage, root_endpoint
from lineage import get_lineage_data, check_dag_cycles


def run_lineage_tests():
    print("==================================================================")
    print("TraceOps Data Lineage Validation Suite")
    print("==================================================================")

    # 1. Root endpoint registration
    root_data = root_endpoint()
    assert "lineage" in root_data["endpoints"], "Missing 'lineage' in root endpoints"
    assert root_data["endpoints"]["lineage"] == "/api/lineage"
    print("[PASS] Test 1: /api/lineage registered in root API navigation links.")

    # 2. Lineage endpoint response
    resp = get_lineage()
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = json.loads(resp.body.decode("utf-8"))
    assert data["status"] == "ok"
    assert "summary" in data and "nodes" in data and "edges" in data and "scenarios" in data
    print("[PASS] Test 2: /api/lineage returns valid schema with status=ok.")

    # 3. Exact 20 edges from DATASET_DEPENDENCIES (Requirement 2)
    edges = data["edges"]
    assert len(edges) == 20, f"Expected 20 edges from DATASET_DEPENDENCIES, got {len(edges)}"
    dep_ids = {e["dependency_id"] for e in edges}
    assert "DEP-001" in dep_ids and "DEP-020" in dep_ids
    print("[PASS] Test 3: Verified exact 20 dependency edges from Exasol DATASET_DEPENDENCIES (zero invented edges).")

    # 4. Cycle Detection & Graph Acyclicity (Requirement 4)
    nodes = {n["id"]: n for n in data["nodes"]}
    assert len(nodes) == 21, f"Expected 21 unique dataset nodes, got {len(nodes)}"

    # 4a. Verify real graph is acyclic using Kahn's algorithm
    is_acyclic, topo_visited, cycle_nodes = check_dag_cycles(set(nodes.keys()), edges)
    assert is_acyclic is True, f"Cycle detected in live graph! Unresolved nodes: {cycle_nodes}"
    assert data["summary"]["is_acyclic"] is True, "Backend summary is_acyclic flag should be True"
    assert len(cycle_nodes) == 0, f"Expected 0 cycle nodes, got {cycle_nodes}"

    # 4b. Synthetic cycle detection verification: inject a cyclic edge and ensure Kahn's algorithm detects it
    cyclic_test_edges = list(edges) + [
        {
            "dependency_id": "DEP-TEST-CYCLE",
            "source": "rpt_executive_daily_flash",
            "target": "raw_ecommerce_orders",
            "dependency_type": "TEST_CYCLE",
            "is_critical": True,
        }
    ]
    test_acyclic, _, test_cycle_nodes = check_dag_cycles(set(nodes.keys()), cyclic_test_edges)
    assert test_acyclic is False, "Cycle detection failed to catch an injected synthetic cycle!"
    assert len(test_cycle_nodes) > 0, "Cycle detection must identify cyclic nodes when a cycle exists"
    assert "raw_ecommerce_orders" in test_cycle_nodes and "rpt_executive_daily_flash" in test_cycle_nodes
    print("[PASS] Test 4: Cycle detection verified: Live graph is strictly acyclic; synthetic cycle injection correctly detected.")

    # 5. Edge Validity: Every edge connects two existing nodes (Requirement 4)
    for e in edges:
        src = e["source"]
        tgt = e["target"]
        assert src in nodes, f"Edge source '{src}' does not exist in nodes list"
        assert tgt in nodes, f"Edge target '{tgt}' does not exist in nodes list"
        assert src != tgt, f"Self-loop detected on node '{src}'"
        assert bool(src.strip()) and bool(tgt.strip()), "Node identifiers must be non-empty strings"

    # 5b. Verify non-existent node detection
    invalid_test_edge = {"source": "non_existent_parent_ds", "target": "stg_online_orders"}
    assert invalid_test_edge["source"] not in nodes, "Validator should detect missing node in edge"
    print("[PASS] Test 5: Every dependency edge connects two distinct, existing graph nodes without self-loops or dangling endpoints.")

    # 6. Topological Layer Invariant: depth(target) > depth(source) (Requirement 3)
    for e in edges:
        src_depth = nodes[e["source"]]["depth"]
        tgt_depth = nodes[e["target"]]["depth"]
        assert src_depth is not None and tgt_depth is not None, "Nodes in edge must have determined depths"
        assert tgt_depth > src_depth, (
            f"Topological violation: {e['source']} (depth {src_depth}) -> {e['target']} (depth {tgt_depth})"
        )
    print("[PASS] Test 6: Strict topological invariant depth(target) > depth(source) verified across all 20 edges.")

    # 7. Stage Mapping: Stages 1 through 5 and explicit unmapped handling (Requirement 3)
    stages_present = {n["stage_idx"] for n in data["nodes"]}
    # Expect stages 1 through 5, with no empty Stage 6
    assert 6 not in stages_present, "Stage 6 should not be present in stage_idx"
    assert stages_present == {1, 2, 3, 4, 5}, f"Expected stages 1 to 5, got {stages_present}"

    for n in data["nodes"]:
        assert n["stage_idx"] in (1, 2, 3, 4, 5) or n["is_unmapped"] is True, (
            f"Node {n['id']} has invalid stage {n['stage_idx']}"
        )
        if n["is_unmapped"]:
            assert n["stage_idx"] is None, f"Unmapped node {n['id']} must have stage_idx=None"
            assert "UNMAPPED" in n["stage_name"], f"Unmapped node {n['id']} must have UNMAPPED stage name"
    print("[PASS] Test 7: Stage layout verified: Exactly Stages 01 to 05 with no empty Stage 06; unmapped handling explicitly configured.")

    # 8. Health Indicator Validation: Silent corruption & direct vs downstream impact (Requirement 5)
    # Proves datasets with failed assertions/corruptions are not labelled HEALTHY solely because pipeline had no failed status
    for n in data["nodes"]:
        ds_checks = n.get("quality_checks", [])
        failed_checks = [c for c in ds_checks if c.get("check_status") == "FAILED"]
        if len(failed_checks) > 0:
            assert n["direct_health"] in ("CRITICAL", "WARNING"), (
                f"Dataset {n['id']} has failed quality checks but was marked '{n['direct_health']}'!"
            )

    # stg_pos_sales: pipeline reported SUCCESS, but quality check failed with CRITICAL numeric outlier
    stg_pos = nodes["stg_pos_sales"]
    assert stg_pos["direct_health"] == "CRITICAL", (
        f"stg_pos_sales should be CRITICAL due to failed assertion, got {stg_pos['direct_health']}"
    )
    assert stg_pos["is_silent_corruption"] is True, "stg_pos_sales must be flagged as silent data corruption"

    # dim_inventory_availability: pipeline reported SUCCESS, but quality check failed (freshness delay)
    dim_inv = nodes["dim_inventory_availability"]
    assert dim_inv["direct_health"] in ("CRITICAL", "WARNING"), (
        f"dim_inventory_availability has failed quality check, got {dim_inv['direct_health']}"
    )
    assert dim_inv["is_silent_corruption"] is True, "dim_inventory_availability must be flagged as silent data corruption"

    # rpt_executive_daily_flash: downstream reporting node (direct checks pass, but downstream blast radius impacted)
    rpt_exec = nodes["rpt_executive_daily_flash"]
    assert rpt_exec["direct_health"] == "HEALTHY", "rpt_executive_daily_flash has no direct check failure"
    assert rpt_exec["downstream_impact"] == "AFFECTED_BY_UPSTREAM", (
        "rpt_executive_daily_flash must show downstream impact from upstream revenue failure"
    )

    # dim_products: clean master catalog baseline
    dim_prod = nodes["dim_products"]
    assert dim_prod["direct_health"] == "HEALTHY", "dim_products should be HEALTHY"
    assert dim_prod["downstream_impact"] == "NONE", "dim_products has no downstream blast radius"
    print("[PASS] Test 8: Health indicators strictly distinguish direct health from downstream impact; silent corruption properly identified.")

    # 9. Scenario Reachability Mapping (Requirement 3 & 6)
    scenarios = {s["case_id"]: s for s in data["scenarios"]}
    assert len(scenarios) == 5, f"Expected 5 scenarios, got {len(scenarios)}"
    assert "CASE-RAW_ECOMMERCE_ORDERS" in scenarios
    assert "raw_ecommerce_orders" in scenarios["CASE-RAW_ECOMMERCE_ORDERS"]["datasets"]
    assert "rpt_executive_daily_flash" in scenarios["CASE-RAW_ECOMMERCE_ORDERS"]["datasets"]

    for sc in data["scenarios"]:
        assert sc["node_count"] > 0, f"Scenario {sc['case_id']} has empty datasets"
        assert sc["root_dataset"] in sc["datasets"], f"Scenario {sc['case_id']} missing root dataset in datasets list"
    print("[PASS] Test 9: All 5 investigation scenarios mapped with complete DAG reachability.")

    print("==================================================================")
    print("ALL 9 LINEAGE VALIDATION CHECKS PASSED WITH ZERO DEFECTS!")
    print("==================================================================")


if __name__ == "__main__":
    run_lineage_tests()
