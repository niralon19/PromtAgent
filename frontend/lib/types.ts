// TypeScript types mirroring backend Pydantic models

export type Severity = 'critical' | 'warning' | 'info';
export type IncidentStatus = 'open' | 'investigating' | 'resolved' | 'false_positive' | 'acknowledged';
export type IncidentCategory = 'physical' | 'data_integrity' | 'coupling';

export interface Alert {
  id: string;
  alertname: string;
  severity: Severity;
  value: number | null;
  annotations: Record<string, string>;
  labels: Record<string, string>;
  status: string;
  starts_at: string;
  ends_at: string | null;
  fingerprint: string;
  generator_url: string | null;
  created_at: string;
}

export interface Evidence {
  claim: string;
  source_tool: string;
  source_output_ref: string;
  strength: 'weak' | 'moderate' | 'strong';
}

export interface Alternative {
  hypothesis: string;
  why_rejected: string;
  evidence_against: string[];
}

export interface SuggestedAction {
  action_key: string;
  parameters: Record<string, unknown>;
  rationale: string;
  estimated_risk: string;
  requires_approval: boolean;
  tier: number;
}

export interface InvestigationResult {
  hypothesis: string;
  confidence: number;
  confidence_rationale: string;
  suggested_action: SuggestedAction;
  evidence_chain: Evidence[];
  alternatives_considered: Alternative[];
  tools_executed_summary: string[];
  iterations_used: number;
  cost_usd: number;
  duration_seconds: number;
  checklist_completion: Record<string, boolean>;
  completed_at: string;
}

export interface Incident {
  id: string;
  hostname: string;
  category: IncidentCategory;
  status: IncidentStatus;
  fingerprint: string | null;
  parent_incident_id: string | null;
  hypothesis: string | null;
  confidence: number | null;
  suggested_action_key: string | null;
  resolution_category: string | null;
  resolution_details: string | null;
  was_hypothesis_correct: boolean | null;
  resolution_time_minutes: number | null;
  tags: string[];
  enrichment: Record<string, unknown> | null;
  investigation: InvestigationResult | null;
  created_at: string;
  updated_at: string;
  alert: Alert | null;
}

export interface AgentRun {
  id: string;
  incident_id: string;
  started_at: string;
  completed_at: string | null;
  iterations: number | null;
  cost_usd: number | null;
  model: string | null;
  status: 'running' | 'completed' | 'failed';
  error: string | null;
}

export interface SimilarIncident {
  id: string;
  hostname: string;
  category: string;
  similarity_score: number;
  resolution_category: string | null;
  was_hypothesis_correct: boolean | null;
}

export interface BaselineAnalysis {
  z_score: number;
  severity_level: string;
  is_anomaly: boolean;
  baseline_mean: number | null;
  baseline_std: number | null;
}

export interface ActionMetric {
  action_key: string;
  total_uses: number;
  correct_uses: number;
  avg_resolution_minutes: number | null;
  last_used_at: string | null;
  accuracy_pct: number;
}

export interface HostMetric {
  hostname: string;
  total_incidents: number;
  open_incidents: number;
  avg_resolution_minutes: number | null;
  most_common_category: string | null;
  last_incident_at: string | null;
}

export interface Pattern {
  hostname: string;
  category: string;
  count: number;
  last_seen: string | null;
  common_action: string | null;
}

// WebSocket event types
export type WSEventType =
  | 'incident.created'
  | 'incident.updated'
  | 'incident.resolved'
  | 'investigation.started'
  | 'investigation.completed'
  | 'tool.executed';

export interface WSEvent<T = unknown> {
  event: WSEventType;
  data: T;
  timestamp: string;
}
