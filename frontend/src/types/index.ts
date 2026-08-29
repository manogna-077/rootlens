/**
 * RootLens Shared Types matching docs/shared-schemas.md and docs/api-contract.md
 */

export interface Incident {
  id: string;
  title: string;
  description: string;
  status: 'OPEN' | 'INVESTIGATING' | 'RESOLVED' | 'CLOSED';
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  created_at: string;
  services_affected?: string[];
  time_window?: {
    start: string;
    end: string;
  };
}

export interface Evidence {
  id: string;
  incident_id: string;
  timestamp: string;
  source: string;
  event_type: string;
  service: string;
  version?: string;
  observation: string;
  metadata?: Record<string, unknown>;
  provenance?: string;
}

export interface Hypothesis {
  id: string;
  statement: string;
  status: 'GENERATED' | 'SUPPORTED' | 'DISCONFIRMED' | 'CONFIRMED' | 'REJECTED';
  score: number;
  supporting_evidence_ids: string[];
  contradicting_evidence_ids: string[];
  missing_evidence: string[];
  disconfirming_condition?: string;
  reasoning?: string;
}

export interface AgentAction {
  tool: string;
  arguments: Record<string, unknown>;
  reason: string;
  target_hypotheses?: string[];
  missing_evidence_addressed?: string[];
}

export interface ToolResult {
  tool: string;
  status: 'SUCCESS' | 'FAILURE' | 'PENDING';
  evidence_ids: string[];
  observations: string[];
  provenance: string[];
}

export interface AuditEvent {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  details: Record<string, unknown>;
}

export interface InvestigationState {
  incident: Incident;
  goal: string;
  time_window: {
    start: string;
    end: string;
  };
  iteration: number;
  actions_taken: AgentAction[];
  evidence_ids: string[];
  hypotheses: Hypothesis[];
  observations: string[];
  missing_evidence: string[];
  candidate_actions: AgentAction[];
  selected_action?: AgentAction;
  action_reason?: string;
  evidence_score?: number;
  verification_status?: 'NOT_STARTED' | 'PASS' | 'FAIL';
  status: 'IN_PROGRESS' | 'COMPLETED' | 'WAITING_FOR_HUMAN' | 'FAILED';
  audit_events: AuditEvent[];
}

export interface Report {
  incident_id: string;
  title: string;
  generated_at: string;
  summary: string;
  root_cause: string;
  contributing_factors: string[];
  supporting_evidence: Evidence[];
  timeline_summary: string[];
  recommended_actions: string[];
  verification_status: string;
  human_approved: boolean;
  approval_comment?: string;
}

export type ViewType = 'incident-command' | 'investigation-console' | 'final-report' | 'audit';
