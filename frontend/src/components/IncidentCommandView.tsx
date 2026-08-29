import React, { useEffect, useState } from 'react';
import { Incident } from '../types';
import { api } from '../services/api';

interface IncidentCommandViewProps {
  onSelectIncident: (incidentId: string) => void;
}

export const IncidentCommandView: React.FC<IncidentCommandViewProps> = ({ onSelectIncident }) => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');

  useEffect(() => {
    api.getIncidents()
      .then((data) => {
        setIncidents(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load incidents', err);
        setLoading(false);
      });
  }, []);

  const filteredIncidents = incidents.filter((incident) => {
    if (selectedCategory === 'ALL') return true;
    return incident.status === selectedCategory;
  });

  const getSeverityBadgeClass = (severity: Incident['severity']) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-red-950 text-red-300 border border-red-800';
      case 'HIGH':
        return 'bg-orange-950 text-orange-300 border border-orange-800';
      case 'MEDIUM':
        return 'bg-yellow-950 text-yellow-300 border border-yellow-800';
      case 'LOW':
        return 'bg-blue-950 text-blue-300 border border-blue-800';
      default:
        return 'bg-slate-800 text-slate-300';
    }
  };

  const getStatusBadgeClass = (status: Incident['status']) => {
    switch (status) {
      case 'INVESTIGATING':
        return 'bg-purple-950 text-purple-300 border border-purple-800 animate-pulse';
      case 'OPEN':
        return 'bg-amber-950 text-amber-300 border border-amber-800';
      case 'RESOLVED':
        return 'bg-emerald-950 text-emerald-300 border border-emerald-800';
      case 'CLOSED':
        return 'bg-slate-900 text-slate-400 border border-slate-700';
      default:
        return 'bg-slate-800 text-slate-300';
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-400">
        Loading Incident Command Center...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 bg-slate-900/90 border border-slate-800 rounded-lg shadow-lg">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <span className="inline-block w-3 h-3 bg-red-500 rounded-full animate-ping"></span>
            Incident Command Center
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time automated root cause analysis & active incident triage dashboard.
          </p>
        </div>

        {/* Category Filters */}
        <div className="flex items-center gap-2 bg-slate-950 p-1 rounded-md border border-slate-800">
          {['ALL', 'INVESTIGATING', 'OPEN', 'RESOLVED'].map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                selectedCategory === cat
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-lg">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Active Incidents</div>
          <div className="text-2xl font-bold text-slate-100 mt-1">{incidents.length}</div>
        </div>
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-lg">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Currently Investigating</div>
          <div className="text-2xl font-bold text-purple-400 mt-1">
            {incidents.filter((i) => i.status === 'INVESTIGATING').length}
          </div>
        </div>
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-lg">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Critical Severity</div>
          <div className="text-2xl font-bold text-red-400 mt-1">
            {incidents.filter((i) => i.severity === 'CRITICAL').length}
          </div>
        </div>
        <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-lg">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Resolved Today</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">
            {incidents.filter((i) => i.status === 'RESOLVED').length}
          </div>
        </div>
      </div>

      {/* Incident List */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-slate-200">Incident Feed</h2>
        {filteredIncidents.map((incident) => (
          <div
            key={incident.id}
            className="p-5 bg-slate-900/80 border border-slate-800 hover:border-indigo-500/50 transition-all rounded-lg shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4"
          >
            <div className="space-y-2 max-w-2xl">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-900">
                  {incident.id}
                </span>
                <span className={`px-2 py-0.5 rounded text-xs font-bold ${getSeverityBadgeClass(incident.severity)}`}>
                  {incident.severity}
                </span>
                <span className={`px-2 py-0.5 rounded text-xs font-bold ${getStatusBadgeClass(incident.status)}`}>
                  {incident.status}
                </span>
                <span className="text-xs text-slate-500">
                  Created: {new Date(incident.created_at).toLocaleTimeString()}
                </span>
              </div>

              <h3 className="text-base font-semibold text-slate-100">{incident.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{incident.description}</p>

              {incident.services_affected && incident.services_affected.length > 0 && (
                <div className="flex items-center gap-2 pt-1">
                  <span className="text-xs text-slate-500 font-medium">Affected Services:</span>
                  <div className="flex gap-1.5 flex-wrap">
                    {incident.services_affected.map((service) => (
                      <span
                        key={service}
                        className="text-xs font-mono bg-slate-950 text-slate-300 px-2 py-0.5 rounded border border-slate-800"
                      >
                        {service}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center gap-3 self-end md:self-center">
              <button
                onClick={() => onSelectIncident(incident.id)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm rounded shadow transition-colors flex items-center gap-2"
              >
                <span>Launch Console</span>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
