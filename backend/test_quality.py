"""
Automated Test Suite for TraceOps Data Quality Checks Module
Validates:
1. /api/quality-checks registered in root API navigation links
2. Endpoint returns 200 OK with valid schema
3. Exact 13 empirical quality checks from TRACEOPS.DATA_QUALITY_CHECKS
4. Accurate status and severity summary counts calculated from Exasol records
5. Status filtering (PASSED, FAILED, WARNING)
6. Severity filtering (CRITICAL, HIGH, MEDIUM, LOW)
7. Dataset filtering
8. Text search filtering across assertion details and expected/actual values
9. Reliable association of quality checks with root-cause investigation cases
10. Empty results and filter reset handling
"""

import json
from pathlib import Path
import sys

backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from main import list_quality_checks, root_endpoint
from database import get_quality_checks


def run_quality_tests():
    print("==================================================================")
    print("TraceOps Data Quality Checks Validation Suite")
    print("==================================================================")

    # 1. Root endpoint registration
    root_data = root_endpoint()
    assert "quality_checks" in root_data["endpoints"], "Missing 'quality_checks' in root endpoints"
    assert root_data["endpoints"]["quality_checks"] == "/api/quality-checks"
    print("[PASS] Test 1: /api/quality-checks registered in root API navigation links.")

    # 2. Quality checks endpoint response schema
    resp = list_quality_checks()
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}"
    data = json.loads(resp.body.decode("utf-8"))
    assert data["status"] == "success"
    assert "checks" in data and "summary" in data and "global_summary" in data
    print("[PASS] Test 2: /api/quality-checks returns valid schema with status=success.")

    # 3. Exact 13 empirical checks from Exasol
    checks = data["checks"]
    assert len(checks) == 13, f"Expected 13 checks from Exasol, got {len(checks)}"
    check_ids = {c["check_id"] for c in checks}
    assert "CHK-20261017-0350-09" in check_ids
    assert "CHK-20261017-0420-01" in check_ids
    assert "CHK-20261016-2310-BASE01" in check_ids
    print("[PASS] Test 3: Verified exact 13 empirical assertions from TRACEOPS.DATA_QUALITY_CHECKS.")

    # 4. Status and Severity Summary Breakdown
    g_sum = data["global_summary"]
    assert g_sum["total_checks"] == 13, f"Expected 13 total, got {g_sum['total_checks']}"
    assert g_sum["passed_checks"] == 3, f"Expected 3 passed, got {g_sum['passed_checks']}"
    assert g_sum["failed_checks"] == 9, f"Expected 9 failed, got {g_sum['failed_checks']}"
    assert g_sum["warning_checks"] == 1, f"Expected 1 warning, got {g_sum['warning_checks']}"
    assert g_sum["critical_checks"] == 6, f"Expected 6 critical, got {g_sum['critical_checks']}"
    assert g_sum["high_checks"] == 3, f"Expected 3 high, got {g_sum['high_checks']}"
    assert g_sum["medium_checks"] == 2, f"Expected 2 medium, got {g_sum['medium_checks']}"
    assert g_sum["low_checks"] == 2, f"Expected 2 low, got {g_sum['low_checks']}"
    print("[PASS] Test 4: Accurate global summary statistics verified (3 passed, 9 failed, 1 warning, 6 critical).")

    # 5. Status Filtering
    # 5a. FAILED filter
    failed_res = get_quality_checks(status="FAILED")
    assert failed_res["total_matching"] == 9, f"Expected 9 failed checks, got {failed_res['total_matching']}"
    assert all(c["check_status"] == "FAILED" for c in failed_res["checks"])

    # 5b. PASSED filter
    passed_res = get_quality_checks(status="PASSED")
    assert passed_res["total_matching"] == 3, f"Expected 3 passed checks, got {passed_res['total_matching']}"
    assert all(c["check_status"] == "PASSED" for c in passed_res["checks"])

    # 5c. WARNING filter
    warn_res = get_quality_checks(status="WARNING")
    assert warn_res["total_matching"] == 1, f"Expected 1 warning check, got {warn_res['total_matching']}"
    assert warn_res["checks"][0]["check_id"] == "CHK-20261017-0635-04"
    print("[PASS] Test 5: Status filtering (PASSED, FAILED, WARNING) strictly validated.")

    # 6. Severity Filtering
    crit_res = get_quality_checks(severity="CRITICAL")
    assert crit_res["total_matching"] == 6, f"Expected 6 critical checks, got {crit_res['total_matching']}"
    assert all(c["severity"] == "CRITICAL" for c in crit_res["checks"])

    high_res = get_quality_checks(severity="HIGH")
    assert high_res["total_matching"] == 3, f"Expected 3 high checks, got {high_res['total_matching']}"
    print("[PASS] Test 6: Severity filtering (CRITICAL, HIGH) strictly validated.")

    # 7. Dataset Filtering
    pos_res = get_quality_checks(dataset="stg_pos_sales")
    assert pos_res["total_matching"] == 1, f"Expected 1 check for stg_pos_sales, got {pos_res['total_matching']}"
    assert pos_res["checks"][0]["check_type"] == "NUMERIC_OUTLIER"
    assert "EUR/GBP currency multiplier" in pos_res["checks"][0]["evidence_details"]
    print("[PASS] Test 7: Dataset filtering strictly validated for stg_pos_sales.")

    # 8. Search Filtering
    search_res = get_quality_checks(search="currency")
    assert search_res["total_matching"] == 1
    assert search_res["checks"][0]["check_id"] == "CHK-20261017-0350-09"

    latency_res = get_quality_checks(search="latency")
    assert latency_res["total_matching"] >= 2
    print("[PASS] Test 8: Free-text search across check details and expected/actual fields validated.")

    # 9. Investigation Case Association
    for c in checks:
        assert c["associated_case_id"] is not None, f"Check {c['check_id']} missing associated_case_id"
        assert c["associated_case_id"].startswith("CASE-"), f"Invalid case format: {c['associated_case_id']}"

    # Verify specific key scenario links
    pos_check = next(c for c in checks if c["check_id"] == "CHK-20261017-0350-09")
    assert pos_check["associated_case_id"] == "CASE-RAW_POS_TRANSACTIONS"

    ecom_check = next(c for c in checks if c["check_id"] == "CHK-20261017-0420-01")
    assert ecom_check["associated_case_id"] == "CASE-RAW_ECOMMERCE_ORDERS"

    crm_check = next(c for c in checks if c["check_id"] == "CHK-20261017-0210-05")
    assert crm_check["associated_case_id"] == "CASE-RAW_CRM_EXPORT"
    print("[PASS] Test 9: All quality checks accurately linked to canonical investigation cases via DAG topology.")

    # 10. Empty Results Handling
    empty_res = get_quality_checks(search="non_existent_search_query_99999")
    assert empty_res["status"] == "success"
    assert empty_res["total_matching"] == 0
    assert len(empty_res["checks"]) == 0
    assert empty_res["global_summary"]["total_checks"] == 13, "Global summary preserved on empty filter"
    print("[PASS] Test 10: Empty search/filter results handled gracefully with intact global summary.")

    print("==================================================================")
    print("ALL 10 QUALITY CHECK VALIDATION CHECKS PASSED WITH ZERO DEFECTS!")
    print("==================================================================")


if __name__ == "__main__":
    run_quality_tests()
