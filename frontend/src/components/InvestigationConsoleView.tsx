import React, { useEffect, useState } from 'react';
import { InvestigationState } from '../types';
import { api } from '../services/api';

interface InvestigationConsoleViewProps {
  incidentId: string;
}

export const InvestigationConsoleView: React.FC<InvestigationConsoleViewProps> = ({ incidentId }) => {
  const [state, setState] = useState<InvestigationState | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<'hypotheses' | 'evidence' | 'missing'>('hypotheses');

  useEffect(() => {
    setLoading(true);
    api.getInvestigation(incidentId)
      .then((data) => {
        setState(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load investigation state', err);
        setLoading(false);
      });
  }, [incidentId]);

  if (loading || !state) {
    return (
      <div className="p-8 text-center text-slate-400">
        Loading Investigation Console for {incidentId}...
      </div>
    );
  }

  const { incident, hypotheses, observations, missing_evidence, verification_status, status, iteration, goal } = state;

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-lg shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono bg-indigo-950 text-indigo-300 border border-indigo-800 px-2 py-0.5 rounded">
                {incident.id}
              </span>
              <span className="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded font-mono">
                Iteration #{iteration}
              </span>
              <span className={`text-xs px-2 py-0.5 rounded font-bold ${
                verification_status === 'PASS'
                  ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                  : 'bg-amber-950 text-amber-300 border border-amber-800'
              }`}>
                Verification: {verification_status || 'IN_PROGRESS'}
              </span>
            </div>
            <h1 className="text-xl font-bold text-slate-100 mt-2">{incident.title}</h1>
            <p className="text-sm text-slate-400 mt-1">Goal: {goal}</p>
          </div>

          <div className="flex items-center gap-3">
            <span className={`px-3 py-1 rounded text-xs font-bold border ${
              status === 'COMPLETED'
                ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                : 'bg-purple-950 text-purple-300 border-purple-800 animate-pulse'
            }`}>
              {status}
            </span>
          </div>
        </div>
      </div>

      {/* Main Console Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Columns: Tabs for Hypotheses / Evidence / Missing */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex border-b border-slate-800 gap-2">
            <button
              onClick={() => setActiveTab('hypotheses')}
              className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors ${
                activeTab === 'hypotheses'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Hypotheses ({hypotheses.length})
            </button>
            <button
              onClick={() => setActiveTab('evidence')}
              className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors ${
                activeTab === 'evidence'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Observations & Evidence ({observations.length})
            </button>
            <button
              onClick={() => setActiveTab('missing')}
              className={`pb-3 px-4 text-sm font-semibold border-b-2 transition-colors ${
                activeTab === 'missing'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              Missing Evidence ({missing_evidence.length})
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === 'hypotheses' && (
            <div className="space-y-4">
              {hypotheses.map((hyp) => (
                <div
                  key={hyp.id}
                  className="p-5 bg-slate-900/70 border border-slate-800 rounded-lg space-y-3"
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-indigo-400 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                        {hyp.id}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded font-bold ${
                        hyp.status === 'SUPPORTED' || hyp.status === 'CONFIRMED'
                          ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                          : hyp.status === 'DISCONFIRMED' || hyp.status === 'REJECTED'
                          ? 'bg-red-950 text-red-300 border border-red-800'
                          : 'bg-slate-800 text-slate-300'
                      }`}>
                        {hyp.status}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-400">Score:</span>
                      <div className="w-24 bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                        <div
                          className="bg-indigo-500 h-full rounded-full transition-all duration-300"
                          style={{ width: `${Math.round(hyp.score * 100)}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono font-bold text-slate-200">
                        {(hyp.score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>

                  <p className="text-sm font-medium text-slate-100">{hyp.statement}</p>

                  {hyp.reasoning && (
                    <p className="text-xs text-slate-400 italic bg-slate-950/50 p-2 rounded border border-slate-900">
                      Reasoning: {hyp.reasoning}
                    </p>
                  )}

                  <div className="grid grid-cols-2 gap-2 text-xs pt-1">
                    <div className="p-2 bg-slate-950 rounded border border-slate-900">
                      <span className="text-emerald-400 font-semibold">Supporting Evidence:</span>{' '}
                      <span className="text-slate-300 font-mono">
                        {hyp.supporting_evidence_ids.join(', ') || 'None'}
                      </span>
                    </div>
                    <div className="p-2 bg-slate-950 rounded border border-slate-900">
                      <span className="text-red-400 font-semibold">Contradicting Evidence:</span>{' '}
                      <span className="text-slate-300 font-mono">
                        {hyp.contradicting_evidence_ids.join(', ') || 'None'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'evidence' && (
            <div className="space-y-3">
              {observations.map((obs, idx) => (
                <div key={idx} className="p-4 bg-slate-900/70 border border-slate-800 rounded-lg flex items-start gap-3">
                  <span className="text-xs font-mono bg-slate-950 text-indigo-400 px-2 py-0.5 rounded border border-slate-800 mt-0.5">
                    OBS-{idx + 1}
                  </span>
                  <p className="text-sm text-slate-200 leading-relaxed">{obs}</p>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'missing' && (
            <div className="space-y-3">
              {missing_evidence.map((item, idx) => (
                <div key={idx} className="p-4 bg-slate-900/70 border border-amber-950/60 rounded-lg flex items-start gap-3">
                  <span className="text-xs font-mono bg-amber-950 text-amber-300 px-2 py-0.5 rounded border border-amber-800 mt-0.5">
                    NEEDED
                  </span>
                  <p className="text-sm text-amber-200/90 leading-relaxed">{item}</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right 1 Column: Investigation Context Sidebar */}
        <div className="space-y-4">
          <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-lg space-y-4">
            <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wider">
              Investigation Context
            </h3>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-slate-500 block">Time Window:</span>
                <span className="text-slate-300 font-mono">{state.time_window.start} - {state.time_window.end}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Evidence Items Collected:</span>
                <span className="text-slate-300 font-mono">{state.evidence_ids.length} items</span>
              </div>
              <div>
                <span className="text-slate-500 block">Evidence Quality Score:</span>
                <span className="text-slate-200 font-mono font-bold text-sm">
                  {((state.evidence_score || 0) * 100).toFixed(0)}%
                </span>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-800 space-y-2">
              <button
                onClick={() => alert(`Investigate requested for ${incidentId}`)}
                className="w-full py-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs rounded transition-colors"
              >
                Trigger Next Reasoning Iteration
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
