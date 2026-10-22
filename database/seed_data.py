"""
TraceOps: Synthetic Data Seeding Script
Populates Exasol database with realistic data incident scenarios for the
ExaThon India 2026 Exasol Open Build Challenge (Track 04).

Safety:
- Operates exclusively within schema TRACEOPS.
- Never modifies or drops system tables or unrelated schemas.
- Safe to rerun repeatedly (idempotent reset).
- Does not expose passwords, credentials, or personal data.
"""

from decimal import Decimal
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple

# Add backend directory to sys.path to reuse database connection logic
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from database import exasol_session  # noqa: E402

SCHEMA_NAME = "TRACEOPS"
TARGET_TABLES = [
    "PIPELINE_RUN_EVENTS",
    "DATASET_DEPENDENCIES",
    "DATA_QUALITY_CHECKS",
    "BUSINESS_KPI_SNAPSHOTS",
]

# -----------------------------------------------------------------------------
# 1. Dataset Dependencies (Lineage DAG)
# (DEPENDENCY_ID, UPSTREAM_DATASET, DOWNSTREAM_DATASET, DEPENDENCY_TYPE, IS_CRITICAL)
# -----------------------------------------------------------------------------
DEPENDENCIES_DATA: List[Tuple[str, str, str, str, bool]] = [
    # E-Commerce Order Flow (Scenario 1 & 4)
    ("DEP-001", "raw_ecommerce_orders", "stg_online_orders", "DIRECT_TRANSFORMATION", True),
    ("DEP-002", "stg_online_orders", "fct_orders", "DIRECT_TRANSFORMATION", True),
    ("DEP-003", "fct_orders", "fct_daily_sales", "AGGREGATION", True),
    ("DEP-004", "fct_daily_sales", "rpt_executive_daily_flash", "METRIC_INPUT", True),
    
    # POS In-Store Sales Flow (Scenario 5)
    ("DEP-005", "raw_pos_transactions", "stg_pos_sales", "DIRECT_TRANSFORMATION", True),
    ("DEP-006", "stg_pos_sales", "fct_orders", "DIRECT_TRANSFORMATION", True),
    ("DEP-007", "stg_pos_sales", "fct_daily_sales", "AGGREGATION", True),
    
    # Inventory & WMS Flow (Scenario 2)
    ("DEP-008", "raw_wms_balances", "stg_inventory_snapshots", "DIRECT_TRANSFORMATION", True),
    ("DEP-009", "stg_inventory_snapshots", "dim_inventory_availability", "DIRECT_TRANSFORMATION", True),
    ("DEP-010", "dim_inventory_availability", "rpt_supply_chain_stockout_radar", "METRIC_INPUT", True),
    
    # CRM Customer Profiles (Scenario 3)
    ("DEP-011", "raw_crm_export", "stg_customer_profiles", "DIRECT_TRANSFORMATION", False),
    ("DEP-012", "stg_customer_profiles", "dim_customers", "DIRECT_TRANSFORMATION", False),
    ("DEP-013", "dim_customers", "rpt_customer_growth_board", "METRIC_INPUT", False),
    ("DEP-014", "dim_customers", "fct_orders", "LOOKUP", False),
    
    # Web Clickstream & Conversion Funnel (Scenario 4)
    ("DEP-015", "raw_web_clickstream", "stg_clickstream_sessions", "DIRECT_TRANSFORMATION", True),
    ("DEP-016", "stg_clickstream_sessions", "fct_web_conversion", "AGGREGATION", True),
    ("DEP-017", "fct_web_conversion", "rpt_ecommerce_funnel_analytics", "METRIC_INPUT", True),
    
    # Store & Product Master Feeds (Baseline)
    ("DEP-018", "raw_product_master", "dim_products", "DIRECT_TRANSFORMATION", True),
    ("DEP-019", "dim_products", "fct_orders", "LOOKUP", True),
    ("DEP-020", "dim_products", "dim_inventory_availability", "LOOKUP", True),
]

