/**
 * TraceOps API Service
 * Interacts with FastAPI backend running on Exasol.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://traceops-backend-x2mu.onrender.com';

/**
 * Fetch evidence-based root-cause investigation cases from backend.
 * @param {Object} params - Optional query filters (case_id, severity, status, limit)
 * @returns {Promise<Object>} API response payload
 */
export async function getInvestigations(params = {}) {
  const query = new URLSearchParams();
  if (params.case_id) query.append('case_id', params.case_id);
  if (params.severity) query.append('severity', params.severity);
  if (params.status) query.append('status', params.status);
  if (params.limit) query.append('limit', params.limit);

  const qs = query.toString();
  const url = `${API_BASE_URL}/api/investigations${qs ? `?${qs}` : ''}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`HTTP ${response.status} (${response.statusText}): ${errorBody || 'Failed to fetch investigations'}`);
  }

  return await response.json();
}

/**
 * Fetch Data Lineage DAG directly from Exasol TRACEOPS.DATASET_DEPENDENCIES.
 * @returns {Promise<Object>} Lineage graph payload containing nodes, edges, summary, and scenarios
 */
export async function getLineage() {
  const url = `${API_BASE_URL}/api/lineage`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`HTTP ${response.status} (${response.statusText}): ${errorBody || 'Failed to fetch lineage DAG'}`);
  }

  return normalizeLineageResponse(await response.json());
}

/**
 * Normalize the lineage API response to guarantee rich node structure,
 * topological stage mapping, degree counts, dependency lists, and accurate summaries.
 * Works seamlessly with both demo data {id, label, type} and full Exasol lineage records.
 *
 * @param {Object} raw - Raw JSON from the backend
 * @returns {Object} Normalized response
 */
function normalizeLineageResponse(raw) {
  if (!raw) return { nodes: [], edges: [], summary: {}, data_mode: 'live' };

  const edges = (raw.edges || []).map((e) => ({
    source: e.source,
    target: e.target,
    dependency_type: e.dependency_type || 'DATA_FLOW',
    is_critical: Boolean(e.is_critical),
  }));

  const inDegreeMap = {};
  const outDegreeMap = {};
  const upstreamMap = {};
  const downstreamMap = {};
  edges.forEach((e) => {
    outDegreeMap[e.source] = (outDegreeMap[e.source] || 0) + 1;
    inDegreeMap[e.target] = (inDegreeMap[e.target] || 0) + 1;
    if (!upstreamMap[e.target]) upstreamMap[e.target] = [];
    upstreamMap[e.target].push(e.source);
    if (!downstreamMap[e.source]) downstreamMap[e.source] = [];
    downstreamMap[e.source].push(e.target);
  });

  const stageNameMap = {
    1: 'Stage 01: Raw Ingestion',
    2: 'Stage 02: Staging & Cleanse',
    3: 'Stage 03: Dimension / Core',
    4: 'Stage 04: Facts & Aggregation',
    5: 'Stage 05: Analytics & KPIs',
  };

  const nodes = (raw.nodes || []).map((n) => {
    const id = n.id;
    const name = n.name || n.label || id;
    const inDeg = n.in_degree ?? (inDegreeMap[id] || 0);
    const outDeg = n.out_degree ?? (outDegreeMap[id] || 0);
    const rawType = (n.type || n.node_type || '').toLowerCase();

    // Determine node classification
    let nodeType = n.node_type;
    if (!nodeType) {
      if (rawType === 'source' || id.startsWith('raw_') || inDeg === 0) {
        nodeType = 'SOURCE_DATASET';
      } else if (rawType === 'mart' || rawType === 'report' || id.startsWith('rpt_') || id.startsWith('mart_') || outDeg === 0) {
        nodeType = 'DOWNSTREAM_DATASET';
      } else {
        nodeType = 'TRANSFORMATION';
      }
    }

    // Assign topological stage index (1 to 5)
    let stageIdx = n.stage_idx;
    if (stageIdx == null || isNaN(stageIdx) || stageIdx < 1 || stageIdx > 5) {
      if (nodeType === 'SOURCE_DATASET') stageIdx = 1;
      else if (nodeType === 'DOWNSTREAM_DATASET') stageIdx = 5;
      else if (id.startsWith('stg_')) stageIdx = 2;
      else if (id.startsWith('dim_')) stageIdx = 3;
      else if (id.startsWith('fct_')) stageIdx = 4;
      else stageIdx = 3;
    }

    // Guarantee valid stage_name (never 'Stage undefined')
    let stageName = n.stage_name;
    if (!stageName || stageName.includes('undefined')) {
      stageName = stageNameMap[stageIdx] || `Stage ${String(stageIdx).padStart(2, '0')}`;
    }

    return {
      ...n,
      id,
      name,
      label: n.label || name,
      node_type: nodeType,
      stage_idx: stageIdx,
      stage_name: stageName,
      in_degree: inDeg,
      out_degree: outDeg,
      upstream_dependencies: n.upstream_dependencies || upstreamMap[id] || [],
      downstream_dependents: n.downstream_dependents || downstreamMap[id] || [],
      direct_health: n.direct_health || 'HEALTHY',
      downstream_impact: n.downstream_impact || 'NONE',
      is_silent_corruption: Boolean(n.is_silent_corruption),
      is_unmapped: Boolean(n.is_unmapped),
      associated_pipelines: n.associated_pipelines || (n.pipeline_name ? [n.pipeline_name] : []),
      quality_checks: n.quality_checks || [],
      kpis: n.kpis || [],
      related_cases: n.related_cases || [],
      direct_issues: n.direct_issues || [],
    };
  });

  const sourceCount = nodes.filter((n) => n.node_type === 'SOURCE_DATASET').length;
  const transformCount = nodes.filter((n) => n.node_type === 'TRANSFORMATION').length;
  const downstreamCount = nodes.filter((n) => n.node_type === 'DOWNSTREAM_DATASET').length;

  // Use accurate counts that do not contradict actual nodes/edges
  const rawSummary = raw.summary || {};
  const summary = {
    source_datasets: (rawSummary.source_datasets && rawSummary.source_datasets > 0) ? rawSummary.source_datasets : sourceCount,
    transformations: (rawSummary.transformations && rawSummary.transformations > 0) ? rawSummary.transformations : transformCount,
    downstream_datasets: (rawSummary.downstream_datasets && rawSummary.downstream_datasets > 0) ? rawSummary.downstream_datasets : downstreamCount,
    total_dependencies: (rawSummary.total_dependencies && rawSummary.total_dependencies > 0) ? rawSummary.total_dependencies : edges.length,
  };
  // Guarantee non-zero counts if nodes exist
  if (sourceCount > 0 && !summary.source_datasets) summary.source_datasets = sourceCount;
  if (transformCount > 0 && !summary.transformations) summary.transformations = transformCount;
  if (downstreamCount > 0 && !summary.downstream_datasets) summary.downstream_datasets = downstreamCount;
  if (edges.length > 0 && !summary.total_dependencies) summary.total_dependencies = edges.length;

  return {
    ...raw,
    data_mode: raw.data_mode || 'live',
    nodes,
    edges,
    summary,
  };
}

/**
 * Fetch empirical quality checks from TRACEOPS.DATA_QUALITY_CHECKS.
 * @param {Object} params - Optional query filters (status, severity, dataset, search, limit)
 * @returns {Promise<Object>} Quality checks payload containing checks and summary metrics
 */
export async function getQualityChecks(params = {}) {
  const query = new URLSearchParams();
  if (params.status && params.status !== 'ALL') query.append('status', params.status);
  if (params.severity && params.severity !== 'ALL') query.append('severity', params.severity);
  if (params.dataset && params.dataset !== 'ALL') query.append('dataset', params.dataset);
  if (params.search) query.append('search', params.search);
  if (params.limit) query.append('limit', params.limit);

  const qs = query.toString();
  const url = `${API_BASE_URL}/api/quality-checks${qs ? `?${qs}` : ''}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`HTTP ${response.status} (${response.statusText}): ${errorBody || 'Failed to fetch quality checks'}`);
  }

  return normalizeQualityChecksResponse(await response.json());
}

