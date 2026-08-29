import React, { useState } from 'react';
import { IterationTraceStep, HypothesisChange } from '../data/mockData';
import { AgentAction, Hypothesis, ToolResult } from '../types';

interface AgentTraceViewProps {
  traceSteps: IterationTraceStep[];
}

export const AgentTraceView: React.FC<AgentTraceViewProps> = ({ traceSteps }) => {
  const [selectedIterationFilter, setSelectedIterationFilter] = useState<number | 'ALL'>('ALL');
  const [expandedIterations, setExpandedIterations] = useState<Record<number, boolean>>({
    1: true,
    2: true,
    3: true
  });

  const toggleIteration = (iterationNum: number) => {
    setExpandedIterations((prev) => ({
      ...prev,
      [iterationNum]: !prev[iterationNum]
    }));
  };

  const filteredSteps = traceSteps.filter((step) => {
    if (selectedIterationFilter === 'ALL') return true;
    return step.iteration === selectedIterationFilter;
  });

  const getStatusBadgeClass = (status: Hypothesis['status']) => {
    switch (status) {
      case 'CONFIRMED':
      case 'SUPPORTED':
        return 'bg-emerald-950 text-emerald-300 border border-emerald-800';
      case 'REJECTED':
      case 'DISCONFIRMED':
        return 'bg-red-950 text-red-300 border border-red-800';
      case 'GENERATED':
      default:
        return 'bg-slate-800 text-slate-300 border border-slate-700';
    }
  };

  const getToolStatusBadgeClass = (status: ToolResult['status']) => {
    switch (status) {
      case 'SUCCESS':
        return 'bg-emerald-950 text-emerald-300 border border-emerald-800';
      case 'FAILURE':
        return 'bg-red-950 text-red-300 border border-red-800';
      case 'PENDING':
      default:
        return 'bg-amber-950 text-amber-300 border border-amber-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* Trace Overview Header & Navigation Bar */}
      <div className="p-5 bg-slate-900/90 border border-slate-800 rounded-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-pulse"></span>
            <h2 className="text-lg font-bold text-slate-100">Agent Reasoning Trace</h2>
            <span className="text-xs bg-indigo-950 text-indigo-300 border border-indigo-800 px-2 py-0.5 rounded font-mono">
              {traceSteps.length} Iterations
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Step-by-step audit of agent hypothesis generation, action selection, tool evidence, and score evolutions.
          </p>
        </div>

        {/* Iteration Stepper / Filters */}
        <div className="flex items-center gap-1.5 bg-slate-950 p-1.5 rounded-lg border border-slate-800 flex-wrap">
          <button
            onClick={() => setSelectedIterationFilter('ALL')}
            className={`px-3 py-1 text-xs font-semibold rounded transition-colors ${
              selectedIterationFilter === 'ALL'
                ? 'bg-indigo-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            All Steps ({traceSteps.length})
          </button>
          {traceSteps.map((step) => (
            <button
              key={step.iteration}
              onClick={() => setSelectedIterationFilter(step.iteration)}
              className={`px-3 py-1 text-xs font-semibold rounded transition-colors ${
                selectedIterationFilter === step.iteration
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              Step #{step.iteration}
            </button>
          ))}
        </div>
      </div>

      {/* Iteration Timeline Cards */}
      <div className="space-y-6">
        {filteredSteps.map((step) => {
          const isExpanded = expandedIterations[step.iteration] ?? true;

          return (
            <div
              key={step.iteration}
              className="bg-slate-900/80 border border-slate-800 rounded-lg shadow-md overflow-hidden transition-all"
            >
              {/* Iteration Header / Bar */}
              <div
                onClick={() => toggleIteration(step.iteration)}
                className="p-4 bg-slate-900 border-b border-slate-800/80 flex items-center justify-between cursor-pointer hover:bg-slate-800/50 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-indigo-950 border border-indigo-700 flex items-center justify-center font-mono font-bold text-indigo-300 text-sm">
                    #{step.iteration}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-slate-100">
                        Iteration #{step.iteration}
                      </span>
                      <span className="text-xs font-mono text-slate-500">
                        {new Date(step.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                      <span>Action: <code className="text-indigo-300 font-mono">{step.selected_action.tool}</code></span>
                      <span>•</span>
                      <span>Evidence: <span className="font-mono text-slate-300">{step.tool_result.evidence_ids.join(', ')}</span></span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-xs text-indigo-400 bg-indigo-950/80 px-2 py-0.5 rounded border border-indigo-900 font-mono">
                    {step.hypothesis_changes.length} Hypothesis Updates
                  </span>
                  <button className="text-slate-400 hover:text-slate-200">
                    <svg
                      className={`w-5 h-5 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                </div>
              </div>

              {/* Collapsible Iteration Body */}
              {isExpanded && (
                <div className="p-5 space-y-6">
                  {/* Step 1: Active Hypotheses at Start of Iteration */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
                      1. Active Hypotheses at Iteration Start
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {step.hypotheses.map((hyp) => (
                        <div key={hyp.id} className="p-3.5 bg-slate-950/70 border border-slate-800 rounded-md space-y-2">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-mono font-bold text-indigo-400">{hyp.id}</span>
                            <div className="flex items-center gap-2">
                              <span className={`text-xs px-2 py-0.5 rounded font-bold ${getStatusBadgeClass(hyp.status)}`}>
                                {hyp.status}
                              </span>
                              <span className="text-xs font-mono font-bold text-slate-300">
                                {Math.round(hyp.score * 100)}%
                              </span>
                            </div>
                          </div>
                          <p className="text-xs text-slate-200 leading-snug">{hyp.statement}</p>
                          <div className="w-full bg-slate-900 h-1.5 rounded-full overflow-hidden">
                            <div
                              className="bg-indigo-500 h-full rounded-full"
                              style={{ width: `${Math.round(hyp.score * 100)}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Step 2: Selected Agent Action & Reason */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      <span className="w-2 h-2 rounded-full bg-purple-500"></span>
                      2. Selected Agent Action & Reasoning
                    </div>
                    <div className="p-4 bg-slate-950/80 border border-purple-900/60 rounded-md space-y-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-purple-400 font-semibold uppercase">Tool Call:</span>
                          <span className="text-xs font-mono bg-purple-950 text-purple-300 px-2.5 py-1 rounded border border-purple-800 font-bold">
                            {step.selected_action.tool}
                          </span>
                        </div>
                        {step.selected_action.target_hypotheses && (
                          <div className="flex items-center gap-1.5 text-xs">
                            <span className="text-slate-500">Target Hypotheses:</span>
                            {step.selected_action.target_hypotheses.map((hId) => (
                              <span key={hId} className="font-mono bg-slate-900 text-indigo-300 px-1.5 py-0.5 rounded border border-slate-800">
                                {hId}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>

                      {/* Reasoning Box */}
                      <div className="p-3 bg-purple-950/30 border border-purple-900/40 rounded text-xs text-purple-200/90 leading-relaxed">
                        <span className="font-semibold text-purple-300 block mb-0.5">Agent Reason:</span>
                        {step.reason}
                      </div>

                      {/* Tool Arguments */}
                      <div className="text-xs space-y-1">
                        <span className="text-slate-400 font-semibold">Arguments:</span>
                        <pre className="p-2.5 bg-slate-900 rounded border border-slate-800 text-slate-300 font-mono overflow-x-auto text-xs">
                          {JSON.stringify(step.selected_action.arguments, null, 2)}
                        </pre>
                      </div>

                      {step.selected_action.missing_evidence_addressed && (
                        <div className="text-xs text-slate-400 flex items-center gap-2">
                          <span className="text-amber-400 font-medium">Addressed Missing Evidence:</span>
                          <span className="text-slate-300">{step.selected_action.missing_evidence_addressed.join(', ')}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Step 3: Returned Evidence / Tool Result */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                      3. Returned Evidence & Tool Result
                    </div>
                    <div className="p-4 bg-slate-950/80 border border-emerald-900/50 rounded-md space-y-3">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-slate-400 font-semibold">Tool:</span>
                          <span className="text-xs font-mono font-bold text-slate-200">{step.tool_result.tool}</span>
                          <span className={`text-xs px-2 py-0.5 rounded font-bold ${getToolStatusBadgeClass(step.tool_result.status)}`}>
                            {step.tool_result.status}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs text-slate-500">Evidence IDs:</span>
                          {step.tool_result.evidence_ids.map((evId) => (
                            <span key={evId} className="text-xs font-mono bg-emerald-950 text-emerald-300 px-1.5 py-0.5 rounded border border-emerald-800">
                              {evId}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Observations */}
                      <div className="space-y-1.5">
                        <span className="text-xs font-semibold text-slate-300">Observations Gathered:</span>
                        {step.tool_result.observations.map((obs, oIdx) => (
                          <div key={oIdx} className="p-2.5 bg-slate-900/90 border border-slate-800 rounded text-xs text-slate-200 flex items-start gap-2">
                            <span className="text-emerald-400 font-mono font-bold mt-0.5">›</span>
                            <span>{obs}</span>
                          </div>
                        ))}
                      </div>

                      {/* Provenance */}
                      {step.tool_result.provenance.length > 0 && (
                        <div className="text-xs flex items-center gap-2 pt-1 border-t border-slate-900">
                          <span className="text-slate-500">Provenance / Source:</span>
                          <span className="font-mono text-slate-400">{step.tool_result.provenance.join(', ')}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Step 4: Hypothesis Changes / Score Evolutions */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                      4. Hypothesis Changes & Score Evolution
                    </div>
                    <div className="space-y-2">
                      {step.hypothesis_changes.map((change) => {
                        const scoreDiff = change.new_score - change.previous_score;
                        const scoreDiffText = (scoreDiff >= 0 ? `+` : ``) + (scoreDiff * 100).toFixed(0) + '%';

                        return (
                          <div key={change.hypothesis_id} className="p-3.5 bg-slate-950/90 border border-slate-800 rounded-md space-y-2">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-mono font-bold text-indigo-400">{change.hypothesis_id}</span>
                                <div className="flex items-center gap-1.5 text-xs">
                                  <span className={`px-2 py-0.5 rounded font-bold ${getStatusBadgeClass(change.previous_status)}`}>
                                    {change.previous_status}
                                  </span>
                                  <span className="text-slate-500">➔</span>
                                  <span className={`px-2 py-0.5 rounded font-bold ${getStatusBadgeClass(change.new_status)}`}>
                                    {change.new_status}
                                  </span>
                                </div>
                              </div>

                              {/* Score Transition Pill */}
                              <div className="flex items-center gap-2">
                                <span className="text-xs text-slate-400">Score:</span>
                                <span className="text-xs font-mono text-slate-400">
                                  {(change.previous_score * 100).toFixed(0)}%
                                </span>
                                <span className="text-slate-500">➔</span>
                                <span className="text-xs font-mono font-bold text-slate-100">
                                  {(change.new_score * 100).toFixed(0)}%
                                </span>
                                <span className={`text-xs px-2 py-0.5 rounded font-bold font-mono ${
                                  scoreDiff > 0
                                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                                    : scoreDiff < 0
                                    ? 'bg-red-950 text-red-300 border border-red-800'
                                    : 'bg-slate-800 text-slate-400'
                                }`}>
                                  {scoreDiffText}
                                </span>
                              </div>
                            </div>

                            <p className="text-xs text-slate-300">{change.statement}</p>

                            {change.reasoning && (
                              <p className="text-xs text-slate-400 italic bg-slate-900/60 p-2 rounded border border-slate-900">
                                Reason for score change: {change.reasoning}
                              </p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Step 5: Next Action */}
                  {step.next_action && (
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                        <span className="w-2 h-2 rounded-full bg-cyan-500"></span>
                        5. Selected Next Action
                      </div>
                      <div className="p-3.5 bg-gradient-to-r from-slate-950 via-slate-900 to-indigo-950/40 border border-indigo-900/50 rounded-md flex flex-col md:flex-row md:items-center justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-semibold text-indigo-400">Next Tool:</span>
                            <span className="text-xs font-mono bg-indigo-950 text-indigo-200 px-2 py-0.5 rounded border border-indigo-800 font-bold">
                              {step.next_action.tool}
                            </span>
                          </div>
                          <p className="text-xs text-slate-300">{step.next_action.reason}</p>
                        </div>
                        <span className="text-xs font-mono text-indigo-300 bg-indigo-950 px-2.5 py-1 rounded border border-indigo-800 whitespace-nowrap self-start md:self-center">
                          Pending Execution ➔
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
