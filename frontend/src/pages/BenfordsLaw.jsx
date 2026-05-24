import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer, Cell } from 'recharts';
import { Activity, AlertTriangle, CheckCircle } from 'lucide-react';

const CONFORMITY_COLOR = {
  CLOSE: 'text-green-400',
  ACCEPTABLE: 'text-blue-400',
  MARGINAL: 'text-yellow-400',
  NON_CONFORMING: 'text-red-400',
};
const CONFORMITY_BG = {
  CLOSE: 'bg-green-500/10 border border-green-500/20',
  ACCEPTABLE: 'bg-blue-500/10 border border-blue-500/20',
  MARGINAL: 'bg-yellow-500/10 border border-yellow-500/20',
  NON_CONFORMING: 'bg-red-500/10 border border-red-500/20',
};
const SEVERITY_BG = {
  HIGH: 'bg-red-500/20 text-red-400 border border-red-500/30',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  LOW: 'bg-green-500/20 text-green-400 border border-green-500/30',
  CRITICAL: 'bg-red-700/30 text-red-300 border border-red-600/40',
};

function DigitChart({ digits }) {
  const data = digits.map((d) => ({
    digit: String(d.digit),
    observed: parseFloat((d.observed_pct * 100).toFixed(2)),
    expected: parseFloat((d.expected_pct * 100).toFixed(2)),
    flagged: d.is_flagged,
  }));

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} barCategoryGap="20%">
        <XAxis dataKey="digit" stroke="#6b7280" tick={{ fill: '#9ca3af', fontSize: 12 }} />
        <YAxis stroke="#6b7280" tick={{ fill: '#9ca3af', fontSize: 11 }} tickFormatter={(v) => `${v}%`} />
        <Tooltip
          contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
          labelStyle={{ color: '#e5e7eb' }}
          formatter={(val, name) => [`${val}%`, name === 'observed' ? 'Observed' : 'Expected']}
        />
        <Bar dataKey="expected" name="expected" fill="#3b82f6" opacity={0.3} radius={[3, 3, 0, 0]} />
        <Bar dataKey="observed" name="observed" radius={[3, 3, 0, 0]}>
          {data.map((entry, idx) => (
            <Cell key={idx} fill={entry.flagged ? '#ef4444' : '#22c55e'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export default function BenfordsLaw({ results }) {
  const findings = results?.benfords_findings ?? [];
  const [expanded, setExpanded] = useState(null);

  if (findings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <CheckCircle className="w-12 h-12 text-green-400 mb-4" />
        <p className="text-lg font-semibold text-white mb-2">No Benford's Law Violations Found</p>
        <p className="text-sm text-gray-400">All scopes (global + per-party) conform to expected digit distribution.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-1.5 flex items-center gap-2">
          <Activity className="w-6 h-6 text-violet-400" />
          Benford's Law Analysis
        </h2>
        <p className="text-sm text-gray-400">
          Benford's Law states that the leading digit of naturally occurring financial data follows a predictable distribution.
          Significant deviation may indicate data manipulation or fraud.
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {['CLOSE', 'ACCEPTABLE', 'MARGINAL', 'NON_CONFORMING'].map((c) => {
          const count = findings.filter((f) => f.conformity === c).length;
          return (
            <div key={c} className={`rounded-xl p-4 ${CONFORMITY_BG[c]}`}>
              <p className={`text-xs font-semibold uppercase tracking-wide ${CONFORMITY_COLOR[c]}`}>{c.replace('_', ' ')}</p>
              <p className="text-2xl font-bold text-white mt-1">{count}</p>
              <p className="text-xs text-gray-400 mt-0.5">scopes</p>
            </div>
          );
        })}
      </div>

      {/* Finding cards */}
      <div className="space-y-4">
        {findings.map((f) => (
          <div key={f.finding_id} className="bg-dark-800 border border-dark-700 rounded-2xl overflow-hidden">
            {/* Header */}
            <button
              onClick={() => setExpanded(expanded === f.finding_id ? null : f.finding_id)}
              className="w-full flex items-center justify-between px-5 py-4 hover:bg-dark-700/40 transition-colors text-left"
            >
              <div className="flex items-center gap-3">
                <AlertTriangle className={`w-5 h-5 ${CONFORMITY_COLOR[f.conformity]}`} />
                <div>
                  <p className="font-semibold text-white text-sm">{f.scope === 'ALL' ? 'Global (All Transactions)' : f.scope}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {f.total_transactions.toLocaleString()} txns · MAD {f.mad_score?.toFixed(5)} · χ² {f.chi_square?.toFixed(2)}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-xs font-bold px-2.5 py-1 rounded-lg ${CONFORMITY_BG[f.conformity]} ${CONFORMITY_COLOR[f.conformity]}`}>
                  {f.conformity.replace('_', ' ')}
                </span>
                <span className={`text-xs font-bold px-2.5 py-1 rounded-lg ${SEVERITY_BG[f.severity] || SEVERITY_BG.MEDIUM}`}>{f.severity}</span>
              </div>
            </button>

            {expanded === f.finding_id && (
              <div className="px-5 pb-5 space-y-4 border-t border-dark-700/60">
                <p className="text-sm text-gray-300 pt-4">{f.description}</p>
                <DigitChart digits={f.digit_results} />
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-gray-500 border-b border-dark-700">
                        <th className="py-2 text-left">Digit</th>
                        <th className="py-2 text-right">Observed %</th>
                        <th className="py-2 text-right">Expected %</th>
                        <th className="py-2 text-right">Z-Score</th>
                        <th className="py-2 text-center">Flag</th>
                      </tr>
                    </thead>
                    <tbody>
                      {f.digit_results.map((d) => (
                        <tr key={d.digit} className={`border-b border-dark-700/40 ${d.is_flagged ? 'text-red-300' : 'text-gray-300'}`}>
                          <td className="py-1.5 font-bold">{d.digit}</td>
                          <td className="py-1.5 text-right">{(d.observed_pct * 100).toFixed(2)}%</td>
                          <td className="py-1.5 text-right text-gray-500">{(d.expected_pct * 100).toFixed(2)}%</td>
                          <td className="py-1.5 text-right">{d.z_score?.toFixed(2)}</td>
                          <td className="py-1.5 text-center">{d.is_flagged ? '⚠️' : '✓'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
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