/**
 * Normalize the quality-checks API response so QualityChecksView always gets
 * the shape it expects, regardless of whether the deployed backend is the old
 * version (returns `quality_checks` key, no `global_summary`) or the new one
 * (returns `checks` key with `global_summary`).
 *
 * @param {Object} raw - Raw JSON from the backend
 * @returns {Object} Normalized response
 */
function normalizeQualityChecksResponse(raw) {
  if (!raw) return { checks: [], global_summary: {}, data_mode: 'live' };

  // Accept either key name: checks or quality_checks
  const dataMode = raw.data_mode || 'live';
  const rawList = raw.checks || raw.quality_checks || [];
  const checks = rawList.map((item) => {
    const statusVal = item.check_status || item.status || 'UNKNOWN';
    return {
      ...item,
      check_id: item.check_id || `CHK-${Math.random().toString(36).substring(2, 7).toUpperCase()}`,
      dataset_name: item.dataset_name || 'unknown_dataset',
      check_type: item.check_type || 'GENERAL',
      expected_value: item.expected_value != null ? String(item.expected_value) : '—',
      actual_value: item.actual_value != null ? String(item.actual_value) : '—',
      severity: (item.severity || 'MEDIUM').toUpperCase(),
      // Guarantee both check_status and status are present
      status: statusVal,
      check_status: statusVal,
      observed_at: item.observed_at || null,
      evidence_details: item.evidence_details || item.description || 'No additional evidence recorded.',
      data_mode: item.data_mode || dataMode,
    };
  });

  // Compute global_summary from all checks when the backend does not supply it
  const existingSummary = raw.global_summary || null;
  const global_summary = existingSummary || {
    total_checks: raw.total ?? checks.length,
    passed_checks:  checks.filter((c) => (c.check_status || c.status) === 'PASSED').length,
    failed_checks:  checks.filter((c) => (c.check_status || c.status) === 'FAILED').length,
    warning_checks: checks.filter((c) => (c.check_status || c.status) === 'WARNING').length,
    critical_checks: checks.filter((c) => c.severity === 'CRITICAL').length,
    high_checks:    checks.filter((c) => c.severity === 'HIGH').length,
    medium_checks:  checks.filter((c) => c.severity === 'MEDIUM').length,
    low_checks:     checks.filter((c) => c.severity === 'LOW').length,
  };

  return {
    ...raw,
    data_mode: dataMode,
    checks,
    global_summary,
  };
}

/**
 * Check live Exasol database connectivity.
 * @returns {Promise<Object>} Exasol health payload
 */
export async function getExasolHealth() {
  const url = `${API_BASE_URL}/api/exasol/health`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Accept': 'application/json',
    },
  });

  // Note: /api/exasol/health returns 503 if disconnected, so we parse JSON even on non-ok
  try {
    const data = await response.json();
    return { ...data, isConnected: response.ok && data.status === 'healthy' };
  } catch {
    return { isConnected: false, status: 'unhealthy', error: 'Service unavailable' };
  }
}
