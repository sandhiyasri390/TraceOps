
/**
 * TraceOps API Service
 * Connects the React frontend to the FastAPI backend hosted on Render.
 */

const API_BASE_URL = (
  import.meta.env.VITE_API_URL ||
  'https://traceops-backend-x2mu.onrender.com'
).replace(/\/+$/, '');

/**
 * Common helper for API requests.
 */
async function apiRequest(endpoint) {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    const errorBody = await response.text();

    throw new Error(
      `HTTP ${response.status} (${response.statusText}): ${errorBody || 'API request failed'
      }`
    );
  }

  return response.json();
}

/**
 * Fetch root-cause investigation cases.
 */
export async function getInvestigations(params = {}) {
  const query = new URLSearchParams();

  if (params.case_id) query.append('case_id', params.case_id);
  if (params.severity) query.append('severity', params.severity);
  if (params.status) query.append('status', params.status);
  if (params.limit) query.append('limit', params.limit);

  const qs = query.toString();
  const endpoint = `/api/investigations${qs ? `?${qs}` : ''}`;

  return apiRequest(endpoint);
}

/**
 * Fetch the data lineage graph.
 */
export async function getLineage() {
  return apiRequest('/api/lineage');
}

/**
 * Fetch data quality checks.
 */
export async function getQualityChecks(params = {}) {
  const query = new URLSearchParams();

  if (params.status && params.status !== 'ALL') {
    query.append('status', params.status);
  }

  if (params.severity && params.severity !== 'ALL') {
    query.append('severity', params.severity);
  }

  if (params.dataset && params.dataset !== 'ALL') {
    query.append('dataset', params.dataset);
  }

  if (params.search) query.append('search', params.search);
  if (params.limit) query.append('limit', params.limit);

  const qs = query.toString();
  const endpoint = `/api/quality-checks${qs ? `?${qs}` : ''}`;

  return apiRequest(endpoint);
}

/**
 * Check backend health.
 */
export async function getApiHealth() {
  return apiRequest('/api/health');
}

/**
 * Check Exasol database connectivity.
 */
export async function getExasolHealth() {
  try {
    const data = await apiRequest('/api/exasol/health');

    return {
      ...data,
      isConnected: data.status === 'healthy',
    };
  } catch (error) {
    return {
      isConnected: false,
      status: 'unhealthy',
      error: error.message || 'Service unavailable',
    };
  }
}
