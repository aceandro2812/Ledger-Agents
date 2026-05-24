import React from 'react';
import { Loader2, CheckCircle2, XCircle, PlayCircle, ShieldAlert } from 'lucide-react';

const AGENT_META = [
  { key: 'Structure Detector', label: 'Structure Detection Agent', desc: 'Identifies header offsets, column configurations, date formats, and party limits.' },
  { key: 'Ingestion Agent', label: 'Ingestion & Validation Agent', desc: 'Validates arithmetic, sanitizes amounts, and parses raw spreadsheet grid lines.' },
  { key: 'Duplicate Payment Detective', label: 'Duplicate Payment Detective', desc: 'Runs 5 forensic passes: exact matches, voucher hits, fuzzy amounts, and round numbers.' },
  { key: 'Aging & FIFO Settlement', label: 'Aging & FIFO Settlement Agent', desc: 'Calculates outstanding balances using FIFO matching across historical periods.' },
  { key: 'Anomaly Detection Agent', label: 'Anomaly Detection Agent', desc: 'Scans for late-night entries, holiday payments, round trips, and split payments.' },
  { key: 'Reconciliation Agent', label: 'Reconciliation & Math Verification', desc: 'Re-evaluates running balances from scratch, identifying discrepancies.' },
  { key: 'Report Generator', label: 'Report Generator Agent', desc: 'Compiles styled spreadsheets, summaries, and invokes Claude for CA Memos.' }
];

export default function LiveAudit({ statusLogs, progress, activeAgent, error }) {
  const getAgentStatus = (agentKey) => {
    const log = statusLogs.find((l) => l.agent === agentKey);
    if (!log) return { status: 'queued', progress: 0, findings: 0 };
    return {
      status: log.status, // running, done, failed, skipped
      progress: log.progress_pct || 0,
      findings: log.finding_count || 0,
      error: log.error
    };
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-12">
      {/* Header */}
      <div className="text-center mb-10">
        <h2 className="text-3xl font-extrabold text-white mb-3">Forensic Agents Running</h2>
        <p className="text-gray-400">
          The orchestrator is coordinating agents in parallel. Running local math checks, database validation, and pattern mapping.
        </p>
      </div>

      {/* Progress Bar Container */}
      <div className="bg-dark-800 border border-dark-700 rounded-2xl p-6 mb-8 shadow-xl">
        <div className="flex justify-between items-center mb-3">
          <span className="text-sm font-semibold text-gray-300">
            {activeAgent ? `Active Agent: ${activeAgent}` : 'Initializing workflow...'}
          </span>
          <span className="text-sm font-bold text-blue-400">{progress}%</span>
        </div>
        <div className="w-full bg-dark-900 rounded-full h-3.5 overflow-hidden border border-dark-600">
          <div
            className="bg-gradient-to-r from-blue-600 to-indigo-500 h-full rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Error Boundary Notification */}
      {error && (
        <div className="bg-red-950/30 border border-red-500/50 rounded-xl p-4 flex gap-3 text-red-300 mb-8">
          <ShieldAlert className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-bold">Execution Warning</h4>
            <p className="text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Agent Cards Grid */}
      <div className="space-y-4">
        {AGENT_META.map((agent) => {
          const state = getAgentStatus(agent.key);
          
          return (
            <div
              key={agent.key}
              className={`bg-dark-800 border rounded-2xl p-5 flex items-center justify-between transition-all duration-300 ${
                state.status === 'running'
                  ? 'border-blue-500/70 shadow-[0_0_15px_rgba(59,130,246,0.15)] bg-dark-800/90'
                  : state.status === 'done'
                  ? 'border-green-500/40 bg-dark-800/50'
                  : state.status === 'failed'
                  ? 'border-red-500/40'
                  : 'border-dark-700 opacity-60'
              }`}
            >
              <div className="flex items-start gap-4">
                <div className="mt-1">
                  {state.status === 'running' && (
                    <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
                  )}
                  {state.status === 'done' && (
                    <CheckCircle2 className="w-6 h-6 text-green-400" />
                  )}
                  {state.status === 'failed' && (
                    <XCircle className="w-6 h-6 text-red-400" />
                  )}
                  {state.status === 'queued' && (
                    <PlayCircle className="w-6 h-6 text-gray-500" />
                  )}
                  {state.status === 'skipped' && (
                    <XCircle className="w-6 h-6 text-yellow-500/60" />
                  )}
                </div>
                
                <div>
                  <h3 className="text-base font-bold text-white mb-0.5">{agent.label}</h3>
                  <p className="text-xs text-gray-400 max-w-xl">{agent.desc}</p>
                  {state.error && (
                    <span className="text-xs text-red-400 mt-2 block font-medium">
                      Error: {state.error}
                    </span>
                  )}
                </div>
              </div>

              <div className="text-right">
                {state.status === 'done' && state.findings > 0 && (
                  <span className={`text-xs px-2.5 py-1 rounded-full font-bold bg-blue-950/40 text-blue-400 border border-blue-800/40`}>
                    {state.findings} Findings
                  </span>
                )}
                {state.status === 'done' && state.findings === 0 && (
                  <span className="text-xs text-gray-500 font-medium">Clear</span>
                )}
                {state.status === 'running' && (
                  <span className="text-xs text-blue-400 font-semibold animate-pulse">Running</span>
                )}
                {state.status === 'queued' && (
                  <span className="text-xs text-gray-500">Queued</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
