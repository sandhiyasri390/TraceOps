-- ============================================================================
-- TraceOps: Evidence-First Data Incident Investigation
-- Exasol Database Schema Definition
-- Track 04: The Work Behind the Work (ExaThon India 2026)
-- ============================================================================

-- Ensure isolated schema for TraceOps to safeguard existing databases
CREATE SCHEMA IF NOT EXISTS TRACEOPS;
OPEN SCHEMA TRACEOPS;

-- ============================================================================
-- 1. PIPELINE_RUN_EVENTS
-- Records historical and real-time execution logs for data pipelines.
-- Captures start/end timestamps, operational status, rows processed, and error traces.
-- ============================================================================
CREATE OR REPLACE TABLE TRACEOPS.PIPELINE_RUN_EVENTS (
    RUN_ID                      VARCHAR(64)         NOT NULL,
    PIPELINE_NAME               VARCHAR(128)        NOT NULL,
    START_TIME                  TIMESTAMP           NOT NULL,
    END_TIME                    TIMESTAMP,
    STATUS                      VARCHAR(32)         NOT NULL,  -- 'SUCCESS', 'FAILED', 'WARNING', 'RUNNING'
    ROWS_PROCESSED              DECIMAL(18, 0)      DEFAULT 0,
    ERROR_CODE                  VARCHAR(64),
    ERROR_MESSAGE               VARCHAR(2000),
    EXECUTION_DURATION_SECONDS  DECIMAL(10, 2),
    CONSTRAINT PK_PIPELINE_RUN_EVENTS PRIMARY KEY (RUN_ID)
);

-- ============================================================================
-- 2. DATASET_DEPENDENCIES
-- Represents the Data Lineage Directed Acyclic Graph (DAG).
-- Connects upstream source/staging datasets to downstream marts and reports.
-- ============================================================================
CREATE OR REPLACE TABLE TRACEOPS.DATASET_DEPENDENCIES (
    DEPENDENCY_ID               VARCHAR(64)         NOT NULL,
    UPSTREAM_DATASET            VARCHAR(128)        NOT NULL,
    DOWNSTREAM_DATASET          VARCHAR(128)        NOT NULL,
    DEPENDENCY_TYPE             VARCHAR(64)         NOT NULL,  -- 'DIRECT_TRANSFORMATION', 'LOOKUP', 'AGGREGATION', 'REPLICATION', 'METRIC_INPUT'
    IS_CRITICAL                 BOOLEAN             NOT NULL,  -- TRUE if failure blocks SLA/KPI reporting
    CONSTRAINT PK_DATASET_DEPENDENCIES PRIMARY KEY (DEPENDENCY_ID)
);

-- ============================================================================
-- 3. DATA_QUALITY_CHECKS
-- Empirical observation log of automated tests and assertions.
-- Stores observed evidence separately from inferred root-cause hypotheses.
-- ============================================================================
CREATE OR REPLACE TABLE TRACEOPS.DATA_QUALITY_CHECKS (
    CHECK_ID                    VARCHAR(64)         NOT NULL,
    RUN_ID                      VARCHAR(64),                   -- Links to PIPELINE_RUN_EVENTS.RUN_ID (nullable for async assertions)
    DATASET_NAME                VARCHAR(128)        NOT NULL,
    CHECK_TYPE                  VARCHAR(64)         NOT NULL,  -- 'FRESHNESS_LATENCY', 'ROW_COUNT_DELTA', 'NULL_RATE', 'SCHEMA_DRIFT', 'NUMERIC_OUTLIER', 'DISTRIBUTION_ZSCORE'
    EXPECTED_VALUE              VARCHAR(256)        NOT NULL,
    ACTUAL_VALUE                VARCHAR(256)        NOT NULL,
    SEVERITY                    VARCHAR(32)         NOT NULL,  -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'
    CHECK_STATUS                VARCHAR(32)         NOT NULL,  -- 'PASSED', 'FAILED', 'WARNING'
    OBSERVED_AT                 TIMESTAMP           NOT NULL,
    EVIDENCE_DETAILS            VARCHAR(2000)       NOT NULL,
    CONSTRAINT PK_DATA_QUALITY_CHECKS PRIMARY KEY (CHECK_ID)
);

-- ============================================================================
-- 4. BUSINESS_KPI_SNAPSHOTS
-- Captures executive metrics, published reporting artifacts, and business impact.
-- Correlates data pipeline anomalies directly with business loss or executive alarms.
-- ============================================================================
CREATE OR REPLACE TABLE TRACEOPS.BUSINESS_KPI_SNAPSHOTS (
    SNAPSHOT_ID                 VARCHAR(64)         NOT NULL,
    KPI_NAME                    VARCHAR(128)        NOT NULL,  -- e.g. 'Gross Merchandise Value (GMV)', 'Stockout Risk'
    REPORT_NAME                 VARCHAR(128)        NOT NULL,  -- e.g. 'Executive Daily Flash', 'Supply Chain Radar'
    DATASET_NAME                VARCHAR(128)        NOT NULL,  -- Feeding dataset from dimensional tier
    SNAPSHOT_TIME               TIMESTAMP           NOT NULL,
    EXPECTED_VALUE              DECIMAL(18, 4)      NOT NULL,
    ACTUAL_VALUE                DECIMAL(18, 4)      NOT NULL,
    DEVIATION_PERCENT           DECIMAL(8, 2)       NOT NULL,  -- Relative % change ((actual - expected) / expected) * 100
    BUSINESS_IMPACT             VARCHAR(1000)       NOT NULL,
    CONSTRAINT PK_BUSINESS_KPI_SNAPSHOTS PRIMARY KEY (SNAPSHOT_ID)
);
