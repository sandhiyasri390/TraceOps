/**
 * TraceOps API Service
 * Interacts with FastAPI backend running on Exasol.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

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

  return await response.json();
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

  return await response.json();
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

