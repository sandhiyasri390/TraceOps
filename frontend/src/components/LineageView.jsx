import React, { useState, useEffect, useMemo, useRef } from 'react';
import { getLineage } from '../services/api';
import {
  Database,
  Workflow,
  TrendingUp,
  TrendingDown,
  GitFork,
  Search,
  X,
  RefreshCw,
  AlertTriangle,
  AlertOctagon,
  ArrowUp,
  ArrowDown,
  ArrowRight,
  ChevronRight,
  ShieldCheck,
  EyeOff,
  Layers
} from 'lucide-react';

export default function LineageView({
  onNavigateToCase,
  onNavigateToTab,
}) {
  const [lineageData, setLineageData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter & interaction state
  const [selectedScenario, setSelectedScenario] = useState('ALL');
  const [selectedNodeType, setSelectedNodeType] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [traceMode, setTraceMode] = useState('ALL'); // 'ALL' | 'UPSTREAM' | 'DOWNSTREAM'

  const graphContainerRef = useRef(null);

  // Fetch lineage from live API
  const fetchLineageData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getLineage();
      setLineageData(data);
      if (data.nodes && data.nodes.length > 0 && !selectedNodeId) {
        const firstSource = data.nodes.find((n) => n.node_type === 'SOURCE_DATASET');
        setSelectedNodeId(firstSource ? firstSource.id : data.nodes[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch lineage data:', err);
      setError(err.message || 'Failed to connect to Exasol Lineage Engine');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLineageData();
  }, []);

  // Filter nodes based on scenario and node type
  const { filteredNodes, filteredEdges, activeScenarioMeta } = useMemo(() => {
    if (!lineageData) {
      return { filteredNodes: [], filteredEdges: [], activeScenarioMeta: null };
    }

    const { nodes = [], edges = [], scenarios = [] } = lineageData;

    let scenarioMeta = null;
    let allowedNodeIds = new Set(nodes.map((n) => n.id));

    if (selectedScenario !== 'ALL') {
      scenarioMeta = scenarios.find((s) => s.case_id === selectedScenario) || null;
      if (scenarioMeta && scenarioMeta.datasets) {
        allowedNodeIds = new Set(scenarioMeta.datasets);
      }
    }

    const nodesList = nodes.filter((n) => {
      if (!allowedNodeIds.has(n.id)) return false;
      if (selectedNodeType !== 'ALL' && n.node_type !== selectedNodeType) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = n.name.toLowerCase().includes(q);
        const matchType = n.node_type.toLowerCase().includes(q);
        const matchPipe = n.associated_pipelines?.some((p) => p.toLowerCase().includes(q));
        if (!matchName && !matchType && !matchPipe) return false;
      }
      return true;
    });

    const activeNodeIds = new Set(nodesList.map((n) => n.id));

    const edgesList = edges.filter((e) => {
      return activeNodeIds.has(e.source) && activeNodeIds.has(e.target);
    });

    return {
      filteredNodes: nodesList,
      filteredEdges: edgesList,
      activeScenarioMeta: scenarioMeta,
    };
  }, [lineageData, selectedScenario, selectedNodeType, searchQuery]);

  // Active selected node object
  const activeNode = useMemo(() => {
    if (!lineageData || !lineageData.nodes) return null;
    return lineageData.nodes.find((n) => n.id === selectedNodeId) || null;
  }, [lineageData, selectedNodeId]);

  // Synchronize selected node when scenario or search filter changes
  useEffect(() => {
    if (filteredNodes.length > 0) {
      const isVisible = filteredNodes.some((n) => n.id === selectedNodeId);
      if (!isVisible) {
        setSelectedNodeId(filteredNodes[0].id);
      }
    }
  }, [filteredNodes, selectedNodeId]);

  // Compute upstream ancestor and downstream descendant sets for highlighted tracing
  const { highlightedUpstream, highlightedDownstream } = useMemo(() => {
    if (!selectedNodeId || !lineageData) {
      return { highlightedUpstream: new Set(), highlightedDownstream: new Set() };
    }

    const { edges = [] } = lineageData;
    const upSet = new Set();
    const downSet = new Set();

    // Upstream BFS
    const upQueue = [selectedNodeId];
    while (upQueue.length > 0) {
      const curr = upQueue.pop();
      edges.forEach((e) => {
        if (e.target === curr && !upSet.has(e.source)) {
          upSet.add(e.source);
          upQueue.push(e.source);
        }
      });
    }

    // Downstream BFS
    const downQueue = [selectedNodeId];
    while (downQueue.length > 0) {
      const curr = downQueue.pop();
      edges.forEach((e) => {
        if (e.source === curr && !downSet.has(e.target)) {
          downSet.add(e.target);
          downQueue.push(e.target);
        }
      });
    }

    return { highlightedUpstream: upSet, highlightedDownstream: downSet };
  }, [selectedNodeId, lineageData]);

  // Group filtered nodes into topological stages
  const stageColumns = useMemo(() => {
    const stages = [
      { id: 1, name: 'Stage 01: Raw Ingestion', key: 'STAGE_01', nodes: [] },
      { id: 2, name: 'Stage 02: Staging & Cleanse', key: 'STAGE_02', nodes: [] },
      { id: 3, name: 'Stage 03: Dimension / Core', key: 'STAGE_03', nodes: [] },
      { id: 4, name: 'Stage 04: Facts & Aggregation', key: 'STAGE_04', nodes: [] },
      { id: 5, name: 'Stage 05: Analytics & KPIs', key: 'STAGE_05', nodes: [] },
    ];

    filteredNodes.forEach((node) => {
      let stageIndex = (node.stage_idx ?? 1) - 1;
      if (stageIndex < 0) stageIndex = 0;
      if (stageIndex >= stages.length) stageIndex = stages.length - 1;
      stages[stageIndex].nodes.push(node);
    });

    return stages;
  }, [filteredNodes]);

  if (loading && !lineageData) {
    return (
      <div className="state-container">
        <div className="spinner"></div>
        <div className="state-title">Querying Exasol Lineage DAG...</div>
        <p className="state-subtitle">
          Constructing topological dependency graph directly from TRACEOPS.DATASET_DEPENDENCIES records.
        </p>
      </div>
    );
  }

  if (error && !lineageData) {
    return (
      <div className="state-container error">
        <AlertTriangle size={32} strokeWidth={1.5} className="state-icon-alert" />
        <div className="state-title">Failed to Load Lineage Graph</div>
        <p className="state-subtitle">{error}</p>
        <button className="btn-retry" onClick={fetchLineageData}>
          <RefreshCw size={14} strokeWidth={2} />
          <span>Retry Connection</span>
        </button>
      </div>
    );
  }

  const summary = lineageData?.summary || {};

  return (
    <div className="lineage-page-container">
      {/* 1. Header & Summary Stats */}
      <div className="lineage-header-bar">
        <div>
          <h2 className="page-headline">Data Lineage Directed Acyclic Graph</h2>
          <p className="page-description">
            Complete data-flow topology synthesized from <code>TRACEOPS.DATASET_DEPENDENCIES</code> in Exasol.
            Traces end-to-end lineage from ingestion roots through transformations to executive KPI reports.
          </p>
        </div>

        <div className="lineage-metrics-chips">
          <div className="stat-chip source">
            <span className="chip-icon">
              <Database size={15} strokeWidth={2} />
            </span>
            <div>
              <span className="stat-chip-num">{summary.source_datasets ?? 6}</span>
              <span className="stat-chip-lbl">Sources</span>
            </div>
          </div>

          <div className="stat-chip transform">
            <span className="chip-icon">
              <Workflow size={15} strokeWidth={2} />
            </span>
            <div>
              <span className="stat-chip-num">{summary.transformations ?? 11}</span>
              <span className="stat-chip-lbl">Transforms</span>
            </div>
          </div>

          <div className="stat-chip downstream">
            <span className="chip-icon">
              <TrendingUp size={15} strokeWidth={2} />
            </span>
            <div>
              <span className="stat-chip-num">{summary.downstream_datasets ?? 4}</span>
              <span className="stat-chip-lbl">Reports</span>
            </div>
          </div>

          <div className="stat-chip critical">
            <span className="chip-icon">
              <GitFork size={15} strokeWidth={2} />
            </span>
            <div>
              <span className="stat-chip-num">{summary.total_dependencies ?? 20}</span>
              <span className="stat-chip-lbl">Exasol Edges</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Interactive Controls & Scenario Switcher Bar */}
      <div className="lineage-controls-card">
        {/* Scenario Selectors */}
        <div className="scenario-filter-row">
          <span className="control-label">Investigation Scenario:</span>
          <div className="scenario-chips-scroll">
            <button
              className={`scenario-pill ${selectedScenario === 'ALL' ? 'active' : ''}`}
              onClick={() => setSelectedScenario('ALL')}
            >
              All Scenarios (Full Exasol Graph: 21 nodes)
            </button>
            {lineageData?.scenarios?.map((sc) => (
              <button
                key={sc.case_id}
                className={`scenario-pill ${selectedScenario === sc.case_id ? 'active' : ''}`}
                onClick={() => setSelectedScenario(sc.case_id)}
                title={sc.title}
              >
                <span className={`pill-dot ${sc.severity === 'CRITICAL' ? 'critical' : 'high'}`}></span>
                <span>{sc.flow_name}</span>
                <span className="scenario-node-count">({sc.node_count} nodes)</span>
              </button>
            ))}
          </div>
        </div>

        {/* Toolbar: Search, Type filter, Trace mode */}
        <div className="lineage-toolbar-row">
          <div className="toolbar-left">
            <div className="search-box-wrapper" style={{ minWidth: '260px' }}>
              <Search size={14} strokeWidth={2} className="search-icon" />
              <input
                type="text"
                className="search-input"
                placeholder="Search dataset, pipeline..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button className="clear-search" onClick={() => setSearchQuery('')} title="Clear search">
                  <X size={12} strokeWidth={2} />
                </button>
              )}
            </div>

            <div className="type-filter-group">
              <span className="control-label" style={{ marginRight: '6px' }}>Filter Type:</span>
              <button
                className={`chip-btn ${selectedNodeType === 'ALL' ? 'active' : ''}`}
                onClick={() => setSelectedNodeType('ALL')}
              >
                All ({filteredNodes.length})
              </button>
              <button
                className={`chip-btn source ${selectedNodeType === 'SOURCE_DATASET' ? 'active' : ''}`}
                onClick={() => setSelectedNodeType('SOURCE_DATASET')}
              >
                Sources
              </button>
              <button
                className={`chip-btn transform ${selectedNodeType === 'TRANSFORMATION' ? 'active' : ''}`}
                onClick={() => setSelectedNodeType('TRANSFORMATION')}
              >
                Transformations
              </button>
              <button
                className={`chip-btn downstream ${selectedNodeType === 'DOWNSTREAM_DATASET' ? 'active' : ''}`}
                onClick={() => setSelectedNodeType('DOWNSTREAM_DATASET')}
              >
                Reports
              </button>
            </div>
          </div>

          <div className="toolbar-right">
            <span className="control-label">Highlight Path:</span>
            <div className="trace-mode-toggle">
              <button
                className={`trace-btn ${traceMode === 'ALL' ? 'active' : ''}`}
                onClick={() => setTraceMode('ALL')}
              >
                Full Graph
              </button>
              <button
                className={`trace-btn ${traceMode === 'UPSTREAM' ? 'active' : ''}`}
                onClick={() => setTraceMode('UPSTREAM')}
                title="Trace all upstream root sources feeding selected node"
              >
                <ArrowUp size={12} strokeWidth={2} style={{ marginRight: '4px' }} />
                Upstream
              </button>
              <button
                className={`trace-btn ${traceMode === 'DOWNSTREAM' ? 'active' : ''}`}
                onClick={() => setTraceMode('DOWNSTREAM')}
                title="Trace all downstream blast radius dependent on selected node"
              >
                <ArrowDown size={12} strokeWidth={2} style={{ marginRight: '4px' }} />
                Downstream
              </button>
            </div>
          </div>
        </div>

        {/* Legend bar */}
        <div className="lineage-legend-row">
          <div className="legend-item">
            <span className="legend-indicator source"></span>
            <span>Source Dataset (Raw Ingestion)</span>
          </div>
          <div className="legend-item">
            <span className="legend-indicator transform"></span>
            <span>Transformation (Staging / Fact / Dim)</span>
          </div>
          <div className="legend-item">
            <span className="legend-indicator downstream"></span>
            <span>Downstream Target (Reporting / Analytics)</span>
          </div>
          <div className="legend-item">
            <span className="legend-dot healthy"></span>
            <span>Direct Pipeline Healthy</span>
          </div>
          <div className="legend-item">
            <span className="legend-dot critical"></span>
            <span>Direct Component Failed</span>
          </div>
          <div className="legend-item">
            <span className="legend-dot warning"></span>
            <span>Assertion Warning / Silent Anomaly</span>
          </div>
        </div>
      </div>

      {/* 3. Main DAG Stage Matrix + Node Inspector Panel */}
      <div className="lineage-main-layout">
        {/* Left: DAG Topological Stages */}
        <div className="dag-board-container" ref={graphContainerRef}>
          {filteredNodes.length === 0 ? (
            <div className="empty-search-state" style={{ padding: '60px 20px' }}>
              <Search size={32} strokeWidth={1.5} className="empty-icon" />
              <div style={{ fontSize: '16px', fontWeight: 600, color: '#fff' }}>No Lineage Nodes Found</div>
              <p style={{ color: 'var(--text-sub)', marginTop: '6px' }}>
                No datasets match query &quot;{searchQuery}&quot; in scenario {selectedScenario}.
              </p>
              <button
                className="btn-refresh"
                style={{ marginTop: '12px', margin: '12px auto 0' }}
                onClick={() => {
                  setSearchQuery('');
                  setSelectedNodeType('ALL');
                  setSelectedScenario('ALL');
                }}
              >
                Reset Filters
              </button>
            </div>
          ) : (
            <div className="dag-stages-matrix">
              {stageColumns.map((col) => {
                if (col.nodes.length === 0) return null;

                return (
                  <div key={col.id} className="dag-stage-column">
                    <div className="stage-column-header">
                      <span className="stage-title">{col.name}</span>
                      <span className="stage-count-badge">{col.nodes.length}</span>
                    </div>

                    <div className="stage-nodes-list">
                      {col.nodes.map((node) => {
                        const isSelected = selectedNodeId === node.id;

                        // Check if highlighted in trace mode
                        let isDimmed = false;
                        if (traceMode === 'UPSTREAM' && selectedNodeId) {
                          isDimmed = node.id !== selectedNodeId && !highlightedUpstream.has(node.id);
                        } else if (traceMode === 'DOWNSTREAM' && selectedNodeId) {
                          isDimmed = node.id !== selectedNodeId && !highlightedDownstream.has(node.id);
                        }

                        // Node classification styling
                        let typeClass = 'transform-node';
                        let TypeIcon = Workflow;
                        let typeLabel = 'TRANSFORMATION';

                        if (node.node_type === 'SOURCE_DATASET') {
                          typeClass = 'source-node';
                          TypeIcon = Database;
                          typeLabel = 'SOURCE';
                        } else if (node.node_type === 'DOWNSTREAM_DATASET') {
                          typeClass = 'downstream-node';
                          TypeIcon = TrendingUp;
                          typeLabel = 'REPORT';
                        }

                        // Direct health vs downstream impact distinction
                        const isSilent = Boolean(node.is_silent_corruption);
                        const hasFailedCheck = node.quality_checks && node.quality_checks.some((c) => c.check_status === 'FAILED');
                        const directHealth = hasFailedCheck && (!node.direct_health || node.direct_health === 'HEALTHY')
                          ? 'WARNING'
                          : (node.direct_health || 'HEALTHY');
                        const downstreamImpact = node.downstream_impact || 'NONE';

                        let healthDotClass = 'healthy';
                        if (directHealth === 'CRITICAL') healthDotClass = 'critical';
                        else if (directHealth === 'WARNING') healthDotClass = 'warning';

                        return (
                          <div
                            key={node.id}
                            className={`dag-node-card ${typeClass} ${isSelected ? 'selected' : ''} ${isDimmed ? 'dimmed' : ''}`}
                            onClick={() => setSelectedNodeId(node.id)}
                            title={`Click to inspect dependencies and telemetry for ${node.name}`}
                          >
                            <div className="node-card-top">
                              <span className="node-type-label">
                                <span className="type-icon">
                                  <TypeIcon size={12} strokeWidth={2} />
                                </span>
                                <span>{typeLabel}</span>
                              </span>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                {isSilent && (
                                  <span className="node-silent-badge" title="Silent corruption: Pipeline succeeded but data is corrupted">
                                    <EyeOff size={10} strokeWidth={2} style={{ marginRight: '2px' }} />
                                    SILENT
                                  </span>
                                )}
                                <span className={`node-health-dot ${healthDotClass}`}></span>
                              </div>
                            </div>

                            <div className="node-card-name mono-font" title={node.name}>
                              {node.name}
                            </div>

                            {/* Downstream Impact Alert Tag if impacted */}
                            {downstreamImpact === 'CRITICAL_KPI_DEVIATION' ? (
                              <div style={{ margin: '1px 0' }}>
                                <span className="node-impact-tag critical" title="Direct or downstream KPI deviation detected">
                                  <TrendingDown size={10} strokeWidth={2} style={{ marginRight: '2px' }} />
                                  KPI DEVIATED
                                </span>
                              </div>
                            ) : downstreamImpact === 'AFFECTED_BY_UPSTREAM' ? (
                              <div style={{ margin: '1px 0' }}>
                                <span className="node-impact-tag affected" title="Impacted by upstream pipeline failure">
                                  <ArrowUp size={10} strokeWidth={2} style={{ marginRight: '2px' }} />
                                  UPSTREAM IMPACT
                                </span>
                              </div>
                            ) : null}

                            {node.associated_pipelines && node.associated_pipelines.length > 0 && (
                              <div className="node-pipeline-tag mono-font">
                                <span>pipe:</span> {node.associated_pipelines[0]}
                              </div>
                            )}

                            <div className="node-card-footer">
                              <span className="node-edge-counter" title="Incoming dependencies">
                                In: <strong>{node.in_degree}</strong>
                              </span>
                              <span className="node-edge-counter" title="Outgoing dependents">
                                Out: <strong>{node.out_degree}</strong>
                              </span>
                              {node.quality_checks && node.quality_checks.length > 0 && (
                                <span className="node-alert-pill" title={`${node.quality_checks.length} assertions triggered`}>
                                  <AlertTriangle size={10} strokeWidth={2} style={{ marginRight: '2px' }} />
                                  {node.quality_checks.length}
                                </span>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: Comprehensive Node Inspector Drawer */}
        <aside className="node-inspector-pane">
          {activeNode ? (
            <div className="inspector-content-scroll">
              <div className="inspector-header">
                <span className="inspector-tag-type">{activeNode.node_type}</span>
                <h3 className="inspector-node-title mono-font">{activeNode.name}</h3>
                <div className="inspector-layer-meta">
                  <span>{activeNode.stage_name ?? `Stage ${activeNode.stage_idx}`}</span>
                  <span>•</span>
                  <span>In: {activeNode.in_degree} | Out: {activeNode.out_degree}</span>
                </div>
              </div>

              {/* Node Health Matrix */}
              <div className="inspector-health-box">
                <div className="health-grid-row">
                  <div className="health-grid-col">
                    <span className="health-grid-lbl">Direct Node Health:</span>
                    <span className={`pill ${activeNode.direct_health === 'CRITICAL' ? 'critical' : activeNode.direct_health === 'WARNING' ? 'high' : 'healthy'}`}>
                      {activeNode.direct_health || 'HEALTHY'}
                    </span>
                  </div>
                  <div className="health-grid-col">
                    <span className="health-grid-lbl">Downstream Impact:</span>
                    <span className={`pill ${activeNode.downstream_impact === 'CRITICAL_KPI_DEVIATION' ? 'critical' : activeNode.downstream_impact === 'AFFECTED_BY_UPSTREAM' ? 'high' : 'neutral'}`}>
                      {activeNode.downstream_impact ? activeNode.downstream_impact.replace(/_/g, ' ') : 'NONE'}
                    </span>
                  </div>
                </div>

                {/* Direct Issues List */}
                {activeNode.direct_issues && activeNode.direct_issues.length > 0 && (
                  <div className="inspector-direct-issues-box">
                    <div className="direct-issues-title">
                      <AlertTriangle size={14} strokeWidth={2} />
                      <span>Direct Diagnostic Evidence ({activeNode.direct_issues.length})</span>
                    </div>
                    <ul className="direct-issues-list">
                      {activeNode.direct_issues.map((issue, idx) => (
                        <li key={idx} className="direct-issue-item">
                          {issue}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Silent Corruption Alert Callout */}
                {activeNode.is_silent_corruption && (
                  <div className="silent-corruption-callout">
                    <div className="callout-header">
                      <EyeOff size={14} strokeWidth={2} />
                      <strong>Silent Data Corruption Alert</strong>
                    </div>
                    <p>
                      Associated pipeline reported <code>SUCCESS</code>, but data-quality telemetry detected critical anomaly (e.g. numeric outlier / currency multiplier bug). Downstream reports are consuming corrupted records despite green pipeline status.
                    </p>
                  </div>
                )}

                {activeNode.is_unmapped && (
                  <div className="unmapped-node-alert">
                    <AlertTriangle size={14} strokeWidth={2} style={{ display: 'inline', marginRight: '4px' }} />
                    This dataset has no resolved dependency lineage in <code>TRACEOPS.DATASET_DEPENDENCIES</code>. It is disconnected from the canonical DAG.
                  </div>
                )}
              </div>

              {/* Related Investigation Cases Banner */}
              {activeNode.related_cases && activeNode.related_cases.length > 0 && (
                <div className="inspector-case-link-card">
                  <div className="case-link-header">
                    <AlertOctagon size={14} strokeWidth={2} />
                    <span>Correlated Investigation Case</span>
                  </div>
                  {activeNode.related_cases.map((cid) => (
                    <div key={cid} className="case-link-row">
                      <span className="mono-font case-id-text">{cid}</span>
                      {onNavigateToCase && (
                        <button
                          className="btn-refresh"
                          style={{ padding: '3px 8px', fontSize: '11px' }}
                          onClick={() => onNavigateToCase(cid)}
                        >
                          <span>Investigate</span>
                          <ArrowRight size={11} strokeWidth={2} />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Upstream Dependencies (Incoming) */}
              <div className="inspector-section">
                <div className="section-label">
                  <ArrowUp size={13} strokeWidth={2} />
                  <span>Upstream Dependencies ({activeNode.upstream_dependencies?.length || 0})</span>
                </div>
                {activeNode.upstream_dependencies && activeNode.upstream_dependencies.length > 0 ? (
                  <div className="dep-nodes-list">
                    {activeNode.upstream_dependencies.map((upName) => {
                      const edge = lineageData.edges?.find(
                        (e) => e.source === upName && e.target === activeNode.id
                      );
                      return (
                        <div
                          key={upName}
                          className="dep-item-card"
                          onClick={() => setSelectedNodeId(upName)}
                          title="Click to select this upstream dataset"
                        >
                          <div className="dep-item-top">
                            <span className="dep-name mono-font">{upName}</span>
                            {edge?.is_critical && (
                              <span className="pill critical" style={{ fontSize: '9px', padding: '1px 5px' }}>
                                CRITICAL
                              </span>
                            )}
                          </div>
                          {edge && (
                            <div className="dep-item-type">
                              Type: <strong>{edge.dependency_type}</strong>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="empty-dep-box">
                    This is an upstream ingestion root source (In-degree: 0).
                  </div>
                )}
              </div>

              {/* Downstream Dependents (Outgoing) */}
              <div className="inspector-section">
                <div className="section-label">
                  <ArrowDown size={13} strokeWidth={2} />
                  <span>Downstream Dependents ({activeNode.downstream_dependents?.length || 0})</span>
                </div>
                {activeNode.downstream_dependents && activeNode.downstream_dependents.length > 0 ? (
                  <div className="dep-nodes-list">
                    {activeNode.downstream_dependents.map((downName) => {
                      const edge = lineageData.edges?.find(
                        (e) => e.source === activeNode.id && e.target === downName
                      );
                      return (
                        <div
                          key={downName}
                          className="dep-item-card"
                          onClick={() => setSelectedNodeId(downName)}
                          title="Click to select this downstream dataset"
                        >
                          <div className="dep-item-top">
                            <span className="dep-name mono-font">{downName}</span>
                            {edge?.is_critical && (
                              <span className="pill critical" style={{ fontSize: '9px', padding: '1px 5px' }}>
                                CRITICAL
                              </span>
                            )}
                          </div>
                          {edge && (
                            <div className="dep-item-type">
                              Type: <strong>{edge.dependency_type}</strong>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="empty-dep-box">
                    This is a terminal downstream reporting artifact (Out-degree: 0).
                  </div>
                )}
              </div>

              {/* Associated Transformation Pipelines */}
              {activeNode.associated_pipelines && activeNode.associated_pipelines.length > 0 && (
                <div className="inspector-section">
                  <div className="section-label">
                    <Workflow size={13} strokeWidth={2} />
                    <span>Associated Pipelines ({activeNode.associated_pipelines.length})</span>
                  </div>
                  <div className="pipelines-list">
                    {activeNode.associated_pipelines.map((pname) => (
                      <div key={pname} className="pipeline-item mono-font">
                        <ChevronRight size={12} strokeWidth={2} style={{ marginRight: '4px' }} />
                        <span>{pname}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Empirical Assertions (Quality Checks) */}
              {activeNode.quality_checks && activeNode.quality_checks.length > 0 && (
                <div className="inspector-section">
                  <div className="section-label">
                    <ShieldCheck size={13} strokeWidth={2} />
                    <span>Observed Quality Assertions ({activeNode.quality_checks.length})</span>
                  </div>
                  <div className="inspector-checks-list">
                    {activeNode.quality_checks.map((chk) => (
                      <div key={chk.check_id} className="inspector-check-card">
                        <div className="chk-top">
                          <span className="chk-type mono-font">{chk.check_type}</span>
                          <span className={`pill ${chk.severity === 'CRITICAL' ? 'critical' : 'high'}`}>
                            {chk.severity}
                          </span>
                        </div>
                        <p className="chk-details">{chk.evidence_details}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Associated Downstream KPIs */}
              {activeNode.kpis && activeNode.kpis.length > 0 && (
                <div className="inspector-section">
                  <div className="section-label">
                    <TrendingUp size={13} strokeWidth={2} />
                    <span>Downstream Business KPIs ({activeNode.kpis.length})</span>
                  </div>
                  <div className="inspector-checks-list">
                    {activeNode.kpis.map((kpi, idx) => (
                      <div key={idx} className="inspector-check-card">
                        <div className="chk-top">
                          <strong style={{ color: '#fff' }}>{kpi.kpi_name}</strong>
                          <span className="pill critical">
                            {kpi.deviation_percent > 0 ? '+' : ''}{kpi.deviation_percent}%
                          </span>
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--text-dim)', margin: '4px 0' }}>
                          Report: {kpi.report_name}
                        </div>
                        <p className="chk-details">{kpi.business_impact}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="empty-workbench-state" style={{ padding: '40px 16px' }}>
              <GitFork size={32} strokeWidth={1.5} className="empty-icon" />
              <div style={{ fontWeight: 600, color: '#fff' }}>Select a Lineage Node</div>
              <p style={{ fontSize: '12px', color: 'var(--text-sub)', marginTop: '4px' }}>
                Click any dataset node in the DAG to inspect its upstream sources, downstream blast radius, and pipeline telemetry.
              </p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
