import React, { useState, useEffect, useCallback } from 'react';
import { getInvestigations, getExasolHealth } from './services/api';
import InvestigationsView from './components/InvestigationsView';
import LineageView from './components/LineageView';
import QualityChecksView from './components/QualityChecksView';
import {
  LayoutDashboard,
  FileSearch,
  GitFork,
  ShieldCheck,
  Activity,
  FolderKanban,
  AlertOctagon,
  AlertTriangle,
  EyeOff,
  RefreshCw,
  Server,
  ArrowRight,
  Layers,
  Database
} from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [investigations, setInvestigations] = useState([]);
  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);
  const [exasolHealth, setExasolHealth] = useState({
    status: 'checking',
    host: '127.0.0.1:8563',
    latency_ms: null,
    schema: 'TRACEOPS'
  });

  const checkConnection = useCallback(async () => {
    try {
      const health = await getExasolHealth();
      setExasolHealth(health);
    } catch {
      setExasolHealth({
        status: 'error',
        host: '127.0.0.1:8563',
        latency_ms: null,
        schema: 'TRACEOPS'
      });
    }
  }, []);

  const fetchInvestigationsData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [invData] = await Promise.all([
        getInvestigations(),
        checkConnection()
      ]);
      const cases = invData.investigations || [];
      setInvestigations(cases);
      setSummary(invData.summary || null);
      setLastRefreshed(new Date().toLocaleTimeString());
      if (cases.length > 0 && !selectedCaseId) {
        setSelectedCaseId(cases[0].case_id);
      }
    } catch (err) {
      console.error('Failed to load investigation data:', err);
      setError(err.message || 'Failed to connect to backend investigation engine');
    } finally {
      setLoading(false);
    }
  }, [selectedCaseId, checkConnection]);

  useEffect(() => {
    fetchInvestigationsData();
  }, [fetchInvestigationsData]);

  // Derive metrics strictly from actual API fields
  const totalCount = summary?.total_matching ?? investigations.length;
  const criticalCount = summary?.critical_cases ?? investigations.filter((c) => c.severity === 'CRITICAL').length;
  const highCount = summary?.high_cases ?? investigations.filter((c) => c.severity === 'HIGH').length;
  const silentCount = summary?.silent_corruption_cases ?? investigations.filter((c) => c.silent_data_corruption).length;
  const totalEvidence = summary?.total_confirmed_evidence_items ?? 0;

  return (
    <div className="dashboard-shell">
      {/* 1. Sidebar Navigation */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="brand-badge">
            <div className="brand-icon">
              <Activity size={20} strokeWidth={2.2} />
            </div>
            <div>
              <div className="brand-title">TraceOps</div>
              <div className="brand-tagline">Data Observability</div>
            </div>
          </div>
        </div>

        <nav className="sidebar-nav">
          <button
            className={`nav-item ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <div className="nav-item-left">
              <LayoutDashboard size={16} strokeWidth={1.8} className="nav-icon" />
              <span>Overview</span>
            </div>
            <span className="nav-pill">System</span>
          </button>

          <button
            className={`nav-item ${activeTab === 'investigations' ? 'active' : ''}`}
            onClick={() => setActiveTab('investigations')}
          >
            <div className="nav-item-left">
              <FileSearch size={16} strokeWidth={1.8} className="nav-icon" />
              <span>Investigations</span>
            </div>
            <span className="nav-pill">
              {loading && !investigations.length ? '...' : `${investigations.length} cases`}
            </span>
          </button>

          <button
            className={`nav-item ${activeTab === 'lineage' ? 'active' : ''}`}
            onClick={() => setActiveTab('lineage')}
          >
            <div className="nav-item-left">
              <GitFork size={16} strokeWidth={1.8} className="nav-icon" />
              <span>Data Lineage</span>
            </div>
            <span className="nav-pill">DAG</span>
          </button>

          <button
            className={`nav-item ${activeTab === 'quality' ? 'active' : ''}`}
            onClick={() => setActiveTab('quality')}
          >
            <div className="nav-item-left">
              <ShieldCheck size={16} strokeWidth={1.8} className="nav-icon" />
              <span>Quality Checks</span>
            </div>
            <span className="nav-pill">Assertions</span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="engine-status">
            <span className={`status-dot ${exasolHealth.status === 'healthy' ? 'healthy' : exasolHealth.status === 'error' ? 'error' : 'warning'}`}></span>
            <span className="engine-text">
              Exasol {exasolHealth.host}
              {exasolHealth.latency_ms !== null && ` (${exasolHealth.latency_ms}ms)`}
            </span>
          </div>
          <div className="sidebar-version-tag">TraceOps v0.1.0 • Enterprise Core</div>
        </div>
      </aside>

      {/* 2. Main Content Wrapper */}
      <div className="main-wrapper">
        {/* Top Header */}
        <header className="top-header">
          <div className="header-brand-title">
            <h1 className="header-title">TraceOps</h1>
            <p className="header-subtitle">Evidence-first data incident investigation</p>
          </div>

          <div className="header-actions">
            {lastRefreshed && (
              <button
                className="btn-refresh"
                onClick={fetchInvestigationsData}
                disabled={loading}
                title="Sync latest incident evidence from Exasol backend"
              >
                <RefreshCw size={13} strokeWidth={2} className={loading ? 'spinning' : ''} />
                <span>{loading ? 'Syncing...' : `Refreshed ${lastRefreshed}`}</span>
              </button>
            )}
            <div className={`badge-tag connection ${exasolHealth.status === 'healthy' ? 'highlight' : exasolHealth.status === 'error' ? 'error' : ''}`}>
              <span className={`connection-dot ${exasolHealth.status === 'healthy' ? 'active' : ''}`}></span>
              <span>
                {exasolHealth.status === 'healthy'
                  ? `Exasol Live (${exasolHealth.latency_ms ?? 0}ms)`
                  : exasolHealth.status === 'error'
                  ? 'Exasol Disconnected'
                  : 'Exasol Checking...'}
              </span>
            </div>
            <div className="badge-tag schema-tag">
              <Database size={12} strokeWidth={1.8} />
              <span>TRACEOPS</span>
            </div>
          </div>
        </header>

        {/* Content Body */}
        <main className="content-body">
          {activeTab === 'overview' ? (
            <div>
              {/* Page Intro */}
              <div className="page-intro">
                <h2 className="page-headline">Incident Operations Overview</h2>
                <p className="page-description">
                  Automated incident synthesis correlating pipeline run history, assertion logs, 
                  and directed acyclic lineage graphs powered by Exasol.
                </p>
              </div>

              {/* Error Banner with Retry */}
              {error && (
                <div className="state-container error">
                  <AlertTriangle size={32} strokeWidth={1.5} className="state-icon-alert" />
                  <div className="state-title">Backend Connection Error</div>
                  <p className="state-subtitle">
                    {error}. Please ensure the FastAPI backend is running at http://127.0.0.1:8000.
                  </p>
                  <button className="btn-retry" onClick={fetchInvestigationsData}>
                    <RefreshCw size={14} strokeWidth={2} />
                    <span>Retry Connection</span>
                  </button>
                </div>
              )}

              {/* Loading State Spinner (when initial load) */}
              {loading && !investigations.length && !error && (
                <div className="state-container">
                  <div className="spinner"></div>
                  <div className="state-title">Synthesizing Incident Evidence...</div>
                  <p className="state-subtitle">
                    Correlating pipeline execution runs, quality assertions, and KPI deviations across Exasol lineage DAGs.
                  </p>
                </div>
              )}

              {/* Summary Cards Grid */}
              <div className="metrics-grid">
                {/* Total Investigations */}
                <div 
                  className="metric-card total" 
                  onClick={() => setActiveTab('investigations')}
                  style={{ cursor: 'pointer' }}
                  title="Click to view all investigations"
                >
                  <div className="metric-header">
                    <span className="metric-label">Total Investigations</span>
                    <div className="metric-icon-bubble">
                      <FolderKanban size={16} strokeWidth={1.8} />
                    </div>
                  </div>
                  <div className="metric-value-row">
                    <span className="metric-value">{totalCount} Cases</span>
                    <span className="metric-badge total">Active Incidents</span>
                  </div>
                  <div className="metric-sub-label">
                    {totalEvidence > 0 ? `${totalEvidence} confirmed evidence records` : 'Correlated from Exasol Lineage'}
                  </div>
                </div>

                {/* Critical Cases */}
                <div 
                  className="metric-card critical"
                  onClick={() => setActiveTab('investigations')}
                  style={{ cursor: 'pointer' }}
                  title="Click to view critical investigations"
                >
                  <div className="metric-header">
                    <span className="metric-label">Critical Cases</span>
                    <div className="metric-icon-bubble">
                      <AlertOctagon size={16} strokeWidth={1.8} />
                    </div>
                  </div>
                  <div className="metric-value-row">
                    <span className="metric-value">{criticalCount} Critical</span>
                    <span className="metric-badge critical">Immediate Action</span>
                  </div>
                  <div className="metric-sub-label">Critical severity pipeline degradations</div>
                </div>

                {/* High Cases */}
                <div 
                  className="metric-card high"
                  onClick={() => setActiveTab('investigations')}
                  style={{ cursor: 'pointer' }}
                  title="Click to view high-severity investigations"
                >
                  <div className="metric-header">
                    <span className="metric-label">High Cases</span>
                    <div className="metric-icon-bubble">
                      <AlertTriangle size={16} strokeWidth={1.8} />
                    </div>
                  </div>
                  <div className="metric-value-row">
                    <span className="metric-value">{highCount} High</span>
                    <span className="metric-badge high">Degraded SLA</span>
                  </div>
                  <div className="metric-sub-label">Freshness & SLA threshold breaches</div>
                </div>

                {/* Silent Corruption */}
                <div 
                  className="metric-card silent"
                  onClick={() => setActiveTab('investigations')}
                  style={{ cursor: 'pointer' }}
                  title="Click to view silent corruption cases"
                >
                  <div className="metric-header">
                    <span className="metric-label">Silent Corruption</span>
                    <div className="metric-icon-bubble">
                      <EyeOff size={16} strokeWidth={1.8} />
                    </div>
                  </div>
                  <div className="metric-value-row">
                    <span className="metric-value">{silentCount} Detected</span>
                    <span className="metric-badge silent">Zero Exception Exit</span>
                  </div>
                  <div className="metric-sub-label">Corrupted data published under SUCCESS exit</div>
                </div>
              </div>

              {/* Workflow Explainer Panel */}
              <div className="workflow-panel">
                <div className="workflow-header">
                  <Layers size={16} strokeWidth={2} className="workflow-header-icon" />
                  <span>Evidence-First Incident Analysis Architecture</span>
                </div>
                <div className="workflow-steps">
                  <div className="step-card">
                    <div className="step-badge">STAGE 01</div>
                    <div className="step-title">Empirical Ingestion</div>
                    <div className="step-desc">
                      Captures execution telemetry, error codes, and row count drifts directly from recorded Exasol table state.
                    </div>
                  </div>

                  <div className="step-card">
                    <div className="step-badge">STAGE 02</div>
                    <div className="step-title">Lineage & Assertion DAG</div>
                    <div className="step-desc">
                      Traverses dependency edges upstream to isolate earliest failure points and downstream blast radius.
                    </div>
                  </div>

                  <div className="step-card">
                    <div className="step-badge">STAGE 03</div>
                    <div className="step-title">Root-Cause Ranking & Action</div>
                    <div className="step-desc">
                      Ranks suspects across 4 weighted factors with a 0.95 confidence ceiling and prescribes recovery playbooks.
                    </div>
                  </div>
                </div>
              </div>

              {/* Active Cases Workbench Table */}
              <div className="workbench-panel">
                <div className="panel-header">
                  <h3 className="panel-title">Active Incident Investigations</h3>
                  <span className="panel-tag live">
                    Exasol Feed ({investigations.length} Cases)
                  </span>
                </div>

                <div style={{ overflowX: 'auto' }}>
                  <table className="cases-table">
                    <thead>
                      <tr>
                        <th>Case ID</th>
                        <th>Incident Title & Causal Flow</th>
                        <th>Root Source Dataset</th>
                        <th>Severity</th>
                        <th>Silent Corruption</th>
                        <th>Downstream Blast Radius</th>
                        <th>Status</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {investigations.length === 0 && !loading && !error ? (
                        <tr>
                          <td colSpan="8" style={{ textAlign: 'center', padding: '32px', color: 'var(--text-sub)' }}>
                            No active data incidents detected in current Exasol snapshot window.
                          </td>
                        </tr>
                      ) : (
                        investigations.map((c) => {
                          const primaryReport = c.downstream_reports && c.downstream_reports.length > 0 
                            ? c.downstream_reports.join(', ') 
                            : 'N/A';
                          const primaryKpi = c.associated_kpis && c.associated_kpis.length > 0 
                            ? c.associated_kpis[0] 
                            : null;
                          const devSign = primaryKpi && primaryKpi.deviation_percent > 0 ? '+' : '';

                          return (
                            <tr 
                              key={c.case_id}
                              onClick={() => {
                                setSelectedCaseId(c.case_id);
                                setActiveTab('investigations');
                              }}
                              style={{ cursor: 'pointer' }}
                              title="Click to inspect this incident case in Investigations workbench"
                            >
                              <td className="case-id-cell">{c.case_id}</td>
                              <td>
                                <div className="case-title-cell">{c.title}</div>
                                <span className="case-flow-text">{c.flow_name}</span>
                              </td>
                              <td>
                                <span className="mono-font" style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>
                                  {c.root_dataset}
                                </span>
                              </td>
                              <td>
                                <span className={`pill ${c.severity === 'CRITICAL' ? 'critical' : 'high'}`}>
                                  {c.severity}
                                </span>
                              </td>
                              <td>
                                {c.silent_data_corruption ? (
                                  <span className="pill silent">DETECTED</span>
                                ) : (
                                  <span className="pill neutral">None</span>
                                )}
                              </td>
                              <td>
                                <div style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                                  {primaryReport}
                                </div>
                                {primaryKpi && (
                                  <span style={{ fontSize: '11px', color: 'var(--status-critical-text)' }}>
                                    {`${devSign}${primaryKpi.deviation_percent}% ${primaryKpi.kpi_name}`}
                                  </span>
                                )}
                              </td>
                              <td>
                                <span className="pill neutral">{c.status}</span>
                              </td>
                              <td>
                                <button
                                  className="btn-refresh"
                                  style={{ fontSize: '11px', padding: '4px 8px' }}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedCaseId(c.case_id);
                                    setActiveTab('investigations');
                                  }}
                                  title="Inspect incident details"
                                >
                                  <span>Inspect</span>
                                  <ArrowRight size={12} strokeWidth={2} />
                                </button>
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : activeTab === 'investigations' ? (
            <InvestigationsView
              investigations={investigations}
              loading={loading}
              error={error}
              onRetry={fetchInvestigationsData}
              selectedCaseId={selectedCaseId}
              onSelectCase={(id) => setSelectedCaseId(id)}
            />
          ) : activeTab === 'lineage' ? (
            <LineageView
              onNavigateToCase={(caseId) => {
                setSelectedCaseId(caseId);
                setActiveTab('investigations');
              }}
              onNavigateToTab={(tab) => setActiveTab(tab)}
            />
          ) : (
            <QualityChecksView
              onNavigateToCase={(caseId) => {
                setSelectedCaseId(caseId);
                setActiveTab('investigations');
              }}
            />
          )}
        </main>
      </div>
    </div>
  );
}
