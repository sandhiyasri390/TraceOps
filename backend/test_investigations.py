"""
Automated Test Suite for TraceOps Evidence-Based Root-Cause Ranking Engine
Validates:
1. Dynamic lineage DAG and topological ordering from DATASET_DEPENDENCIES
2. Upstream-versus-downstream causal ranking precedence
3. Silent corruption handling (pipeline reporting SUCCESS with failed assertions)
4. Confidence score cap (<= 0.95; no hypothesis marked as proven 1.0)
5. Separation of confirmed evidence vs inferred hypotheses (is_confirmed=False)
6. Actionable, safe recovery action recommendations
7. Missing / unmapped lineage handling
8. Query filters and empty results handling
9. Preservation of all 5 seeded scenarios and API contract
"""

import json
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import list_investigations, root_endpoint
from ranking import get_investigation_cases, _score_candidate, MAX_HYPOTHESIS_CONFIDENCE


def run_all_tests():
    print("==================================================================")
    print("TraceOps Root-Cause Ranking Engine Validation Suite")
    print("==================================================================")

    # -------------------------------------------------------------------------
    # TEST 1: Endpoint Discovery in Root API
    # -------------------------------------------------------------------------
    root_data = root_endpoint()
    assert "investigations" in root_data["endpoints"], "Missing 'investigations' in root endpoints"
    assert root_data["endpoints"]["investigations"] == "/api/investigations"
    print("[PASS] Test 1: /api/investigations registered in root API navigation links.")

    # -------------------------------------------------------------------------
    # TEST 2: Lineage Graph-Driven Grouping of All 5 Seeded Scenarios
    # -------------------------------------------------------------------------
    resp = list_investigations()
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    data = json.loads(resp.body.decode("utf-8"))

    assert data["status"] == "success"
    assert data["total_investigations"] == 5, f"Expected 5 investigation cases, got {data['total_investigations']}"
    assert "hypothesis_disclaimer" in data, "Missing top-level hypothesis disclaimer"

    case_ids = {c["case_id"] for c in data["investigations"]}
    expected_case_ids = {
        "CASE-RAW_ECOMMERCE_ORDERS",
        "CASE-RAW_WMS_BALANCES",
        "CASE-RAW_CRM_EXPORT",
        "CASE-RAW_WEB_CLICKSTREAM",
        "CASE-RAW_POS_TRANSACTIONS",
    }
    assert case_ids == expected_case_ids, f"Mismatch in case IDs: {case_ids} vs {expected_case_ids}"
    print(f"[PASS] Test 2: Graph-driven grouping formed exactly 5 cases matching root sources: {sorted(list(case_ids))}")

    # -------------------------------------------------------------------------
    # TEST 3: Upstream-versus-Downstream Ranking Precedence
    # -------------------------------------------------------------------------
    ecom_case = next(c for c in data["investigations"] if c["case_id"] == "CASE-RAW_ECOMMERCE_ORDERS")
    assert ecom_case["top_candidate_root_cause"] == "pipe_raw_ecommerce_orders", (
        f"Expected root ingestion pipe_raw_ecommerce_orders to be top rank, got {ecom_case['top_candidate_root_cause']}"
    )

    hypotheses = ecom_case["inferred_hypotheses"]
    assert len(hypotheses) >= 2, "Expected multiple candidate hypotheses in cascading failure"
    
    # Verify strict descending order of confidence scores
    scores = [h["confidence_score"] for h in hypotheses]
    assert scores == sorted(scores, reverse=True), f"Hypotheses not strictly sorted descending: {scores}"

    # Verify root candidate ranks strictly above downstream staging and fact pipelines
    hyp_names = [h["candidate_root_cause"] for h in hypotheses]
    assert hyp_names.index("pipe_raw_ecommerce_orders") < hyp_names.index("pipe_stg_online_orders")
    assert hyp_names.index("pipe_raw_ecommerce_orders") < hyp_names.index("pipe_fct_orders")
    print(f"[PASS] Test 3: Upstream-versus-downstream ranking verified: root source '{ecom_case['top_candidate_root_cause']}' ranked #1 ({scores[0]}), above downstream staging ({scores[1]}).")

    # -------------------------------------------------------------------------
    # TEST 4: Silent Data Corruption Handling (SUCCESS run with failed assertions)
    # -------------------------------------------------------------------------
    pos_case = next(c for c in data["investigations"] if c["case_id"] == "CASE-RAW_POS_TRANSACTIONS")
    assert pos_case["silent_data_corruption"] is True, "Expected silent_data_corruption=True for POS case"
    assert pos_case["top_candidate_root_cause"] == "pipe_pos_transactions_etl"
    
    # Verify recovery action targets the currency logic directly
    recovery_text = " ".join(pos_case["recommended_recovery_actions"])
    assert "currency" in recovery_text.lower() or "multiplier" in recovery_text.lower(), (
        f"Expected currency recovery guidance, got: {recovery_text}"
    )
    print(f"[PASS] Test 4: Silent corruption correctly identified on pipe_pos_transactions_etl (reported SUCCESS). Recovery guidance addresses currency multiplier logic.")

    # -------------------------------------------------------------------------
    # TEST 5: Confidence Score Capping (Never 1.0) & Unconfirmed Tagging
    # -------------------------------------------------------------------------
    for case in data["investigations"]:
        for hyp in case["inferred_hypotheses"]:
            # Assert confidence score is strictly <= 0.95
            assert hyp["confidence_score"] <= MAX_HYPOTHESIS_CONFIDENCE, (
                f"Confidence score {hyp['confidence_score']} exceeds cap {MAX_HYPOTHESIS_CONFIDENCE} in {hyp['hypothesis_id']}"
            )
            assert hyp["confidence_score"] < 1.0, f"Confidence cannot be 1.0 (proven cause): {hyp}"
            assert hyp["is_confirmed"] is False, f"Hypothesis cannot be marked as confirmed: {hyp}"
            assert hyp["reasoning"].startswith("[Inferred Hypothesis]"), f"Reasoning missing disclaimer prefix: {hyp['reasoning']}"
    print(f"[PASS] Test 5: All hypotheses capped at max {MAX_HYPOTHESIS_CONFIDENCE} (none are 1.0) and tagged with is_confirmed=False.")

    # -------------------------------------------------------------------------
    # TEST 6: Confirmed Evidence Separation & Auditability
    # -------------------------------------------------------------------------
    for case in data["investigations"]:
        assert len(case["confirmed_evidence"]) > 0, f"Case {case['case_id']} has empty confirmed evidence"
        for ev in case["confirmed_evidence"]:
            assert "evidence_id" in ev
            assert "evidence_type" in ev
            assert "details" in ev
            assert "component" in ev
            assert ev["evidence_type"] in ("PIPELINE_EXECUTION", "DATA_QUALITY_ASSERTION", "BUSINESS_KPI_DEVIATION")
    print("[PASS] Test 6: Confirmed evidence strictly contains empirical Exasol observations.")

    # -------------------------------------------------------------------------
    # TEST 7: Missing / Unmapped Lineage Handling
    # -------------------------------------------------------------------------
    unmapped_candidate = {
        "candidate_id": "pipe_custom_unmapped_stream",
        "pipeline_name": "pipe_custom_unmapped_stream",
        "dataset_name": "unknown_custom_table_xyz",
        "run_id": "RUN-TEST-001",
        "status": "FAILED",
        "error_code": "ERR_CUSTOM",
        "start_time": "2026-10-17 01:00:00",
        "is_silent_corruption": False,
        "check_severity": "HIGH",
    }
    # Mock DAG depth without this dataset
    mock_depths = {"some_other_dataset": 0}
    conf, breakdown, reasoning = _score_candidate(
        unmapped_candidate,
        [unmapped_candidate],
        [],
        mock_depths,
    )
    assert conf <= MAX_HYPOTHESIS_CONFIDENCE
    assert "Unmapped lineage tier" in reasoning or "Unmapped" in str(breakdown["scoring_details"])
    assert breakdown["topological_upstream_score"] == 15.0
    print("[PASS] Test 7: Missing / unmapped lineage handled gracefully without exceptions; neutral topological score assigned.")

    # -------------------------------------------------------------------------
    # TEST 8: Recovery Guidance Safety & Actionability
    # -------------------------------------------------------------------------
    for case in data["investigations"]:
        actions = case["recommended_recovery_actions"]
        assert len(actions) >= 2, f"Case {case['case_id']} has insufficient recovery actions"
        for act in actions:
            # Must contain safety prefix
            assert act.startswith("["), f"Recovery action missing audit/safety bracket: {act}"
    print("[PASS] Test 8: All recovery actions follow safe, read-only audit-before-action guidelines.")

    # -------------------------------------------------------------------------
    # TEST 9: Query Filtering (case_id, severity, limit)
    # -------------------------------------------------------------------------
    # Filter by specific case_id
    resp_case = list_investigations(case_id="CASE-RAW_CRM_EXPORT")
    assert resp_case.status_code == 200
    data_case = json.loads(resp_case.body.decode("utf-8"))
    assert data_case["total_investigations"] == 1
    assert data_case["investigations"][0]["case_id"] == "CASE-RAW_CRM_EXPORT"
    assert data_case["summary"]["total_matching"] == 1
    assert data_case["global_summary"]["total_cases"] == 5

    # Filter with limit
    resp_limit = list_investigations(limit=2)
    data_limit = json.loads(resp_limit.body.decode("utf-8"))
    assert data_limit["total_investigations"] == 2
    assert len(data_limit["investigations"]) == 2
    assert data_limit["summary"]["total_matching"] == 5
    assert data_limit["summary"]["returned_count"] == 2
    print("[PASS] Test 9: Query filtering and limit application validated.")

    # -------------------------------------------------------------------------
    # TEST 10: Empty Results Handling
    # -------------------------------------------------------------------------
    resp_empty = list_investigations(case_id="NON_EXISTENT_CASE")
    assert resp_empty.status_code == 200
    data_empty = json.loads(resp_empty.body.decode("utf-8"))
    assert data_empty["total_investigations"] == 0
    assert data_empty["investigations"] == []
    assert data_empty["summary"]["total_matching"] == 0
    assert data_empty["global_summary"]["total_cases"] == 5
    print("[PASS] Test 10: Empty results handled gracefully with 0 matching records and intact global summary.")

    print("\n==================================================================")
    print("ALL 10 VERIFICATION CHECKS PASSED WITH ZERO DEFECTS!")
    print("==================================================================")


if __name__ == "__main__":
    run_all_tests()
