import { Incident, InvestigationState, Evidence, Hypothesis, Report, AuditEvent, AgentAction, ToolResult } from '../types';

export interface HypothesisChange {
  hypothesis_id: string;
  statement: string;
  previous_status: Hypothesis['status'];
  new_status: Hypothesis['status'];
  previous_score: number;
  new_score: number;
  reasoning?: string;
  added_evidence_ids?: string[];
}

export interface IterationTraceStep {
  iteration: number;
  timestamp: string;
  hypotheses: Hypothesis[];
  selected_action: AgentAction;
  reason: string;
  tool_result: ToolResult;
  hypothesis_changes: HypothesisChange[];
  next_action?: AgentAction;
}

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

export const mockTraceSteps: IterationTraceStep[] = [
  {
    iteration: 1,
    timestamp: '2026-08-29T14:15:30Z',
    hypotheses: [
      {
        id: 'HYP-01',
        statement: 'Unindexed query introduced in payment-service v2.4.1 is holding DB connection locks under load.',
        status: 'GENERATED',
        score: 0.40,
        supporting_evidence_ids: [],
        contradicting_evidence_ids: [],
        missing_evidence: ['Latency breakdown by endpoint', 'DB active connections'],
        disconfirming_condition: 'DB connection count remains normal after rolling back v2.4.1.',
        reasoning: 'Initial alert triggered due to p99 latency spike on checkout pipeline.'
      },
      {
        id: 'HYP-02',
        statement: 'Upstream payment gateway provider degradation causing socket connection pooling backup.',
        status: 'GENERATED',
        score: 0.30,
        supporting_evidence_ids: [],
        contradicting_evidence_ids: [],
        missing_evidence: ['External gateway health metrics'],
        disconfirming_condition: 'External gateway latency is within normal SLA range.',
        reasoning: 'Third-party gateway latency spikes can cascade into checkout timeouts.'
      }
    ],
    selected_action: {
      tool: 'query_metrics',
      arguments: { service: 'payment-service', metric: 'http_request_duration_seconds', time_window: '1h' },
      reason: 'Analyze p99 latency spike and 504 gateway timeout distribution across payment service endpoints post v2.4.1 deployment.',
      target_hypotheses: ['HYP-01', 'HYP-02'],
      missing_evidence_addressed: ['Latency breakdown by endpoint']
    },
    reason: 'Analyze p99 latency spike and 504 gateway timeout distribution across payment service endpoints post v2.4.1 deployment.',
    tool_result: {
      tool: 'query_metrics',
      status: 'SUCCESS',
      evidence_ids: ['EVD-101'],
      observations: ['HTTP 504 Gateway Timeout rate increased to 12.4% on /api/v1/charge (p99: 4500ms vs baseline 220ms).'],
      provenance: ['prometheus:query:http_request_duration_seconds']
    },
    hypothesis_changes: [
      {
        hypothesis_id: 'HYP-01',
        statement: 'Unindexed query introduced in payment-service v2.4.1 is holding DB connection locks under load.',
        previous_status: 'GENERATED',
        new_status: 'GENERATED',
        previous_score: 0.40,
        new_score: 0.60,
        reasoning: 'Latency spike is concentrated on /api/v1/charge which executes primary payment DB queries.',
        added_evidence_ids: ['EVD-101']
      },
      {
        hypothesis_id: 'HYP-02',
        statement: 'Upstream payment gateway provider degradation causing socket connection pooling backup.',
        previous_status: 'GENERATED',
        new_status: 'GENERATED',
        previous_score: 0.30,
        new_score: 0.35,
        reasoning: 'Gateway timeout correlates with /api/v1/charge latency, but upstream status remains unverified.',
        added_evidence_ids: ['EVD-101']
      }
    ],
    next_action: {
      tool: 'inspect_db_connections',
      arguments: { db_instance: 'db-primary', metric: 'active_connections' },
      reason: 'Check if /api/v1/charge timeouts coincide with database connection pool saturation on db-primary.',
      target_hypotheses: ['HYP-01'],
      missing_evidence_addressed: ['DB active connections']
    }
  },
  {
    iteration: 2,
    timestamp: '2026-08-29T14:18:45Z',
    hypotheses: [
      {
        id: 'HYP-01',
        statement: 'Unindexed query introduced in payment-service v2.4.1 is holding DB connection locks under load.',
        status: 'GENERATED',
        score: 0.60,
        supporting_evidence_ids: ['EVD-101'],
        contradicting_evidence_ids: [],
        missing_evidence: ['DB active connections', 'EXPLAIN ANALYZE slow query log output from db-primary'],
        disconfirming_condition: 'DB connection count remains normal after rolling back v2.4.1.',
        reasoning: 'High correlation between /api/v1/charge timeouts and deployment v2.4.1.'
      },
      {
        id: 'HYP-02',
        statement: 'Upstream payment gateway provider degradation causing socket connection pooling backup.',
        status: 'GENERATED',
        score: 0.35,
        supporting_evidence_ids: ['EVD-101'],
        contradicting_evidence_ids: [],
        missing_evidence: ['External gateway health check metrics'],
        disconfirming_condition: 'External gateway latency is within normal SLA range.',
        reasoning: 'Upstream issue remains candidate until DB connection status is confirmed.'
      }
    ],
    selected_action: {
      tool: 'inspect_db_connections',
      arguments: { db_instance: 'db-primary', metric: 'active_connections' },
      reason: 'Verify DB connection pool exhaustion on db-primary and check deployment timestamp correlation.',
      target_hypotheses: ['HYP-01'],
      missing_evidence_addressed: ['DB active connections']
    },
    reason: 'Verify DB connection pool exhaustion on db-primary and check deployment timestamp correlation.',
    tool_result: {
      tool: 'inspect_db_connections',
      status: 'SUCCESS',
      evidence_ids: ['EVD-102', 'EVD-103'],
      observations: [
        'Deployment rollout completed for payment-service v2.4.1.',
        'PostgreSQL active connection pool reached maximum limit (100/100) on db-primary.'
      ],
      provenance: ['k8s:deployment:payment-service', 'datadog:logs:service:db-primary']
    },
    hypothesis_changes: [
      {
        hypothesis_id: 'HYP-01',
        statement: 'Unindexed query introduced in payment-service v2.4.1 is holding DB connection locks under load.',
        previous_status: 'GENERATED',
        new_status: 'SUPPORTED',
        previous_score: 0.60,
        new_score: 0.85,
        reasoning: 'Deployment v2.4.1 directly coincides with DB connection pool saturation (100/100).',
        added_evidence_ids: ['EVD-102', 'EVD-103']
      },
      {
        hypothesis_id: 'HYP-02',
        statement: 'Upstream payment gateway provider degradation causing socket connection pooling backup.',
        previous_status: 'GENERATED',
        new_status: 'DISCONFIRMED',
        previous_score: 0.35,
        new_score: 0.15,
        reasoning: 'Internal DB connection pool saturation indicates local database bottleneck rather than external gateway wait.',
        added_evidence_ids: []
      }
    ],
    next_action: {
      tool: 'explain_slow_queries',
      arguments: { database: 'db-primary', query_pattern: 'SELECT * FROM transactions WHERE customer_id = ?' },
      reason: 'Execute query plan analysis to confirm missing index on transactions table in v2.4.1.',
      target_hypotheses: ['HYP-01'],
      missing_evidence_addressed: ['EXPLAIN ANALYZE slow query log output from db-primary']
    }
  },
  {
    iteration: 3,
    timestamp: '2026-08-29T14:22:10Z',
    hypotheses: [
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
        status: 'DISCONFIRMED',
        score: 0.15,
        supporting_evidence_ids: ['EVD-101'],
        contradicting_evidence_ids: ['EVD-103'],
        missing_evidence: ['External gateway health check metrics'],
        disconfirming_condition: 'External gateway latency is within normal SLA range.',
        reasoning: 'External gateway issues usually produce socket timeout errors rather than internal DB connection pool saturation.'
      }
    ],
    selected_action: {
      tool: 'verify_hypothesis',
      arguments: { hypothesis_id: 'HYP-01', verification_checks: ['explain_analyze', 'index_lookup'] },
      reason: 'Confirm missing index on transaction table in payment-service v2.4.1 before recommending index creation and rollback.',
      target_hypotheses: ['HYP-01'],
      missing_evidence_addressed: ['EXPLAIN ANALYZE slow query log output from db-primary']
    },
    reason: 'Confirm missing index on transaction table in payment-service v2.4.1 before recommending index creation and rollback.',
    tool_result: {
      tool: 'verify_hypothesis',
      status: 'SUCCESS',
      evidence_ids: ['EVD-101', 'EVD-102', 'EVD-103'],
      observations: [
        'EXPLAIN ANALYZE confirms Sequential Scan on transactions table without index on customer_id.',
        'Average lock duration 3.8s per transaction under load.'
      ],
      provenance: ['postgres:pg_stat_statements:db-primary']
    },
    hypothesis_changes: [
      {
        hypothesis_id: 'HYP-01',
        statement: 'Unindexed query introduced in payment-service v2.4.1 is holding DB connection locks under load.',
        previous_status: 'SUPPORTED',
        new_status: 'CONFIRMED',
        previous_score: 0.85,
        new_score: 0.95,
        reasoning: 'Query plan verification confirms full table scan due to missing index on customer_id.',
        added_evidence_ids: []
      },
      {
        hypothesis_id: 'HYP-02',
        statement: 'Upstream payment gateway provider degradation causing socket connection pooling backup.',
        previous_status: 'DISCONFIRMED',
        new_status: 'REJECTED',
        previous_score: 0.15,
        new_score: 0.05,
        reasoning: 'Root cause confirmed as internal DB index omission in release v2.4.1.',
        added_evidence_ids: []
      }
    ],
    next_action: {
      tool: 'generate_final_report',
      arguments: { incident_id: 'INC-2026-001', recommended_action: 'Add composite index on transaction(customer_id, created_at) and rollback v2.4.1' },
      reason: 'Finalize investigation report and submit mitigation recommendations for human approval.',
      target_hypotheses: ['HYP-01']
    }
  }
];

