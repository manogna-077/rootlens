import { useState } from 'react';
import { ViewType } from './types';
import { IncidentCommandView } from './components/IncidentCommandView';
import { InvestigationConsoleView } from './components/InvestigationConsoleView';
import { FinalReportView } from './components/FinalReportView';
import { AuditView } from './components/AuditView';

export function App() {
  const [currentView, setCurrentView] = useState<ViewType>('incident-command');
  const [selectedIncidentId, setSelectedIncidentId] = useState<string>('INC-2026-001');

  const handleSelectIncident = (id: string) => {
    setSelectedIncidentId(id);
    setCurrentView('investigation-console');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Top App Header */}
      <header className="bg-slate-900 border-b border-slate-800 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white font-black text-sm shadow-md">
              RL
            </div>
            <div>
              <span className="font-bold text-lg text-slate-100 tracking-tight">RootLens</span>
              <span className="ml-2 text-xs font-mono text-indigo-400 bg-indigo-950 px-2 py-0.5 rounded border border-indigo-900">
                v1.0-BuildSprint
              </span>
            </div>
          </div>

          {/* Navigation Bar for 4 Skeleton Views */}
          <nav className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
            <button
              onClick={() => setCurrentView('incident-command')}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                currentView === 'incident-command'
                  ? 'bg-indigo-600 text-white font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Incident Command
            </button>
            <button
              onClick={() => setCurrentView('investigation-console')}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                currentView === 'investigation-console'
                  ? 'bg-indigo-600 text-white font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Investigation Console
            </button>
            <button
              onClick={() => setCurrentView('final-report')}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                currentView === 'final-report'
                  ? 'bg-indigo-600 text-white font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Final Report
            </button>
            <button
              onClick={() => setCurrentView('audit')}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                currentView === 'audit'
                  ? 'bg-indigo-600 text-white font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Audit Log
            </button>
          </nav>
        </div>
      </header>

      {/* View Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {currentView === 'incident-command' && (
          <IncidentCommandView onSelectIncident={handleSelectIncident} />
        )}
        {currentView === 'investigation-console' && (
          <InvestigationConsoleView incidentId={selectedIncidentId} />
        )}
        {currentView === 'final-report' && (
          <FinalReportView incidentId={selectedIncidentId} />
        )}
        {currentView === 'audit' && (
          <AuditView incidentId={selectedIncidentId} />
        )}
      </main>

      {/* Footer */}
      <footer className="bg-slate-950 border-t border-slate-900 py-4 text-center text-xs text-slate-500">
        RootLens BuildSprint 2026 — Person 2 (Frontend)
      </footer>
    </div>
  );
}

export default App;