# -----------------------------------------------------------------------------
# 2. Pipeline Run Events (Execution History)
# (RUN_ID, PIPELINE_NAME, START_TIME, END_TIME, STATUS, ROWS_PROCESSED, ERROR_CODE, ERROR_MESSAGE, EXECUTION_DURATION_SECONDS)
# -----------------------------------------------------------------------------
PIPELINE_RUNS_DATA: List[Tuple[str, str, str, str, str, int, Any, Any, float]] = [
    # --- Scenario 1: Upstream Source Ingestion Failure Cascade ---
    (
        "RUN-20261017-0415-ECOM01",
        "pipe_raw_ecommerce_orders",
        "2026-10-17 04:15:00",
        "2026-10-17 04:18:12",
        "FAILED",
        0,
        "ERR_DB_CONN_TIMEOUT",
        "Connection timed out after 180s to ecom-primary-db.us-east-1.rds:5432; socket closed by remote host",
        192.00,
    ),
    (
        "RUN-20261017-0430-STG01",
        "pipe_stg_online_orders",
        "2026-10-17 04:30:00",
        "2026-10-17 04:31:05",
        "FAILED",
        0,
        "ERR_UPSTREAM_MISSING",
        "Upstream dataset raw_ecommerce_orders partition 2026-10-17-04 not found or empty",
        65.00,
    ),
    (
        "RUN-20261017-0445-FCT01",
        "pipe_fct_orders",
        "2026-10-17 04:45:00",
        "2026-10-17 04:52:10",
        "WARNING",
        11200,
        "WARN_PARTIAL_PARTITIONS",
        "Staging partition stg_online_orders missing; processed only retail POS orders",
        430.00,
    ),
    (
        "RUN-20261017-0500-FCT02",
        "pipe_fct_daily_sales",
        "2026-10-17 05:00:00",
        "2026-10-17 05:08:45",
        "WARNING",
        11200,
        "WARN_INCOMPLETE_SOURCE",
        "Sales aggregation incomplete: e-commerce revenue partition not available",
        525.00,
    ),

    # --- Scenario 2: Freshness Delay / Lock Contention ---
    (
        "RUN-20261017-0330-INV01",
        "pipe_inventory_snapshot",
        "2026-10-17 03:30:00",
        "2026-10-17 07:15:45",
        "WARNING",
        85000,
        "WARN_LOCK_CONTENTION_DELAY",
        "Execution elapsed 13545s exceeding SLA threshold of 900s due to exclusive table lock on WMS_INVENTORY_BALANCES",
        13545.00,
    ),
    (
        "RUN-20261017-0720-INV02",
        "pipe_dim_inventory_availability",
        "2026-10-17 07:20:00",
        "2026-10-17 07:28:10",
        "SUCCESS",
        85000,
        None,
        "Completed refresh of dim_inventory_availability after upstream delay resolution",
        490.00,
    ),

    # --- Scenario 3: Schema Drift in CRM Feed ---
    (
        "RUN-20261017-0200-CRM01",
        "pipe_crm_customer_enrichment",
        "2026-10-17 02:00:00",
        "2026-10-17 02:08:30",
        "WARNING",
        120000,
        "WARN_SCHEMA_MISMATCH",
        "Field customer_postal_code not found in source payload; fallback default NULL assigned to 120000 records",
        510.00,
    ),
    (
        "RUN-20261017-0230-CRM02",
        "pipe_dim_customers",
        "2026-10-17 02:30:00",
        "2026-10-17 02:37:12",
        "WARNING",
        120000,
        "WARN_HIGH_NULL_RATE",
        "Postal code null rate exceeds 95% threshold in dim_customers",
        432.00,
    ),

    # --- Scenario 4: Row Count Drop in Web Clickstream ---
    (
        "RUN-20261017-0500-WEB01",
        "pipe_clickstream_sessionizer",
        "2026-10-17 05:00:00",
        "2026-10-17 05:14:22",
        "FAILED",
        24500,
        "ERR_ROW_VOLUME_ANOMALY",
        "Processed rows 24500 fell below safety threshold 120000 (-79.5% vs 7-day rolling median)",
        862.00,
    ),
    (
        "RUN-20261017-0530-WEB02",
        "pipe_fct_web_conversion",
        "2026-10-17 05:30:00",
        "2026-10-17 05:35:10",
        "WARNING",
        24500,
        "WARN_PARTIAL_SESSIONS",
        "Funnel analysis generated from incomplete mobile traffic slice",
        310.00,
    ),

    # --- Scenario 5: Silent Anomaly / Currency Multiplier Bug ---
    (
        "RUN-20261017-0300-POS01",
        "pipe_pos_transactions_etl",
        "2026-10-17 03:00:00",
        "2026-10-17 03:22:10",
        "SUCCESS",
        210000,
        "SUCCESS_SILENT_ANOMALY",
        "Execution completed with 0 runtime exceptions; 210000 records transformed into stg_pos_sales",
        1330.00,
    ),
    (
        "RUN-20261017-0345-POS02",
        "pipe_fct_daily_sales",
        "2026-10-17 03:45:00",
        "2026-10-17 03:55:40",
        "SUCCESS",
        210000,
        None,
        "Aggregated store level sales successfully",
        640.00,
    ),

    # --- Baseline Normal / Passing Runs ---
    (
        "RUN-20261016-2300-BASE01",
        "pipe_raw_ecommerce_orders",
        "2026-10-16 23:00:00",
        "2026-10-16 23:08:15",
        "SUCCESS",
        58420,
        None,
        "Hourly batch ingestion completed successfully",
        495.00,
    ),
    (
        "RUN-20261016-2330-BASE02",
        "pipe_pos_transactions_etl",
        "2026-10-16 23:30:00",
        "2026-10-16 23:48:20",
        "SUCCESS",
        198500,
        None,
        "POS daily reconciliation completed cleanly",
        1100.00,
    ),
    (
        "RUN-20261017-0100-BASE03",
        "pipe_product_catalog_sync",
        "2026-10-17 01:00:00",
        "2026-10-17 01:04:10",
        "SUCCESS",
        14200,
        None,
        "Product master catalog sync completed",
        250.00,
    ),
    (
        "RUN-20261017-0130-BASE04",
        "pipe_loyalty_rewards_sync",
        "2026-10-17 01:30:00",
        "2026-10-17 01:36:50",
        "SUCCESS",
        64200,
        None,
        "Customer loyalty tiers and reward balances reconciled",
        410.00,
    ),
]

