import React, { useState, useMemo } from 'react';
import {
  Search,
  AlertTriangle,
  AlertOctagon,
  Info,
  Layers,
  Database,
  Clock,
  ArrowRight,
  Check,
  X,
  RefreshCw,
  EyeOff,
  Activity,
  FileText,
  SlidersHorizontal,
  ChevronRight,
  ShieldAlert
} from 'lucide-react';

export default function InvestigationsView({
  investigations = [],
  loading = false,
  error = null,
  onRetry,
  selectedCaseId,
  onSelectCase,
}) {
  const [filterSeverity, setFilterSeverity] = useState('ALL');
  const [filterSilentOnly, setFilterSilentOnly] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Filter cases based on user controls
  const filteredCases = useMemo(() => {
    return investigations.filter((c) => {
      if (filterSeverity !== 'ALL' && c.severity !== filterSeverity) {
        return false;
      }
      if (filterSilentOnly && !c.silent_data_corruption) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchId = c.case_id?.toLowerCase().includes(q);
        const matchTitle = c.title?.toLowerCase().includes(q);
        const matchDataset = c.root_dataset?.toLowerCase().includes(q);
        const matchFlow = c.flow_name?.toLowerCase().includes(q);
        if (!matchId && !matchTitle && !matchDataset && !matchFlow) {
          return false;
        }
      }
      return true;
    });
  }, [investigations, filterSeverity, filterSilentOnly, searchQuery]);

  // Determine currently active case
  const activeCase = useMemo(() => {
    if (!investigations || investigations.length === 0) return null;
    if (selectedCaseId) {
      const found = investigations.find((c) => c.case_id === selectedCaseId);
      if (found) return found;
    }
    return filteredCases[0] || investigations[0];
  }, [investigations, selectedCaseId, filteredCases]);

  if (loading && !investigations.length) {
    return (
      <div className="state-container">
        <div className="spinner"></div>
        <div className="state-title">Loading TraceOps Investigations...</div>
        <p className="state-subtitle">
          Querying Exasol pipeline execution runs, quality assertions, and KPI deviations across directed lineage DAGs.
        </p>
      </div>
    );
  }

  if (error && !investigations.length) {
    return (
      <div className="state-container error">
        <AlertTriangle size={32} strokeWidth={1.5} className="state-icon-alert" />
        <div className="state-title">Failed to Load Investigations</div>
        <p className="state-subtitle">{error}</p>
        {onRetry && (
          <button className="btn-retry" onClick={onRetry}>
            <RefreshCw size={14} strokeWidth={2} />
            <span>Retry Connection</span>
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="investigations-workbench">
      {/* Header Summary Bar */}
      <div className="investigations-header-row">
        <div>
          <h2 className="page-headline">Root-Cause Investigations Workbench</h2>
          <p className="page-description">
            Algorithmic incident synthesis ranking candidate root causes from DAG lineage precedence, assertion failures, and temporal observation logs.
          </p>
        </div>
        <div className="investigations-header-stats">
          <div className="badge-tag">
            Total Cases: <strong style={{ color: '#fff', marginLeft: '4px' }}>{investigations.length}</strong>
          </div>
          <div className="badge-tag highlight">
            Active Filter: <strong style={{ color: 'var(--cyan-primary)', marginLeft: '4px' }}>{filteredCases.length}</strong>
          </div>
        </div>
      </div>

      {/* Main 2-Pane Master-Detail Layout */}
      <div className="workbench-grid">
        {/* Pane 1: Left Case Selector */}
        <aside className="cases-selector-pane">
          {/* Search & Filter Toolbar */}
          <div className="selector-toolbar">
            <div className="search-box-wrapper">
              <Search size={14} strokeWidth={2} className="search-icon" />
              <input
                type="text"
                className="search-input"
                placeholder="Search case, dataset, title..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button className="clear-search" onClick={() => setSearchQuery('')} title="Clear search">
                  <X size={12} strokeWidth={2} />
                </button>
              )}
            </div>

            <div className="filter-chips-row">
              <button
                className={`chip-btn ${filterSeverity === 'ALL' ? 'active' : ''}`}
                onClick={() => setFilterSeverity('ALL')}
              >
                All ({investigations.length})
              </button>
              <button
                className={`chip-btn critical ${filterSeverity === 'CRITICAL' ? 'active' : ''}`}
                onClick={() => setFilterSeverity('CRITICAL')}
              >
                Critical
              </button>
              <button
                className={`chip-btn high ${filterSeverity === 'HIGH' ? 'active' : ''}`}
                onClick={() => setFilterSeverity('HIGH')}
              >
                High
              </button>
              <button
                className={`chip-btn silent ${filterSilentOnly ? 'active' : ''}`}
                onClick={() => setFilterSilentOnly(!filterSilentOnly)}
                title="Filter cases where pipeline reported SUCCESS but output corrupted data"
              >
                Silent Corruption
              </button>
            </div>
          </div>

          {/* Cases List */}
          <div className="cases-list-scroll">
            {filteredCases.length === 0 ? (
              <div className="empty-search-state">
                <Search size={24} strokeWidth={1.5} className="empty-icon" />
                <div style={{ fontWeight: 600, color: '#fff' }}>No cases match filters</div>
                <p style={{ fontSize: '12px', color: 'var(--text-sub)', margin: '6px 0 12px' }}>
                  Reset search query or severity filters to view active cases.
                </p>
                <button
                  className="btn-refresh"
                  style={{ fontSize: '11px', padding: '4px 8px', margin: '0 auto' }}
                  onClick={() => {
                    setFilterSeverity('ALL');
                    setFilterSilentOnly(false);
                    setSearchQuery('');
                  }}
                >
                  Reset Filters
                </button>
              </div>
            ) : (
              filteredCases.map((c) => {
                const isSelected = activeCase && activeCase.case_id === c.case_id;
                return (
                  <div
                    key={c.case_id}
                    className={`case-item-card ${isSelected ? 'selected' : ''}`}
                    onClick={() => onSelectCase && onSelectCase(c.case_id)}
                  >
                    <div className="case-item-header">
                      <span className="case-item-id">{c.case_id}</span>
                      <span className={`pill ${c.severity === 'CRITICAL' ? 'critical' : 'high'}`}>
                        {c.severity}
                      </span>
                    </div>

                    <div className="case-item-title">{c.title}</div>

                    <div className="case-item-flow-meta">
                      <span className="mono-font dataset-tag">
                        {c.root_dataset}
                      </span>
                      {c.silent_data_corruption && (
                        <span className="pill silent" title="Published with 0 exit code but invalid data">
                          Silent Corruption
                        </span>
                      )}
                    </div>

                    <div className="case-item-footer">
                      <span className="case-time-text">Observed {c.first_observed_at?.split(' ')[1] || '06:00'}</span>
                      <span className="case-hyp-count">
                        {c.inferred_hypotheses?.length || 0} suspects
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </aside>

        {/* Pane 2: Right Detail Pane */}
        <section className="case-detail-pane">
          {activeCase ? (
            <div className="detail-scroll-content">
              {/* Incident Hero Header */}
              <div className="incident-hero-box">
                <div className="hero-top-row">
                  <div className="hero-id-badges">
                    <span className="hero-case-id">{activeCase.case_id}</span>
                    <span className={`pill ${activeCase.severity === 'CRITICAL' ? 'critical' : 'high'}`}>
                      {activeCase.severity} SEVERITY
                    </span>
                    <span className="pill neutral">{activeCase.status}</span>
                    {activeCase.silent_data_corruption && (
                      <span className="pill silent">
                        <EyeOff size={12} strokeWidth={2} style={{ marginRight: '4px' }} />
                        SILENT DATA CORRUPTION
                      </span>
                    )}
                  </div>
                </div>

                <h1 className="hero-title">{activeCase.title}</h1>
                <div className="hero-flow-desc">
                  <strong>Causal Flow:</strong> {activeCase.flow_name}
                </div>

                <div className="hero-meta-grid">
                  <div className="meta-box">
                    <span className="meta-box-label">Root Dataset</span>
                    <span className="meta-box-value mono-font">{activeCase.root_dataset}</span>
                  </div>
                  <div className="meta-box">
                    <span className="meta-box-label">First Observed</span>
                    <span className="meta-box-value mono-font">{activeCase.first_observed_at || 'N/A'}</span>
                  </div>
                  <div className="meta-box">
                    <span className="meta-box-label">Last Observed</span>
                    <span className="meta-box-value mono-font">{activeCase.last_observed_at || 'N/A'}</span>
                  </div>
                  <div className="meta-box">
                    <span className="meta-box-label">Downstream Blast Radius</span>
                    <span className="meta-box-value">
                      {activeCase.downstream_reports?.join(', ') || 'N/A'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Hypothesis Notice Banner */}
              <div className="disclaimer-banner">
                <Info size={18} strokeWidth={2} className="disclaimer-icon-svg" />
                <div className="disclaimer-body">
                  <strong>Hypothesis Notice:</strong> Candidate root causes are algorithmically ranked based on topological DAG lineage precedence, temporal execution logs, assertion failures, and downstream impact. Algorithmic scores (max 100.0 raw points, normalized to a 0.95 confidence ceiling) represent relative evidentiary correlation, <em>not</em> proven causal certainty.
                </div>
              </div>

              {/* Section 1: Top Candidate Root Cause (Hypothesis #1) */}
              <div className="detail-section top-hypothesis-section">
                <div className="section-title-row">
                  <div className="section-badge hypothesis-badge">
                    <Activity size={14} strokeWidth={2} />
                    <span>Inferred Root-Cause Hypothesis #1 (Leading Candidate)</span>
                  </div>
                  <span className="unconfirmed-warning">[Unconfirmed Hypothesis — Requires Verification]</span>
                </div>

                {activeCase.inferred_hypotheses && activeCase.inferred_hypotheses.length > 0 ? (
                  (() => {
                    const topHyp = activeCase.inferred_hypotheses[0];
                    const sb = topHyp.score_breakdown || {};
                    const pct = Math.round((topHyp.confidence_score || 0) * 100);

                    const topScore = sb.topological_upstream_score ?? 0;
                    const maxTop = sb.max_topological_score ?? 35.0;

                    const tempScore = sb.temporal_priority_score ?? 0;
                    const maxTemp = sb.max_temporal_score ?? 25.0;

                    const failScore = sb.failure_evidence_score ?? 0;
                    const maxFail = sb.max_failure_evidence_score ?? 25.0;

                    const impactScore = sb.downstream_impact_score ?? 0;
                    const maxImpact = sb.max_downstream_impact_score ?? 15.0;

                    const rawTotal = sb.raw_total_score ?? (topScore + tempScore + failScore + impactScore);
                    const maxTotal = sb.max_total_score ?? 100.0;

                    return (
                      <div className="hypothesis-card featured">
                        <div className="hypothesis-card-top">
                          <div>
                            <div className="candidate-name mono-font">
                              {topHyp.candidate_root_cause}
                            </div>
                            <div className="candidate-sub">
                              Component: <strong>{topHyp.pipeline_name || topHyp.candidate_root_cause}</strong> | Target Dataset: <strong className="mono-font">{topHyp.dataset_name}</strong> | Run ID: <span className="mono-font">{topHyp.run_id || 'N/A'}</span>
                            </div>
                          </div>
                          <div className="confidence-score-block">
                            <div className="score-val-huge">{pct}%</div>
                            <div className="score-level-tag">{topHyp.confidence_level} CONFIDENCE</div>
                            <div className="score-cap-note">(Algorithmic Cap: 0.95)</div>
                          </div>
                        </div>

                        {/* Reasoning Callout */}
                        <div className="reasoning-box">
                          <div className="reasoning-label">Algorithmic Precedence & Lineage Rationale:</div>
                          <p className="reasoning-text">{topHyp.reasoning}</p>
                        </div>

                        {/* Mathematically Consistent Score Breakdown */}
                        <div className="score-breakdown-wrapper">
                          <div className="breakdown-header-row">
                            <span className="breakdown-title">Multi-Factor Weight Breakdown:</span>
                            <span className="breakdown-total-badge">
                              Raw Total: <strong>{rawTotal.toFixed(1)}</strong> / {maxTotal.toFixed(1)} pts
                            </span>
                          </div>

                          <div className="score-breakdown-grid">
                            <div className="breakdown-stat-box">
                              <span className="sb-label">Lineage Precedence</span>
                              <span className="sb-val">{topScore.toFixed(1)} <span className="sb-max">/ {maxTop} pts</span></span>
                              <span className="sb-sub">Topological DAG depth</span>
                            </div>
                            <div className="breakdown-stat-box">
                              <span className="sb-label">Temporal Priority</span>
                              <span className="sb-val">{tempScore.toFixed(1)} <span className="sb-max">/ {maxTemp} pts</span></span>
                              <span className="sb-sub">Earliest failure timestamp</span>
                            </div>
                            <div className="breakdown-stat-box">
                              <span className="sb-label">Failure Evidence</span>
                              <span className="sb-val">{failScore.toFixed(1)} <span className="sb-max">/ {maxFail} pts</span></span>
                              <span className="sb-sub">Assertion error severity</span>
                            </div>
                            <div className="breakdown-stat-box">
                              <span className="sb-label">Downstream Impact</span>
                              <span className="sb-val">{impactScore.toFixed(1)} <span className="sb-max">/ {maxImpact} pts</span></span>
                              <span className="sb-sub">KPI deviation severity</span>
                            </div>
                          </div>

                          {sb.scoring_details && sb.scoring_details.length > 0 && (
                            <ul className="scoring-details-list">
                              {sb.scoring_details.map((detail, idx) => (
                                <li key={idx}>
                                  <Check size={12} strokeWidth={2.5} className="detail-check-icon" />
                                  <span>{detail}</span>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      </div>
                    );
                  })()
                ) : (
                  <div className="empty-sub-card">No root-cause hypotheses generated for this incident case.</div>
                )}
              </div>

              {/* Section 2: Alternative Inferred Hypotheses (Rank 2+) */}
              {activeCase.inferred_hypotheses && activeCase.inferred_hypotheses.length > 1 && (
                <div className="detail-section">
                  <div className="section-title-row">
                    <h3 className="section-title">
                      Alternative Inferred Hypotheses ({activeCase.inferred_hypotheses.length - 1})
                    </h3>
                    <span className="section-subtitle-tag">Secondary Suspects in Lineage Path</span>
                  </div>

                  <div className="alt-hypotheses-list">
                    {activeCase.inferred_hypotheses.slice(1).map((hyp) => {
                      const altPct = Math.round((hyp.confidence_score || 0) * 100);
                      return (
                        <div key={hyp.hypothesis_id || hyp.candidate_root_cause} className="alt-hypothesis-card">
                          <div className="alt-hyp-header">
                            <div className="alt-hyp-left">
                              <span className="rank-badge">RANK #{hyp.rank}</span>
                              <span className="alt-name mono-font">{hyp.candidate_root_cause}</span>
                              <span className="alt-dataset mono-font">({hyp.dataset_name})</span>
                            </div>
                            <div className="alt-score-badge">
                              {altPct}% Score ({hyp.confidence_level})
                            </div>
                          </div>
                          <p className="alt-reasoning">{hyp.reasoning}</p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Section 3: Confirmed Empirical Evidence */}
              <div className="detail-section">
                <div className="section-title-row">
                  <div className="section-badge evidence-badge">
                    <Database size={14} strokeWidth={2} />
                    <span>Confirmed Empirical Evidence ({activeCase.confirmed_evidence?.length || 0} Records)</span>
                  </div>
                  <span className="confirmed-note">[Telemetry from Exasol Engine Tables]</span>
                </div>

                <div className="evidence-grid">
                  {activeCase.confirmed_evidence && activeCase.confirmed_evidence.length > 0 ? (
                    activeCase.confirmed_evidence.map((ev, idx) => {
                      let typeColor = 'neutral';
                      if (ev.evidence_type === 'PIPELINE_EXECUTION') typeColor = 'blue';
                      if (ev.evidence_type === 'DATA_QUALITY_ASSERTION') typeColor = 'amber';
                      if (ev.evidence_type === 'BUSINESS_KPI_DEVIATION') typeColor = 'critical';

                      return (
                        <div key={ev.evidence_id || idx} className="evidence-card">
                          <div className="evidence-card-header">
                            <span className={`evidence-type-badge ${typeColor}`}>
                              {ev.evidence_type}
                            </span>
                            <span className="evidence-time mono-font">{ev.observed_at}</span>
                          </div>

                          <div className="evidence-component-row">
                            <span className="mono-font evidence-comp-name">{ev.component}</span>
                            <span className={`pill ${ev.severity === 'CRITICAL' ? 'critical' : ev.severity === 'HIGH' ? 'high' : 'neutral'}`}>
                              {ev.severity || ev.status}
                            </span>
                          </div>

                          {ev.details && <p className="evidence-details-text">{ev.details}</p>}

                          <div className="evidence-footer-meta">
                            {ev.run_id && (
                              <span className="ev-meta-tag">Run: <strong className="mono-font">{ev.run_id}</strong></span>
                            )}
                            {ev.check_type && (
                              <span className="ev-meta-tag">Check: <strong className="mono-font">{ev.check_type}</strong></span>
                            )}
                            {ev.error_code && (
                              <span className="ev-meta-tag warning">Error: <strong className="mono-font">{ev.error_code}</strong></span>
                            )}
                            {ev.expected_value && (
                              <span className="ev-meta-tag">Expected: <span className="mono-font">{ev.expected_value}</span></span>
                            )}
                            {ev.actual_value && (
                              <span className="ev-meta-tag critical">Actual: <span className="mono-font">{ev.actual_value}</span></span>
                            )}
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="empty-sub-card">No empirical evidence records linked to this case.</div>
                  )}
                </div>
              </div>

              {/* Section 4: Downstream Business Impact & KPIs */}
              <div className="detail-section">
                <div className="section-title-row">
                  <h3 className="section-title">Downstream Business Impact & KPI Deviations</h3>
                  <span className="section-subtitle-tag">Executive Blast Radius</span>
                </div>

                {activeCase.associated_kpis && activeCase.associated_kpis.length > 0 ? (
                  <div className="kpi-cards-grid">
                    {activeCase.associated_kpis.map((kpi, idx) => {
                      const dev = kpi.deviation_percent;
                      const devSign = dev > 0 ? '+' : '';
                      const isNegativeDev = dev < 0;

                      return (
                        <div key={kpi.snapshot_id || idx} className="kpi-impact-card">
                          <div className="kpi-card-header">
                            <div>
                              <div className="kpi-name">{kpi.kpi_name}</div>
                              <div className="kpi-report-name">Report: <strong>{kpi.report_name}</strong></div>
                            </div>
                            <div className="kpi-dev-badge">
                              <span className={`kpi-dev-val ${isNegativeDev ? 'negative' : 'positive'}`}>
                                {devSign}{dev}%
                              </span>
                            </div>
                          </div>

                          <div className="kpi-values-row">
                            <div className="kpi-val-box">
                              <span className="kpi-v-lbl">Expected / Baseline</span>
                              <span className="kpi-v-num mono-font">{kpi.expected_value ?? kpi.baseline_value ?? 'N/A'}</span>
                            </div>
                            <div className="kpi-val-divider">
                              <ArrowRight size={14} strokeWidth={2} />
                            </div>
                            <div className="kpi-val-box">
                              <span className="kpi-v-lbl">Actual Observed</span>
                              <span className="kpi-v-num critical mono-font">{kpi.actual_value ?? 'N/A'}</span>
                            </div>
                          </div>

                          {kpi.business_impact && (
                            <div className="kpi-impact-desc">
                              <strong>Operational Impact:</strong> {kpi.business_impact}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="empty-sub-card">No downstream KPI deviations registered for this incident.</div>
                )}
              </div>

              {/* Section 5: Recommended Recovery Actions */}
              <div className="detail-section">
                <div className="section-title-row">
                  <h3 className="section-title">Recommended Remediation & Recovery Procedures</h3>
                  <span className="section-subtitle-tag">Advisory Operational Protocol</span>
                </div>

                <div className="governance-notice">
                  <ShieldAlert size={16} strokeWidth={2} />
                  <span>
                    <strong>Production Governance:</strong> Procedures are advisory recommendations. Production execution requires staging verification, formal change approval, and post-pipeline data reconciliation.
                  </span>
                </div>

                {activeCase.recommended_recovery_actions && activeCase.recommended_recovery_actions.length > 0 ? (
                  <div className="recovery-actions-list">
                    {activeCase.recommended_recovery_actions.map((action, idx) => (
                      <div key={idx} className="recovery-action-card">
                        <div className="action-step-num">{String(idx + 1).padStart(2, '0')}</div>
                        <div className="action-text">{action}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-sub-card">No recovery actions prescribed.</div>
                )}
              </div>
            </div>
          ) : (
            <div className="empty-workbench-state">
              <FileText size={40} strokeWidth={1.5} className="empty-icon" />
              <h3>Select an Investigation Case</h3>
              <p>Choose an incident from the left panel to review its evidence graph and root-cause ranking.</p>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
