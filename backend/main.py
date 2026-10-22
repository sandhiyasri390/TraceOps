    {
        "case_id": "CASE-RAW_CUSTOMER_PROFILES",
        "title": "Customer Profile Data Freshness Breach",
        "flow_name": "Customer Profile Processing Flow",
        "root_dataset": "raw_customer_profiles",
        "severity": "HIGH",
        "status": "ACTIVE_INVESTIGATION",
        "first_observed_at": "2026-10-22T10:00:00+00:00",
        "last_observed_at": "2026-10-22T10:15:00+00:00",
        "silent_data_corruption": False,
        "affected_datasets": [
            "raw_customer_profiles",
            "stg_customer_profiles",
            "mart_customer_360"
        ],
        "downstream_reports": ["Customer 360 Dashboard"],
        "associated_kpis": [{
            "kpi_name": "Profile Data Freshness",
            "expected_value": 100,
            "actual_value": 68,
            "deviation_percent": -32,
            "business_impact": "Customer profiles may be outdated."
        }],
        "confirmed_evidence": [{
            "evidence_id": "DEMO-EV-004",
            "evidence_type": "DATA_QUALITY_ASSERTION",
            "component": "raw_customer_profiles",
            "check_status": "FAILED",
            "severity": "HIGH",
            "observed_at": "2026-10-22T10:15:00+00:00",
            "details": "DEMO: Customer profile freshness threshold was missed."
        }],
        "inferred_hypotheses": [{
            "hypothesis_id": "DEMO-HYP-003",
            "candidate_root_cause": "pipe_customer_profiles",
            "dataset_name": "raw_customer_profiles",
            "pipeline_name": "pipe_customer_profiles",
            "confidence_score": 0.79,
            "confidence_level": "MEDIUM",
            "is_confirmed": False,
            "rank": 1,
            "reasoning": "[DEMO HYPOTHESIS] A delayed upstream ingestion may explain stale profiles.",
            "score_breakdown": {
                "raw_score": 80,
                "max_raw_score": 100,
                "confidence_score": 0.79,
                "max_confidence_limit": 0.95,
                "scoring_details": ["DEMO: Freshness threshold missed"]
            }
        }],
        "top_candidate_root_cause": "pipe_customer_profiles",
        "top_confidence_score": 0.79,
        "recommended_recovery_actions": [
            "[Pipeline Audit] Check customer profile ingestion logs.",
            "[Validation] Compare source and target update timestamps."
        ],
        "data_mode": "demo"
    },
    {
        "case_id": "CASE-RAW_PAYMENT_EVENTS",
        "title": "Payment Event Ingestion Failure",
        "flow_name": "Payment Event Processing Flow",
        "root_dataset": "raw_payment_events",
        "severity": "CRITICAL",
        "status": "ACTIVE_INVESTIGATION",
        "first_observed_at": "2026-10-22T10:30:00+00:00",
        "last_observed_at": "2026-10-22T10:40:00+00:00",
        "silent_data_corruption": False,
        "affected_datasets": [
            "raw_payment_events",
            "stg_payment_events",
            "fct_payments"
        ],
        "downstream_reports": ["Payment Operations Dashboard"],
        "associated_kpis": [{
            "kpi_name": "Payment Event Volume",
            "expected_value": 10000,
            "actual_value": 6100,
            "deviation_percent": -39,
            "business_impact": "Payment reporting may be incomplete."
        }],
        "confirmed_evidence": [{
            "evidence_id": "DEMO-EV-005",
            "evidence_type": "PIPELINE_EXECUTION",
            "component": "pipe_raw_payment_events",
            "status": "FAILED",
            "severity": "CRITICAL",
            "observed_at": "2026-10-22T10:40:00+00:00",
            "details": "DEMO: Simulated payment event ingestion failure."
        }],
        "inferred_hypotheses": [{
            "hypothesis_id": "DEMO-HYP-004",
            "candidate_root_cause": "pipe_raw_payment_events",
            "dataset_name": "raw_payment_events",
            "pipeline_name": "pipe_raw_payment_events",
            "confidence_score": 0.86,
            "confidence_level": "HIGH",
            "is_confirmed": False,
            "rank": 1,
            "reasoning": "[DEMO HYPOTHESIS] An ingestion failure may explain the reduced payment event volume.",
            "score_breakdown": {
                "raw_score": 88,
                "max_raw_score": 100,
                "confidence_score": 0.86,
                "max_confidence_limit": 0.95,
                "scoring_details": ["DEMO: Simulated pipeline failure"]
            }
        }],
        "top_candidate_root_cause": "pipe_raw_payment_events",
        "top_confidence_score": 0.86,
        "recommended_recovery_actions": [
            "[Pipeline Audit] Inspect payment ingestion execution logs.",
            "[Reconciliation] Compare source event counts with target records."
        ],
        "data_mode": "demo"
    },
    {
        "case_id": "CASE-RAW_MARKETING_EVENTS",
        "title": "Duplicate Marketing Events Detected",
        "flow_name": "Marketing Event Processing Flow",
        "root_dataset": "raw_marketing_events",
        "severity": "MEDIUM",
        "status": "ACTIVE_INVESTIGATION",
        "first_observed_at": "2026-10-22T11:00:00+00:00",
        "last_observed_at": "2026-10-22T11:20:00+00:00",
        "silent_data_corruption": True,
        "affected_datasets": [
            "raw_marketing_events",
            "stg_marketing_events",
            "mart_campaign_performance"
        ],
        "downstream_reports": ["Campaign Performance Dashboard"],
        "associated_kpis": [{
            "kpi_name": "Unique Marketing Events",
            "expected_value": 50000,
            "actual_value": 63500,
            "deviation_percent": 27,
            "business_impact": "Campaign engagement metrics may be overstated."
        }],
        "confirmed_evidence": [{
            "evidence_id": "DEMO-EV-006",
            "evidence_type": "DATA_QUALITY_ASSERTION",
            "component": "stg_marketing_events",
            "check_status": "FAILED",
            "severity": "MEDIUM",
            "observed_at": "2026-10-22T11:20:00+00:00",
            "details": "DEMO: Duplicate event count exceeded the configured threshold."
        }],
        "inferred_hypotheses": [{
            "hypothesis_id": "DEMO-HYP-005",
            "candidate_root_cause": "pipe_marketing_events",
            "dataset_name": "raw_marketing_events",
            "pipeline_name": "pipe_marketing_events",
            "confidence_score": 0.74,
            "confidence_level": "MEDIUM",
            "is_confirmed": False,
            "rank": 1,
            "reasoning": "[DEMO HYPOTHESIS] Duplicate ingestion may explain inflated campaign metrics.",
            "score_breakdown": {
                "raw_score": 75,
                "max_raw_score": 100,
                "confidence_score": 0.74,
                "max_confidence_limit": 0.95,
                "scoring_details": ["DEMO: Duplicate event threshold exceeded"]
            }
        }],
        "top_candidate_root_cause": "pipe_marketing_events",
        "top_confidence_score": 0.74,
        "recommended_recovery_actions": [
            "[Deduplication Audit] Inspect event identifiers and ingestion retries.",
            "[Validation] Compare unique source events with transformed records."
        ],
        "data_mode": "demo"
    },