# -----------------------------------------------------------------------------
# 3. Data Quality Checks (Evidence Log)
# (CHECK_ID, RUN_ID, DATASET_NAME, CHECK_TYPE, EXPECTED_VALUE, ACTUAL_VALUE, SEVERITY, CHECK_STATUS, OBSERVED_AT, EVIDENCE_DETAILS)
# -----------------------------------------------------------------------------
QUALITY_CHECKS_DATA: List[Tuple[str, Any, str, str, str, str, str, str, str, str]] = [
    # Scenario 1 Evidence
    (
        "CHK-20261017-0420-01",
        "RUN-20261017-0415-ECOM01",
        "raw_ecommerce_orders",
        "FRESHNESS_LATENCY",
        "< 30m",
        "185m",
        "CRITICAL",
        "FAILED",
        "2026-10-17 04:20:00",
        "Latest batch timestamp is 2026-10-17 01:00:00 UTC; ingestion threshold exceeded by 155 minutes",
    ),
    (
        "CHK-20261017-0446-02",
        "RUN-20261017-0445-FCT01",
        "fct_orders",
        "ROW_COUNT_DELTA",
        "> 45000 rows",
        "11200 rows",
        "HIGH",
        "FAILED",
        "2026-10-17 04:46:15",
        "E-commerce partition missing; only POS retail orders were ingested (-75.1% row drop)",
    ),

    # Scenario 2 Evidence
    (
        "CHK-20261017-0630-03",
        "RUN-20261017-0330-INV01",
        "dim_inventory_availability",
        "FRESHNESS_LATENCY",
        "< 60m",
        "245m",
        "HIGH",
        "FAILED",
        "2026-10-17 06:30:00",
        "Snapshot timestamp 2026-10-16 23:00:00 is 245 minutes behind scheduled publication window",
    ),
    (
        "CHK-20261017-0635-04",
        "RUN-20261017-0330-INV01",
        "dim_inventory_availability",
        "RECONCILIATION_GAP",
        "0 unresolved",
        "142 unconfirmed SKUs",
        "MEDIUM",
        "WARNING",
        "2026-10-17 06:35:00",
        "In-flight replenishment transfers between distribution centers pending WMS lock release",
    ),

    # Scenario 3 Evidence
    (
        "CHK-20261017-0210-05",
        "RUN-20261017-0200-CRM01",
        "stg_customer_profiles",
        "SCHEMA_DRIFT",
        "column [customer_postal_code] exists",
        "column [postal_code_v2] detected",
        "CRITICAL",
        "FAILED",
        "2026-10-17 02:10:00",
        "Source payload schema altered in release crm-v4.12.0; unmapped attribute postal_code_v2",
    ),
    (
        "CHK-20261017-0212-06",
        "RUN-20261017-0200-CRM01",
        "dim_customers",
        "NULL_RATE",
        "< 1.0%",
        "99.8%",
        "CRITICAL",
        "FAILED",
        "2026-10-17 02:12:30",
        "Column customer_postal_code has 119760 null values out of 120000 active records",
    ),

    # Scenario 4 Evidence
    (
        "CHK-20261017-0515-07",
        "RUN-20261017-0500-WEB01",
        "stg_clickstream_sessions",
        "ROW_COUNT_DELTA",
        ">= 135000 rows",
        "24500 rows",
        "CRITICAL",
        "FAILED",
        "2026-10-17 05:15:00",
        "Mobile browser traffic (iOS Safari & Android Chrome) dropped from 110,000 sessions to 0 sessions",
    ),
    (
        "CHK-20261017-0518-08",
        "RUN-20261017-0530-WEB02",
        "fct_web_conversion",
        "FUNNEL_DROP_ANOMALY",
        "Mobile checkouts > 15000",
        "12 checkouts",
        "HIGH",
        "FAILED",
        "2026-10-17 05:18:00",
        "Mobile sessions excluded upstream before checkout funnel attribution step",
    ),

    # Scenario 5 Evidence
    (
        "CHK-20261017-0350-09",
        "RUN-20261017-0300-POS01",
        "stg_pos_sales",
        "NUMERIC_OUTLIER",
        "MAX(unit_price_usd) <= 2500.00",
        "248500.00",
        "CRITICAL",
        "FAILED",
        "2026-10-17 03:50:00",
        "5,420 rows exhibit unit_price > $10,000; EUR/GBP currency multiplier applied 100x instead of 1.08x",
    ),
    (
        "CHK-20261017-0355-10",
        "RUN-20261017-0345-POS02",
        "fct_daily_sales",
        "DISTRIBUTION_ZSCORE",
        "Z-score within [-3.0, +3.0]",
        "Z-score = +14.8",
        "CRITICAL",
        "FAILED",
        "2026-10-17 03:55:00",
        "Daily store sales mean skewed from baseline $45.20 to $489.10 per basket",
    ),

    # Baseline Passing Checks
    (
        "CHK-20261016-2310-BASE01",
        "RUN-20261016-2300-BASE01",
        "raw_ecommerce_orders",
        "FRESHNESS_LATENCY",
        "< 30m",
        "8m",
        "LOW",
        "PASSED",
        "2026-10-16 23:10:00",
        "Hourly batch ingestion within expected freshness threshold",
    ),
    (
        "CHK-20261016-2312-BASE02",
        "RUN-20261016-2300-BASE01",
        "raw_ecommerce_orders",
        "NULL_RATE",
        "< 0.1%",
        "0.0%",
        "LOW",
        "PASSED",
        "2026-10-16 23:12:00",
        "Primary order_id and customer_id have 0 null values",
    ),
    (
        "CHK-20261017-0105-BASE03",
        "RUN-20261017-0100-BASE03",
        "dim_products",
        "UNIQUENESS",
        "0 duplicate SKUs",
        "0 duplicate SKUs",
        "MEDIUM",
        "PASSED",
        "2026-10-17 01:05:00",
        "SKU primary key uniqueness 100% verified across 14,200 product entities",
    ),
]

