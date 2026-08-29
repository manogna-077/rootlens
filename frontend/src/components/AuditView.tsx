import React, { useEffect, useState } from 'react';
import { AuditEvent } from '../types';
import { api } from '../services/api';

interface AuditViewProps {
  incidentId: string;
}

export const AuditView: React.FC<AuditViewProps> = ({ incidentId }) => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    setLoading(true);
    api.getAudit(incidentId)
      .then((data) => {
        setEvents(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load audit events', err);
        setLoading(false);
      });
  }, [incidentId]);

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-400">
        Loading Audit Trail for {incidentId}...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-lg shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <span>Audit Trail & Provenance Log</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Verifiable, deterministic execution log for incident {incidentId}.
          </p>
        </div>
        <span className="text-xs font-mono bg-slate-950 text-slate-300 px-3 py-1.5 rounded border border-slate-800 self-start md:self-auto">
          Total Audit Records: {events.length}
        </span>
      </div>

      <div className="bg-slate-900/80 border border-slate-800 rounded-lg overflow-hidden shadow-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-950 border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold">
                <th className="p-3">Event ID</th>
                <th className="p-3">Timestamp</th>
                <th className="p-3">Actor</th>
                <th className="p-3">Action</th>
                <th className="p-3">Payload Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {events.map((evt) => (
                <tr key={evt.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="p-3 text-indigo-400 font-bold">{evt.id}</td>
                  <td className="p-3 text-slate-300">{new Date(evt.timestamp).toLocaleString()}</td>
                  <td className="p-3">
                    <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                      evt.actor.includes('AGENT')
                        ? 'bg-purple-950 text-purple-300 border border-purple-800'
                        : evt.actor.includes('VERIFIER')
                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        : 'bg-slate-800 text-slate-300'
                    }`}>
                      {evt.actor}
                    </span>
                  </td>
                  <td className="p-3 text-slate-100 font-semibold">{evt.action}</td>
                  <td className="p-3 text-slate-400 max-w-md truncate">
                    <pre className="text-[11px] bg-slate-950 p-1.5 rounded border border-slate-900 overflow-x-auto text-slate-300 font-mono">
                      {JSON.stringify(evt.details, null, 2)}
                    </pre>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
