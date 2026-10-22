import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  ShieldCheck,
  AlertOctagon,
  AlertTriangle,
  CheckCircle2,
  Search,
  Filter,
  RefreshCw,
  X,
  ChevronRight,
  Database,
  Calendar,
  ExternalLink,
  SlidersHorizontal,
} from 'lucide-react';
import { getQualityChecks } from '../services/api';

/**
 * QualityChecksView Component
 * Renders an enterprise-grade data quality assertions workbench.
 * Directly queries Exasol TRACEOPS.DATA_QUALITY_CHECKS to display empirical test results,
 * assertions telemetry, status/severity distributions, and links to investigation cases.
 */
export default function QualityChecksView({ onNavigateToCase }) {
  const [checksData, setChecksData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [datasetFilter, setDatasetFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCheckId, setSelectedCheckId] = useState(null);

  const fetchChecks = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getQualityChecks({
        status: statusFilter,
        severity: severityFilter,
        dataset: datasetFilter,
        search: searchQuery,
      });
      setChecksData(data);
      setLastRefreshed(new Date().toLocaleTimeString());
      if (data.checks && data.checks.length > 0 && !selectedCheckId) {
        setSelectedCheckId(data.checks[0].check_id);
      }
    } catch (err) {
      console.error('Failed to load quality checks:', err);
      setError(err.message || 'Failed to connect to Exasol Quality Engine');
    } finally {
      setLoading(false);
    }
  }, [statusFilter, severityFilter, datasetFilter, searchQuery, selectedCheckId]);

  useEffect(() => {
    fetchChecks();
  }, [fetchChecks]);

  const checks = checksData?.checks || [];
  const globalSummary = checksData?.global_summary || {
    total_checks: 0,
    passed_checks: 0,
    failed_checks: 0,
    warning_checks: 0,
    critical_checks: 0,
    high_checks: 0,
    medium_checks: 0,
    low_checks: 0,
  };

  // Derive unique dataset list from global checks if available
  const availableDatasets = useMemo(() => {
    if (!checksData?.checks) return [];
    const dsSet = new Set(checksData.checks.map((c) => c.dataset_name));
    return Array.from(dsSet).sort();
  }, [checksData]);

  const activeCheck = useMemo(() => {
    if (!checks.length) return null;
    return checks.find((c) => c.check_id === selectedCheckId) || checks[0];
  }, [checks, selectedCheckId]);

  const isFiltered =
    statusFilter !== 'ALL' ||
    severityFilter !== 'ALL' ||
    datasetFilter !== 'ALL' ||
    searchQuery.trim().length > 0;

  const resetFilters = () => {
    setStatusFilter('ALL');
    setSeverityFilter('ALL');
    setDatasetFilter('ALL');
    setSearchQuery('');
  };

  return (
    <div className="quality-page-shell">
      {/* 1. Header & Summary Stats */}
      <div className="page-header-row">
        <div>
          <h2 className="page-headline">Data Quality Assertions</h2>
          <p className="page-description">
            Empirical test observations from <code>TRACEOPS.DATA_QUALITY_CHECKS</code> in Exasol.
            Captures freshness latency, row volume deltas, schema drift, and numeric anomalies.
          </p>
        </div>

        <div className="header-actions-group">
          {lastRefreshed && (
            <span className="last-sync-tag">Updated {lastRefreshed}</span>
          )}
          <button
            className="btn-secondary"
            onClick={fetchChecks}
            disabled={loading}
            title="Refresh assertion records from Exasol"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            <span>{loading ? 'Refreshing...' : 'Refresh'}</span>
          </button>
        </div>
      </div>

      {/* 2. KPI Summary Metrics Cards */}
      <div className="metrics-grid">
        <div
          className={`metric-card total ${statusFilter === 'ALL' ? 'active-filter' : ''}`}
          onClick={() => setStatusFilter('ALL')}
          title="Filter to all assertions"
        >
          <div className="metric-header">
            <span className="metric-label">Total Assertions</span>
            <ShieldCheck size={16} className="metric-icon" />
          </div>
          <div className="metric-value-row">
            <span className="metric-value">{globalSummary.total_checks}</span>
            <span className="metric-badge neutral">Recorded Checks</span>
          </div>
          <div className="metric-sub-label">Across operational pipeline stages</div>
        </div>

        <div
          className={`metric-card critical ${statusFilter === 'FAILED' ? 'active-filter' : ''}`}
          onClick={() => setStatusFilter('FAILED')}
          title="Filter to failed assertions"
        >
          <div className="metric-header">
            <span className="metric-label">Failed Checks</span>
            <AlertOctagon size={16} className="metric-icon critical" />
          </div>
          <div className="metric-value-row">
            <span className="metric-value text-critical">{globalSummary.failed_checks}</span>
            <span className="metric-badge critical">Contract Failures</span>
          </div>
          <div className="metric-sub-label">{globalSummary.critical_checks} critical contract breaches</div>
        </div>

        <div
          className={`metric-card high ${statusFilter === 'WARNING' ? 'active-filter' : ''}`}
          onClick={() => setStatusFilter('WARNING')}
          title="Filter to warning assertions"
        >
          <div className="metric-header">
            <span className="metric-label">Warning Checks</span>
            <AlertTriangle size={16} className="metric-icon warning" />
          </div>
          <div className="metric-value-row">
            <span className="metric-value text-warning">{globalSummary.warning_checks}</span>
            <span className="metric-badge warning">Threshold Latency</span>
          </div>
          <div className="metric-sub-label">Freshness / reconciliation drift</div>
        </div>

        <div
          className={`metric-card healthy ${statusFilter === 'PASSED' ? 'active-filter' : ''}`}
          onClick={() => setStatusFilter('PASSED')}
          title="Filter to passed assertions"
        >
          <div className="metric-header">
            <span className="metric-label">Passed Checks</span>
            <CheckCircle2 size={16} className="metric-icon success" />
          </div>
          <div className="metric-value-row">
            <span className="metric-value text-healthy">{globalSummary.passed_checks}</span>
            <span className="metric-badge healthy">Verified Nominal</span>
          </div>
          <div className="metric-sub-label">Baseline assertions verified</div>
        </div>
      </div>

      {/* 3. Controls & Filter Bar */}
      <div className="filter-controls-card">
        <div className="filter-controls-left">
          {/* Search Box */}
          <div className="search-box-wrapper">
            <Search size={14} className="search-icon" />
            <input
              type="text"
              className="search-input"
              placeholder="Search check ID, dataset, evidence..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button
                className="clear-search-btn"
                onClick={() => setSearchQuery('')}
                aria-label="Clear search"
              >
                <X size={13} />
              </button>
            )}
          </div>

          {/* Status Tabs */}
          <div className="segmented-control">
            <button
              className={`segmented-btn ${statusFilter === 'ALL' ? 'active' : ''}`}
              onClick={() => setStatusFilter('ALL')}
            >
              All ({globalSummary.total_checks})
            </button>
            <button
              className={`segmented-btn ${statusFilter === 'FAILED' ? 'active' : ''}`}
              onClick={() => setStatusFilter('FAILED')}
            >
              Failed ({globalSummary.failed_checks})
            </button>
            <button
              className={`segmented-btn ${statusFilter === 'WARNING' ? 'active' : ''}`}
              onClick={() => setStatusFilter('WARNING')}
            >
              Warning ({globalSummary.warning_checks})
            </button>
            <button
              className={`segmented-btn ${statusFilter === 'PASSED' ? 'active' : ''}`}
              onClick={() => setStatusFilter('PASSED')}
            >
              Passed ({globalSummary.passed_checks})
            </button>
          </div>

          {/* Severity Dropdown */}
          <div className="dropdown-control-wrap">
            <SlidersHorizontal size={13} className="dropdown-icon" />
            <select
              className="select-input"
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              aria-label="Filter by severity"
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>

          {/* Dataset Dropdown */}
          {availableDatasets.length > 0 && (
            <div className="dropdown-control-wrap">
              <Database size={13} className="dropdown-icon" />
              <select
                className="select-input"
                value={datasetFilter}
                onChange={(e) => setDatasetFilter(e.target.value)}
                aria-label="Filter by dataset"
              >
                <option value="ALL">All Datasets ({availableDatasets.length})</option>
                {availableDatasets.map((ds) => (
                  <option key={ds} value={ds}>
                    {ds}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {isFiltered && (
          <button className="btn-ghost-clear" onClick={resetFilters}>
            <X size={13} />
            <span>Clear Filters</span>
          </button>
        )}
      </div>

      {/* 4. Error / Loading State */}
      {error && (
        <div className="state-container error">
          <AlertOctagon size={28} className="state-icon critical" />
          <div className="state-title">Failed to Query Exasol Quality Checks</div>
          <p className="state-subtitle">{error}</p>
          <button className="btn-secondary" onClick={fetchChecks}>
            <RefreshCw size={14} />
            <span>Retry Query</span>
          </button>
        </div>
      )}

      {loading && !checksData && !error && (
        <div className="state-container">
          <div className="spinner"></div>
          <div className="state-title">Loading Quality Checks...</div>
          <p className="state-subtitle">
            Fetching empirical assertions from <code>TRACEOPS.DATA_QUALITY_CHECKS</code>.
          </p>
        </div>
      )}

      {/* 5. Main Workbench: Table (Left) + Detail Panel (Right) */}
      {!error && (
        <div className="quality-workbench-layout">
          {/* Table Container */}
          <div className="table-card">
            {checks.length === 0 ? (
              <div className="empty-table-state">
                <Filter size={24} className="empty-icon" />
                <div className="empty-title">No Quality Assertions Match Filters</div>
                <p className="empty-desc">
                  No checks match the active combination of status, severity, dataset, and search terms.
                </p>
                {isFiltered && (
                  <button className="btn-secondary" onClick={resetFilters}>
                    Reset All Filters
                  </button>
                )}
              </div>
            ) : (
              <div className="table-responsive">
                <table className="enterprise-table">
                  <thead>
                    <tr>
                      <th>Check Identifier</th>
                      <th>Target Dataset</th>
                      <th>Status</th>
                      <th>Severity</th>
                      <th>Expected vs Actual</th>
                      <th>Observed Timestamp</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {checks.map((chk) => {
                      const isSelected = activeCheck?.check_id === chk.check_id;
                      const isFailed = chk.check_status === 'FAILED';
                      const isWarning = chk.check_status === 'WARNING';
                      const isPassed = chk.check_status === 'PASSED';

                      return (
                        <tr
                          key={chk.check_id}
                          className={`table-row ${isSelected ? 'row-selected' : ''}`}
                          onClick={() => setSelectedCheckId(chk.check_id)}
                        >
                          <td>
                            <div className="check-id-cell">
                              <span className="mono-font primary-text">{chk.check_type}</span>
                              <span className="mono-font sub-text">{chk.check_id}</span>
                            </div>
                          </td>
                          <td>
                            <div className="dataset-cell">
                              <span className="mono-font">{chk.dataset_name}</span>
                              {chk.run_id && (
                                <span className="mono-font run-tag">{chk.run_id}</span>
                              )}
                            </div>
                          </td>
                          <td>
                            <span
                              className={`status-pill ${
                                isFailed ? 'critical' : isWarning ? 'warning' : isPassed ? 'healthy' : 'neutral'
                              }`}
                            >
                              <span className="status-dot"></span>
                              <span>{chk.check_status}</span>
                            </span>
                          </td>
                          <td>
                            <span
                              className={`severity-pill ${
                                chk.severity === 'CRITICAL'
                                  ? 'critical'
                                  : chk.severity === 'HIGH'
                                  ? 'high'
                                  : chk.severity === 'MEDIUM'
                                  ? 'medium'
                                  : 'low'
                              }`}
                            >
                              {chk.severity}
                            </span>
                          </td>
                          <td>
                            <div className="comparison-cell">
                              <div className="comparison-line">
                                <span className="comp-lbl">Exp:</span>
                                <span className="mono-font comp-val">{chk.expected_value}</span>
                              </div>
                              <div className="comparison-line">
                                <span className="comp-lbl">Act:</span>
                                <span
                                  className={`mono-font comp-val ${
                                    isFailed ? 'text-critical' : isWarning ? 'text-warning' : 'text-healthy'
                                  }`}
                                >
                                  {chk.actual_value}
                                </span>
                              </div>
                            </div>
                          </td>
                          <td>
                            <span className="mono-font text-dim" style={{ fontSize: '11px' }}>
                              {chk.observed_at ? chk.observed_at.replace('.000000', '') : '—'}
                            </span>
                          </td>
                          <td>
                            <button
                              className="btn-icon-subtle"
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedCheckId(chk.check_id);
                              }}
                              title="Inspect assertion details"
                              aria-label={`Inspect check ${chk.check_id}`}
                            >
                              <ChevronRight size={14} />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Detail Side Panel */}
          <aside className="quality-detail-pane">
            {activeCheck ? (
              <div className="detail-pane-content">
                <div className="detail-pane-header">
                  <div className="header-meta-row">
                    <span className="mono-font check-id-tag">{activeCheck.check_id}</span>
                    <span
                      className={`status-pill ${
                        activeCheck.check_status === 'FAILED'
                          ? 'critical'
                          : activeCheck.check_status === 'WARNING'
                          ? 'warning'
                          : 'healthy'
                      }`}
                    >
                      <span className="status-dot"></span>
                      <span>{activeCheck.check_status}</span>
                    </span>
                  </div>

                  <h3 className="detail-check-type mono-font">{activeCheck.check_type}</h3>
                  <div className="detail-dataset-row">
                    <span className="meta-lbl">Target Dataset:</span>
                    <span className="mono-font meta-val">{activeCheck.dataset_name}</span>
                  </div>
                </div>

                {/* Evidence Details Box */}
                <div className="detail-section">
                  <div className="section-title-sm">Recorded Empirical Evidence</div>
                  <div className="evidence-callout-box">
                    <p className="evidence-text">{activeCheck.evidence_details}</p>
                  </div>
                </div>

                {/* Expected vs Actual Metric Comparison */}
                <div className="detail-section">
                  <div className="section-title-sm">Assertion Boundaries</div>
                  <div className="comparison-grid">
                    <div className="comp-box">
                      <span className="comp-box-lbl">Expected Contract</span>
                      <span className="mono-font comp-box-val">{activeCheck.expected_value}</span>
                    </div>
                    <div className="comp-box">
                      <span className="comp-box-lbl">Observed Value</span>
                      <span
                        className={`mono-font comp-box-val ${
                          activeCheck.check_status === 'FAILED'
                            ? 'text-critical'
                            : activeCheck.check_status === 'WARNING'
                            ? 'text-warning'
                            : 'text-healthy'
                        }`}
                      >
                        {activeCheck.actual_value}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Technical Telemetry Metadata */}
                <div className="detail-section">
                  <div className="section-title-sm">Execution Telemetry</div>
                  <div className="telemetry-meta-list">
                    <div className="telemetry-row">
                      <span className="t-lbl">Pipeline Run ID</span>
                      <span className="mono-font t-val">{activeCheck.run_id || 'Asynchronous Assertion'}</span>
                    </div>
                    <div className="telemetry-row">
                      <span className="t-lbl">Severity Level</span>
                      <span
                        className={`severity-pill ${
                          activeCheck.severity === 'CRITICAL'
                            ? 'critical'
                            : activeCheck.severity === 'HIGH'
                            ? 'high'
                            : 'medium'
                        }`}
                      >
                        {activeCheck.severity}
                      </span>
                    </div>
                    <div className="telemetry-row">
                      <span className="t-lbl">Observed Timestamp</span>
                      <span className="mono-font t-val">
                        {activeCheck.observed_at ? activeCheck.observed_at.replace('.000000', '') : '—'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Associated Investigation Case Link */}
                {activeCheck.associated_case_id && (
                  <div className="detail-section">
                    <div className="section-title-sm">Root-Cause Investigation Link</div>
                    <div className="case-link-box">
                      <div>
                        <div className="case-link-title">Correlated Incident Case</div>
                        <span className="mono-font case-link-id">{activeCheck.associated_case_id}</span>
                      </div>
                      {onNavigateToCase && (
                        <button
                          className="btn-secondary"
                          onClick={() => onNavigateToCase(activeCheck.associated_case_id)}
                          title="Open correlated case in Investigations Workbench"
                        >
                          <span>Investigate</span>
                          <ExternalLink size={13} />
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="empty-detail-state">
                <ShieldCheck size={28} className="empty-icon" />
                <div className="empty-title">Select an Assertion</div>
                <p className="empty-desc">
                  Click any assertion row to inspect detailed evidence, evaluation boundaries, and correlated investigation cases.
                </p>
              </div>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