# -----------------------------------------------------------------------------
# 4. Business KPI Snapshots (Impact Observation)
# (SNAPSHOT_ID, KPI_NAME, REPORT_NAME, DATASET_NAME, SNAPSHOT_TIME, EXPECTED_VALUE, ACTUAL_VALUE, DEVIATION_PERCENT, BUSINESS_IMPACT)
# -----------------------------------------------------------------------------
KPI_SNAPSHOTS_DATA: List[Tuple[str, str, str, str, str, float, float, float, str]] = [
    # Scenario 1 Impact
    (
        "SNAP-20261017-0600-01",
        "Gross Merchandise Value (GMV)",
        "Executive Daily Flash",
        "fct_daily_sales",
        "2026-10-17 06:00:00",
        420000.00,
        165000.00,
        -60.71,
        "Executive Daily Flash reports $255k GMV shortfall due to missing e-commerce online orders stream.",
    ),

    # Scenario 2 Impact
    (
        "SNAP-20261017-0700-02",
        "Inventory Stockout Risk Rate",
        "Supply Chain & Stockout Radar",
        "dim_inventory_availability",
        "2026-10-17 07:00:00",
        2.10,
        8.95,
        326.19,
        "Supply Chain Operations falsely alarmed on 34 top-selling SKUs flagged out-of-stock due to un-refreshed warehouse receipts.",
    ),

    # Scenario 3 Impact
    (
        "SNAP-20261017-0630-03",
        "Regional Customer Density Index",
        "Customer Growth & Retention Board",
        "dim_customers",
        "2026-10-17 06:30:00",
        94.50,
        0.20,
        -99.79,
        "Marketing regional geo-targeting campaigns suspended; 4 geographic segmentation cohorts collapsed to zero volume.",
    ),

    # Scenario 4 Impact
    (
        "SNAP-20261017-0600-04",
        "Checkout Conversion Rate",
        "E-Commerce Funnel Analytics",
        "fct_web_conversion",
        "2026-10-17 06:00:00",
        3.45,
        0.62,
        -82.03,
        "E-Commerce team received false critical alert indicating mobile checkout outage; conversion rate cratered -82%.",
    ),

    # Scenario 5 Impact
    (
        "SNAP-20261017-0600-05",
        "Average Order Value (AOV)",
        "Executive Daily Flash",
        "fct_daily_sales",
        "2026-10-17 06:00:00",
        68.50,
        412.30,
        501.90,
        "Executive Flash Report showed artificial 500% surge in AOV; finance alerted on multi-million dollar revenue overstatement.",
    ),

    # Baseline Healthy KPIs
    (
        "SNAP-20261016-2300-BASE01",
        "Daily Active Customers",
        "Customer Growth & Retention Board",
        "dim_customers",
        "2026-10-16 23:00:00",
        88400.00,
        89150.00,
        0.85,
        "Customer activity tracking on target; retention cohort metrics stable.",
    ),
    (
        "SNAP-20261016-2300-BASE02",
        "Order Fulfillment SLA Rate",
        "Supply Chain & Stockout Radar",
        "dim_inventory_availability",
        "2026-10-16 23:00:00",
        98.50,
        98.70,
        0.20,
        "Distribution center order dispatch SLA met with 0 backlog.",
    ),
]


