import React, { useState } from 'react';
import { GitMerge, ArrowRight, CheckCircle } from 'lucide-react';

const SEVERITY_BG = {
  HIGH: 'bg-red-500/20 text-red-400 border border-red-500/30',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  LOW: 'bg-green-500/20 text-green-400 border border-green-500/30',
  CRITICAL: 'bg-red-700/30 text-red-300 border border-red-600/40',
};

function fmt(val, sym = 'Rs.') {
  return `${sym} ${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function CycleChain({ parties }) {
  return (
    <div className="flex flex-wrap items-center gap-2 mt-3">
      {parties.map((p, i) => (
        <React.Fragment key={i}>
          <span className="bg-violet-500/20 border border-violet-500/30 text-violet-300 text-xs font-semibold px-3 py-1.5 rounded-lg">
            {p}
          </span>
          {i < parties.length - 1 && <ArrowRight className="w-4 h-4 text-gray-500" />}
        </React.Fragment>
      ))}
      {/* Loop back to first */}
      <ArrowRight className="w-4 h-4 text-gray-500" />
      <span className="bg-violet-500/20 border border-violet-500/30 text-violet-300 text-xs font-semibold px-3 py-1.5 rounded-lg opacity-50">
        {parties[0]}
      </span>
    </div>
  );
}

export default function CircularFunds({ results, currencySymbol = 'Rs.' }) {
  const findings = results?.circular_funds ?? [];
  const [expanded, setExpanded] = useState(null);

  if (findings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <CheckCircle className="w-12 h-12 text-green-400 mb-4" />
        <p className="text-lg font-semibold text-white mb-2">No Circular Fund Flows Detected</p>
        <p className="text-sm text-gray-400">No round-trip transactions found in the contra-ledger graph.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-1.5 flex items-center gap-2">
          <GitMerge className="w-6 h-6 text-violet-400" />
          Circular Fund Detection
        </h2>
        <p className="text-sm text-gray-400">
          Directed graph analysis of contra-ledger entries to identify fund round-trips —
          a common mechanism for inflating revenue or laundering funds.
        </p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Total Cycles</p>
          <p className="text-3xl font-bold text-violet-300">{findings.length}</p>
        </div>
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Total Cycled Amount</p>
          <p className="text-xl font-bold text-red-300">
            {fmt(findings.reduce((s, f) => s + (f.total_amount || 0), 0), currencySymbol)}
          </p>
        </div>
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Avg. Cycle Length</p>
          <p className="text-3xl font-bold text-yellow-300">
            {findings.length ? (findings.reduce((s, f) => s + (f.cycle_length || 0), 0) / findings.length).toFixed(1) : '—'}
          </p>
        </div>
      </div>

      {/* Cards */}
      <div className="space-y-4">
        {findings.map((f) => (
          <div key={f.finding_id} className="bg-dark-800 border border-dark-700 rounded-2xl overflow-hidden">
            <button
              onClick={() => setExpanded(expanded === f.finding_id ? null : f.finding_id)}
              className="w-full flex items-center justify-between px-5 py-4 hover:bg-dark-700/40 transition-colors text-left"
            >
              <div className="flex items-center gap-3">
                <GitMerge className="w-5 h-5 text-violet-400" />
                <div>
                  <p className="font-semibold text-white text-sm">
                    {f.cycle_length}-party cycle: {(f.parties || []).join(' → ')}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">{f.leg_count} transaction legs · {f.date_range || ''}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-sm font-bold text-red-300">{fmt(f.total_amount || 0, currencySymbol)}</span>
                <span className={`text-xs font-bold px-2.5 py-1 rounded-lg ${SEVERITY_BG[f.severity] || SEVERITY_BG.HIGH}`}>
                  {f.severity}
                </span>
              </div>
            </button>

            {expanded === f.finding_id && (
              <div className="px-5 pb-5 border-t border-dark-700/60 pt-4 space-y-4">
                <p className="text-sm text-gray-300">{f.description}</p>
                <CycleChain parties={f.parties || []} />
                {f.transactions && f.transactions.length > 0 && (
                  <div className="overflow-x-auto mt-4">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-gray-500 border-b border-dark-700 uppercase tracking-wide">
                          <th className="py-2 text-left">Date</th>
                          <th className="py-2 text-left">From</th>
                          <th className="py-2 text-left">To</th>
                          <th className="py-2 text-right">Amount</th>
                          <th className="py-2 text-left">Narration</th>
                        </tr>
                      </thead>
                      <tbody>
                        {f.transactions.map((t, i) => (
                          <tr key={i} className="border-b border-dark-700/40 text-gray-300">
                            <td className="py-1.5">{t.date}</td>
                            <td className="py-1.5">{t.from_party}</td>
                            <td className="py-1.5">{t.to_party}</td>
                            <td className="py-1.5 text-right text-red-300">{fmt(t.amount, currencySymbol)}</td>
                            <td className="py-1.5 text-gray-400">{t.narration}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                {f.recommendation && (
                  <div className="bg-blue-500/10 border border-blue-500/20 rounded-xl p-3 text-xs text-blue-300">
                    <span className="font-semibold">Recommendation: </span>{f.recommendation}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
