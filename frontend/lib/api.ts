import type {
  Incident,
  AgentRun,
  SimilarIncident,
  BaselineAnalysis,
  ActionMetric,
  HostMetric,
  Pattern,
} from './types';

const BASE = '/api/v1';

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// Incidents
export const getIncidents = (params?: Record<string, string>) => {
  const qs = params ? '?' + new URLSearchParams(params).toString() : '';
  return apiFetch<Incident[]>(`/incidents${qs}`);
};

export const getIncident = (id: string) =>
  apiFetch<Incident>(`/incidents/${id}`);

export const acknowledgeIncident = (id: string) =>
  apiFetch<Incident>(`/incidents/${id}/acknowledge`, { method: 'POST' });

export const markFalsePositive = (id: string) =>
  apiFetch<Incident>(`/incidents/${id}/false-positive`, { method: 'POST' });

export const escalateIncident = (id: string, body: Record<string, unknown>) =>
  apiFetch<Incident>(`/incidents/${id}/escalate`, {
    method: 'POST',
    body: JSON.stringify(body),
  });

export const getSimilarIncidents = (id: string) =>
  apiFetch<SimilarIncident[]>(`/incidents/${id}/similar`);

export const getIncidentEnrichment = (id: string) =>
  apiFetch<Record<string, unknown>>(`/incidents/${id}/enrichment`);

// Feedback / metrics
export const getActionMetrics = () =>
  apiFetch<ActionMetric[]>('/metrics/actions');

export const getHostMetrics = (hostname: string) =>
  apiFetch<HostMetric>(`/metrics/hosts/${hostname}`);

export const getRecentPatterns = () =>
  apiFetch<Pattern[]>('/patterns/recent');

export const getActiveRecurrences = () =>
  apiFetch<Pattern[]>('/recurrence/active');

// Quality metrics (Stage 11)
export const getQualityMetrics = () =>
  apiFetch<Record<string, unknown>>('/metrics/quality');

export const getOperationalMetrics = () =>
  apiFetch<Record<string, unknown>>('/metrics/operational');

export const getAutonomyCandidates = () =>
  apiFetch<Record<string, unknown>[]>('/metrics/autonomy-candidates');

export const getSystemHealth = () =>
  apiFetch<Record<string, unknown>>('/system/health');

// Knowledge (Stage 12)
export const knowledgeSearch = (query: string, filters?: Record<string, string>) => {
  const params = new URLSearchParams({ q: query, ...filters });
  return apiFetch<Incident[]>(`/knowledge/search?${params}`);
};

export const getKnowledgeIncident = (id: string) =>
  apiFetch<Incident>(`/knowledge/incidents/${id}`);

export const addAnnotation = (id: string, body: Record<string, unknown>) =>
  apiFetch<unknown>(`/knowledge/incidents/${id}/annotations`, {
    method: 'POST',
    body: JSON.stringify(body),
  });

export const getKnowledgePatterns = () =>
  apiFetch<Pattern[]>('/knowledge/patterns');

// Autonomy (Stage 13)
export const getAutonomyTiers = () =>
  apiFetch<Record<string, unknown>[]>('/autonomy/tiers');

export const toggleKillSwitch = (enabled: boolean) =>
  apiFetch<unknown>('/autonomy/kill-switch', {
    method: 'POST',
    body: JSON.stringify({ enabled }),
  });