def reset_schema(conn) -> None:
    """
    Ensure TRACEOPS schema exists and clean/reset only the four TraceOps tables.
    Never alters system tables or other user schemas.
    """
    print(f"[*] Ensuring schema {SCHEMA_NAME} exists...")
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA_NAME}")
    conn.execute(f"OPEN SCHEMA {SCHEMA_NAME}")

    print(f"[*] Re-creating TraceOps tables from schema.sql in {SCHEMA_NAME}...")
    schema_sql_path = Path(__file__).resolve().parent / "schema.sql"
    if schema_sql_path.exists():
        sql_content = schema_sql_path.read_text(encoding="utf-8")
        statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]
        for stmt in statements:
            conn.execute(stmt)
    else:
        for table in TARGET_TABLES:
            conn.execute(f"CREATE OR REPLACE TABLE {SCHEMA_NAME}.{table}")


def run_seed() -> Dict[str, int]:
    """
    Main seed function. Connects to Exasol, resets TraceOps tables, inserts data,
    and returns a mapping of table names to row counts.
    """
    print("==================================================================")
    print("TraceOps Database Seeder: Exasol Open Build Challenge")
    print("==================================================================")

    counts: Dict[str, int] = {}
    with exasol_session() as conn:
        reset_schema(conn)

        print("[*] Populating deterministic synthetic incident data...")
        
        print("  -> Importing DATASET_DEPENDENCIES...")
        conn.import_from_iterable(DEPENDENCIES_DATA, (SCHEMA_NAME, "DATASET_DEPENDENCIES"))
        counts["DATASET_DEPENDENCIES"] = len(DEPENDENCIES_DATA)

        print("  -> Importing PIPELINE_RUN_EVENTS...")
        conn.import_from_iterable(PIPELINE_RUNS_DATA, (SCHEMA_NAME, "PIPELINE_RUN_EVENTS"))
        counts["PIPELINE_RUN_EVENTS"] = len(PIPELINE_RUNS_DATA)

        print("  -> Importing DATA_QUALITY_CHECKS...")
        conn.import_from_iterable(QUALITY_CHECKS_DATA, (SCHEMA_NAME, "DATA_QUALITY_CHECKS"))
        counts["DATA_QUALITY_CHECKS"] = len(QUALITY_CHECKS_DATA)

        print("  -> Importing BUSINESS_KPI_SNAPSHOTS...")
        conn.import_from_iterable(KPI_SNAPSHOTS_DATA, (SCHEMA_NAME, "BUSINESS_KPI_SNAPSHOTS"))
        counts["BUSINESS_KPI_SNAPSHOTS"] = len(KPI_SNAPSHOTS_DATA)

        print("\n[+] Verification of Seeded Row Counts in Exasol:")
        for table in TARGET_TABLES:
            res = conn.execute(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.{table}").fetchall()
            row_count = res[0][0] if res else 0
            print(f"    - {SCHEMA_NAME}.{table}: {row_count} rows")

        # Foreign-key integrity check between DATA_QUALITY_CHECKS.RUN_ID and PIPELINE_RUN_EVENTS.RUN_ID
        orphan_check = conn.execute(f"""
            SELECT COUNT(*)
            FROM {SCHEMA_NAME}.DATA_QUALITY_CHECKS c
            LEFT JOIN {SCHEMA_NAME}.PIPELINE_RUN_EVENTS r
              ON c.RUN_ID = r.RUN_ID
            WHERE c.RUN_ID IS NOT NULL AND r.RUN_ID IS NULL
        """).fetchall()
        orphan_count = orphan_check[0][0] if orphan_check else 0
        if orphan_count == 0:
            print("[+] Referential consistency check: 0 orphan check-to-run links.")
        else:
            print(f"[!] Warning: {orphan_count} orphan check-to-run links detected!")

        print("\n[+] Seeding completed successfully.")
        print("==================================================================")

    return counts


if __name__ == "__main__":
    try:
        run_seed()
    except Exception as exc:
        print(f"\n[!] Seed error: {exc}", file=sys.stderr)
        sys.exit(1)
