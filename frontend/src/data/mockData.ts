import { Incident, InvestigationState, Evidence, Hypothesis, Report, AuditEvent } from '../types';

export const mockIncidents: Incident[] = [
  {
    id: 'INC-2026-001',
    title: 'High Latency Spike in Payment Checkout Pipeline',
    description: 'Elevated p99 latency observed across payment-service and checkout-gateway following deployment v2.4.1.',
    status: 'INVESTIGATING',
    severity: 'CRITICAL',
    created_at: '2026-08-29T14:22:00Z',
    services_affected: ['payment-service', 'checkout-gateway', 'db-primary'],
    time_window: {
      start: '2026-08-29T14:00:00Z',
      end: '2026-08-29T15:00:00Z'
    }
  },
  {
    id: 'INC-2026-002',
    title: 'Authentication Token Validation Failures',
    description: 'User login sessions dropping intermittently due to key rotation timeout in auth-service.',
    status: 'OPEN',
    severity: 'HIGH',
    created_at: '2026-08-29T13:10:00Z',
    services_affected: ['auth-service', 'user-api'],
    time_window: {
      start: '2026-08-29T13:00:00Z',
      end: '2026-08-29T14:00:00Z'
    }
  },
  {
    id: 'INC-2026-003',
    title: 'Inventory Sync Queue Backlog',
    description: 'Kafka partition lag on inventory-events topic causing stale stock availability in storefront.',
    status: 'RESOLVED',
    severity: 'MEDIUM',
    created_at: '2026-08-29T10:00:00Z',
    services_affected: ['inventory-service', 'kafka-cluster'],
    time_window: {
      start: '2026-08-29T09:30:00Z',
      end: '2026-08-29T11:00:00Z'
    }
  }
];

export const mockEvidences: Evidence[] = [
  {
    id: 'EVD-101',
    incident_id: 'INC-2026-001',
    timestamp: '2026-08-29T14:15:00Z',
    source: 'metrics-prometheus',
    event_type: 'LATENCY_SPIKE',
    service: 'payment-service',
    version: 'v2.4.1',
    observation: 'HTTP 504 Gateway Timeout rate increased to 12.4% on /api/v1/charge.',
    metadata: { p99_ms: 4500, baseline_p99_ms: 220 },
    provenance: 'prometheus:query:http_request_duration_seconds'
  },
  {
    id: 'EVD-102',
    incident_id: 'INC-2026-001',
    timestamp: '2026-08-29T14:12:00Z',
    source: 'deployment-log',
    event_type: 'DEPLOYMENT',
    service: 'payment-service',
    version: 'v2.4.1',
    observation: 'Deployment rollout completed for payment-service v2.4.1.',
    metadata: { deployed_by: 'cd-pipeline', commit_sha: 'a1b2c3d' },
    provenance: 'k8s:deployment:payment-service'
  },
  {
    id: 'EVD-103',
    incident_id: 'INC-2026-001',
    timestamp: '2026-08-29T14:18:00Z',
    source: 'logs-datadog',
    event_type: 'DB_CONNECTION_EXHAUSTION',
    service: 'db-primary',
    observation: 'PostgreSQL active connection pool reached maximum limit (100/100).',
    metadata: { max_connections: 100, active_connections: 100 },
    provenance: 'datadog:logs:service:db-primary'
  }
];

export const mockHypotheses: Hypothesis[] = [
  {
    id: 'HYP-01',
    statement: 'Unindexed query introduced in payment-service v2.4.1 is holding DB connection locks under load.',
    status: 'SUPPORTED',
    score: 0.85,
    supporting_evidence_ids: ['EVD-101', 'EVD-102', 'EVD-103'],
    contradicting_evidence_ids: [],
    missing_evidence: ['EXPLAIN ANALYZE slow query log output from db-primary'],
    disconfirming_condition: 'DB connection count remains normal after rolling back v2.4.1 or query execution time is <10ms.',
    reasoning: 'Deployment of v2.4.1 coincides directly with DB connection pool exhaustion and API 504 timeouts.'
  },
  {
    id: 'HYP-02',
    statement: 'Upstream payment gateway provider degradation causing socket connection pooling backup.',
    status: 'GENERATED',
    score: 0.30,
    supporting_evidence_ids: ['EVD-101'],
    contradicting_evidence_ids: ['EVD-103'],
    missing_evidence: ['External gateway health check metrics'],
    disconfirming_condition: 'External gateway latency is within normal SLA range.',
    reasoning: 'External gateway issues usually produce socket timeout errors rather than internal DB connection pool saturation.'
  }
];

export const mockAuditEvents: AuditEvent[] = [
  {
    id: 'AUD-001',
    timestamp: '2026-08-29T14:22:05Z',
    actor: 'SYSTEM_TRIGGER',
    action: 'INCIDENT_CREATED',
    details: { incident_id: 'INC-2026-001', source: 'PagerDuty Alert' }
  },
  {
    id: 'AUD-002',
    timestamp: '2026-08-29T14:22:10Z',
    actor: 'ROOTLENS_AGENT',
    action: 'INVESTIGATION_STARTED',
    details: { goal: 'Identify root cause of p99 latency spike in payment-service' }
  },
  {
    id: 'AUD-003',
    timestamp: '2026-08-29T14:23:45Z',
    actor: 'VERIFIER',
    action: 'HYPOTHESIS_EVALUATED',
    details: { hypothesis_id: 'HYP-01', score: 0.85, verification_status: 'PASS' }
  }
];

export const mockInvestigationState: InvestigationState = {
  incident: mockIncidents[0],
  goal: 'Identify root cause of p99 latency spike in payment-service',
  time_window: {
    start: '2026-08-29T14:00:00Z',
    end: '2026-08-29T15:00:00Z'
  },
  iteration: 1,
  actions_taken: [],
  evidence_ids: ['EVD-101', 'EVD-102', 'EVD-103'],
  hypotheses: mockHypotheses,
  observations: [
    'HTTP 504 Gateway Timeout rate elevated on /api/v1/charge.',
    'DB connection pool exhausted on db-primary.'
  ],
  missing_evidence: ['EXPLAIN ANALYZE query plan for payment-service DB queries'],
  candidate_actions: [],
  evidence_score: 0.85,
  verification_status: 'PASS',
  status: 'IN_PROGRESS',
  audit_events: mockAuditEvents
};

export const mockReport: Report = {
  incident_id: 'INC-2026-001',
  title: 'RootLens Final Investigation Report - INC-2026-001',
  generated_at: '2026-08-29T14:25:00Z',
  summary: 'Investigation identified high latency and 504 timeouts on payment-service following deployment v2.4.1.',
  root_cause: 'Pending verification: Unindexed DB query introduced in release v2.4.1 exhausting connection pool.',
  contributing_factors: [
    'Deployment v2.4.1 introduced unindexed query on transaction table.',
    'PostgreSQL connection pool max limit reached (100 connections).'
  ],
  supporting_evidence: mockEvidences,
  timeline_summary: [
    '14:12:00Z - Deployment v2.4.1 completed on payment-service.',
    '14:15:00Z - Latency spike detected by Prometheus monitor.',
    '14:18:00Z - Database connection pool exhaustion logged.'
  ],
  recommended_actions: [
    'Add composite index on transaction(customer_id, created_at).',
    'Rollback payment-service deployment v2.4.1 to restore baseline performance.',
    'Increase connection pool monitoring alert sensitivity.'
  ],
  verification_status: 'PASS',
  human_approved: false
};
