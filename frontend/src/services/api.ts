import { Incident, Evidence, Hypothesis, InvestigationState, Report, AuditEvent, CausalGraphData } from '../types';
import {
  mockIncidents,
  mockEvidences,
  mockHypotheses,
  mockInvestigationState,
  mockReport,
  mockAuditEvents,
  mockCausalGraph
} from '../data/mockData';

const API_BASE_URL = '/api';
const backendIncidentId = (id: string): string =>
  id === 'INC-2026-001' ? 'scenario_a' : id;

async function fetchJson<T>(url: string, options?: RequestInit, fallback?: T): Promise<T> {
  try {
    const response = await fetch(url, options);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    if (fallback !== undefined) {
      return fallback;
    }
    throw error;
  }
}

export const api = {
  getHealth: async (): Promise<{ status: string }> => {
    return fetchJson(`${API_BASE_URL}/health`, undefined, { status: 'ok' });
  },

  getIncidents: async (): Promise<Incident[]> => {
    return fetchJson(`${API_BASE_URL}/incidents`, undefined, mockIncidents);
  },

  getIncidentById: async (id: string): Promise<Incident> => {
    const fallback = mockIncidents.find((i) => i.id === id) || mockIncidents[0];
    return fetchJson(`${API_BASE_URL}/incidents/${id}`, undefined, fallback);
  },

  getEvidence: async (id: string): Promise<Evidence[]> => {
    return fetchJson(`${API_BASE_URL}/incidents/${id}/evidence`, undefined, mockEvidences);
  },

  getTimeline: async (id: string): Promise<Evidence[]> => {
    return fetchJson(`${API_BASE_URL}/incidents/${id}/timeline`, undefined, mockEvidences);
  },

  startInvestigation: async (id: string): Promise<InvestigationState> => {
    return fetchJson(
      `${API_BASE_URL}/incidents/${id}/investigate`,
      { method: 'POST' },
      mockInvestigationState
    );
  },

  getInvestigation: async (id: string): Promise<InvestigationState> => {
    return fetchJson(`${API_BASE_URL}/incidents/${id}/investigation`, undefined, mockInvestigationState);
  },

  getHypotheses: async (id: string): Promise<Hypothesis[]> => {
    return fetchJson(`${API_BASE_URL}/incidents/${id}/hypotheses`, undefined, mockHypotheses);
  },

  getReport: async (id: string): Promise<Report> => {
    return fetchJson(`${API_BASE_URL}/incidents/${id}/report`, undefined, mockReport);
  },

getAudit: async (id: string): Promise<AuditEvent[]> => {
  return fetchJson(
    `${API_BASE_URL}/incidents/${backendIncidentId(id)}/audit`,
    undefined,
    mockAuditEvents
  );
},

  getGraph: async (id: string): Promise<CausalGraphData> => {
    return fetchJson(`${API_BASE_URL}/incidents/${id}/graph`, undefined, mockCausalGraph);
  },

  submitApproval: async (id: string, approved: boolean, comment?: string): Promise<{ success: boolean }> => {
    return fetchJson(
      `${API_BASE_URL}/incidents/${backendIncidentId(id)}/approval`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved, comments: comment })
      },
      { success: true }
    );
  }
};
