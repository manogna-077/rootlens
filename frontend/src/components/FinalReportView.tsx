import React, { useEffect, useState } from 'react';
import { Report } from '../types';
import { api } from '../services/api';

interface FinalReportViewProps {
  incidentId: string;
}

export const FinalReportView: React.FC<FinalReportViewProps> = ({ incidentId }) => {
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [approvalComment, setApprovalComment] = useState<string>('');
  const [submitting, setSubmitting] = useState<boolean>(false);

  useEffect(() => {
    setLoading(true);
    api.getReport(incidentId)
      .then((data) => {
        setReport(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load report', err);
        setLoading(false);
      });
  }, [incidentId]);

  const handleApproval = async (approved: boolean) => {
    if (!report) return;
    setSubmitting(true);
    try {
      await api.submitApproval(incidentId, approved, approvalComment);
      setReport({
        ...report,
        human_approved: approved,
        approval_comment: approvalComment
      });
    } catch (err) {
      console.error('Approval submission failed', err);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || !report) {
    return (
      <div className="p-8 text-center text-slate-400">
        Generating Final Investigation Report for {incidentId}...
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="p-6 bg-slate-900/90 border border-slate-800 rounded-lg shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono bg-indigo-950 text-indigo-300 border border-indigo-800 px-2 py-0.5 rounded">
              {report.incident_id}
            </span>
            <span className={`text-xs px-2 py-0.5 rounded font-bold border ${
              report.human_approved
                ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                : 'bg-amber-950 text-amber-300 border-amber-800'
            }`}>
              {report.human_approved ? 'APPROVED BY HUMAN OPERATOR' : 'PENDING HUMAN APPROVAL'}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-100 mt-2">{report.title}</h1>
          <p className="text-xs text-slate-400 mt-1">Generated at: {report.generated_at}</p>
        </div>

        <button
          onClick={() => window.print()}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded border border-slate-700 transition-colors self-start md:self-auto"
        >
          Export / Print Report
        </button>
      </div>

      {/* Summary Section */}
      <div className="p-6 bg-slate-900/70 border border-slate-800 rounded-lg space-y-3">
        <h2 className="text-sm font-bold text-indigo-400 uppercase tracking-wider">Executive Summary</h2>
        <p className="text-sm text-slate-200 leading-relaxed">{report.summary}</p>
      </div>

      {/* Root Cause & Contributing Factors */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-6 bg-slate-900/70 border border-slate-800 rounded-lg space-y-3">
          <h2 className="text-sm font-bold text-red-400 uppercase tracking-wider">Root Cause Analysis</h2>
          <p className="text-sm text-slate-200 font-medium leading-relaxed">{report.root_cause}</p>
        </div>

        <div className="p-6 bg-slate-900/70 border border-slate-800 rounded-lg space-y-3">
          <h2 className="text-sm font-bold text-amber-400 uppercase tracking-wider">Contributing Factors</h2>
          <ul className="list-disc list-inside space-y-1 text-sm text-slate-300">
            {report.contributing_factors.map((factor, idx) => (
              <li key={idx}>{factor}</li>
            ))}
          </ul>
        </div>
      </div>

      {/* Timeline Summary & Recommendations */}
      <div className="p-6 bg-slate-900/70 border border-slate-800 rounded-lg space-y-4">
        <h2 className="text-sm font-bold text-slate-300 uppercase tracking-wider">Timeline Summary</h2>
        <div className="space-y-2 border-l-2 border-slate-800 pl-4">
          {report.timeline_summary.map((event, idx) => (
            <div key={idx} className="text-xs font-mono text-slate-300">
              {event}
            </div>
          ))}
        </div>
      </div>

      <div className="p-6 bg-slate-900/70 border border-slate-800 rounded-lg space-y-3">
        <h2 className="text-sm font-bold text-emerald-400 uppercase tracking-wider">Recommended Remediation</h2>
        <ul className="list-disc list-inside space-y-1 text-sm text-slate-200">
          {report.recommended_actions.map((action, idx) => (
            <li key={idx}>{action}</li>
          ))}
        </ul>
      </div>

      {/* Human Approval Form */}
      <div className="p-6 bg-slate-900/90 border border-indigo-900/80 rounded-lg space-y-4 shadow-xl">
        <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
          <span>Human Approval & Sign-Off</span>
        </h2>

        {report.human_approved ? (
          <div className="p-4 bg-emerald-950/60 border border-emerald-800 rounded text-sm text-emerald-200 space-y-1">
            <p className="font-semibold">✓ Report Approved</p>
            {report.approval_comment && (
              <p className="text-xs text-emerald-300 italic">Comment: "{report.approval_comment}"</p>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Sign-off Comment / Reviewer Notes:
              </label>
              <textarea
                value={approvalComment}
                onChange={(e) => setApprovalComment(e.target.value)}
                placeholder="Enter approval rationale or feedback..."
                className="w-full p-3 bg-slate-950 border border-slate-800 rounded text-sm text-slate-100 focus:outline-none focus:border-indigo-500"
                rows={3}
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => handleApproval(true)}
                disabled={submitting}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white font-medium text-xs rounded transition-colors"
              >
                Approve Investigation Report
              </button>
              <button
                onClick={() => handleApproval(false)}
                disabled={submitting}
                className="px-5 py-2 bg-slate-800 hover:bg-slate-700 disabled:bg-slate-800 text-slate-300 font-medium text-xs rounded transition-colors"
              >
                Reject / Request Revision
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