export const mockInvestigationState: InvestigationState = {
  incident: mockIncidents[0],
  goal: 'Identify root cause of p99 latency spike in payment-service',
  time_window: {
    start: '2026-08-29T14:00:00Z',
    end: '2026-08-29T15:00:00Z'
  },
  iteration: 3,
  actions_taken: [
    mockTraceSteps[0].selected_action,
    mockTraceSteps[1].selected_action
  ],
  evidence_ids: ['EVD-101', 'EVD-102', 'EVD-103'],
  hypotheses: [
    {
      id: 'HYP-01',
      statement: 'Unindexed query introduced in payment-service v2.4.1 is holding DB connection locks under load.',
      status: 'CONFIRMED',
      score: 0.95,
      supporting_evidence_ids: ['EVD-101', 'EVD-102', 'EVD-103'],
      contradicting_evidence_ids: [],
      missing_evidence: [],
      disconfirming_condition: 'DB connection count remains normal after rolling back v2.4.1 or query execution time is <10ms.',
      reasoning: 'EXPLAIN ANALYZE confirmed sequential scan without index on customer_id causing connection pool exhaustion.'
    },
    {
      id: 'HYP-02',
      statement: 'Upstream payment gateway provider degradation causing socket connection pooling backup.',
      status: 'REJECTED',
      score: 0.05,
      supporting_evidence_ids: ['EVD-101'],
      contradicting_evidence_ids: ['EVD-103'],
      missing_evidence: [],
      disconfirming_condition: 'External gateway latency is within normal SLA range.',
      reasoning: 'Root cause identified as internal DB query lock rather than external gateway degradation.'
    }
  ],
  observations: [
    'HTTP 504 Gateway Timeout rate elevated on /api/v1/charge.',
    'Deployment rollout completed for payment-service v2.4.1.',
    'DB connection pool exhausted on db-primary (100/100 connections).',
    'EXPLAIN ANALYZE confirmed sequential scan on transactions table without index on customer_id.'
  ],
  missing_evidence: [],
  candidate_actions: [mockTraceSteps[2].next_action!],
  selected_action: mockTraceSteps[2].selected_action,
  action_reason: mockTraceSteps[2].reason,
  evidence_score: 0.95,
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
