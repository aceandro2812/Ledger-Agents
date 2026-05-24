import React from 'react';
import { Calendar, CheckCircle, AlertTriangle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

const SEVERITY_BG = {
  HIGH: 'bg-red-500/20 text-red-400 border border-red-500/30',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  LOW: 'bg-green-500/20 text-green-400 border border-green-500/30',
  CRITICAL: 'bg-red-700/30 text-red-300 border border-red-600/40',
};

const TYPE_LABEL = {
  WEEKEND_CONCENTRATION: 'Weekend Concentration',
  YEAR_END_LOADING: 'Month-End Loading',
  FY_END_SPIKE: 'Financial Year-End Spike',
  GAP_BURST: 'Gap + Burst Pattern',
};
const TYPE_COLOR = {
  WEEKEND_CONCENTRATION: 'text-orange-400',
  YEAR_END_LOADING: 'text-yellow-400',
  FY_END_SPIKE: 'text-red-400',
  GAP_BURST: 'text-violet-400',
};

function fmt(val, sym = 'Rs.') {
  return `${sym} ${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function TemporalPatterns({ results, currencySymbol = 'Rs.' }) {
  const findings = results?.temporal_patterns ?? [];
  const fySpike = findings.filter((f) => f.pattern_type === 'FY_END_SPIKE');

  if (findings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <CheckCircle className="w-12 h-12 text-green-400 mb-4" />
        <p className="text-lg font-semibold text-white mb-2">No Temporal Anomalies Detected</p>
        <p className="text-sm text-gray-400">Transaction timing follows normal business patterns.</p>
      </div>
    );
  }

  const monthlyData =
    fySpike.length > 0 && fySpike[0].monthly_breakdown
      ? Object.entries(fySpike[0].monthly_breakdown).map(([month, amount]) => ({
          month,
          amount: Number(amount),
        }))
      : [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-1.5 flex items-center gap-2">
          <Calendar className="w-6 h-6 text-orange-400" />
          Temporal Pattern Analysis
        </h2>
        <p className="text-sm text-gray-400">
          Detects unusual transaction timing: weekend clustering, month/year-end loading, and gap-burst sequences.
        </p>
      </div>

      {/* FY Monthly Chart */}
      {monthlyData.length > 0 && (
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-5">
          <p className="text-sm font-semibold text-white mb-4">Monthly Transaction Distribution (FY)</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={monthlyData}>
              <XAxis dataKey="month" stroke="#6b7280" tick={{ fill: '#9ca3af', fontSize: 11 }} />
              <YAxis stroke="#6b7280" tick={{ fill: '#9ca3af', fontSize: 10 }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                formatter={(v) => [fmt(v, currencySymbol), 'Amount']}
              />
              <Bar dataKey="amount" fill="#f97316" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Pattern cards */}
      <div className="space-y-4">
        {findings.map((f) => (
          <div key={f.finding_id} className="bg-dark-800 border border-dark-700 rounded-2xl p-5">
            <div className="flex justify-between items-start">
              <div className="flex items-start gap-3">
                <AlertTriangle className={`w-5 h-5 mt-0.5 ${TYPE_COLOR[f.pattern_type] || 'text-yellow-400'}`} />
                <div>
                  <p className="font-semibold text-white">{TYPE_LABEL[f.pattern_type] || f.pattern_type}</p>
                  <p className="text-xs text-gray-400 mt-1">{f.description}</p>
                </div>
              </div>
              <span className={`text-xs font-bold px-2.5 py-1 rounded-lg ml-3 flex-shrink-0 ${SEVERITY_BG[f.severity] || SEVERITY_BG.MEDIUM}`}>
                {f.severity}
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
              {f.count != null && (
                <div className="bg-dark-700/40 rounded-xl p-3 text-center">
                  <p className="text-xs text-gray-500 mb-1">Count</p>
                  <p className="text-lg font-bold text-white">{f.count.toLocaleString()}</p>
                </div>
              )}
              {f.percentage != null && (
                <div className="bg-dark-700/40 rounded-xl p-3 text-center">
                  <p className="text-xs text-gray-500 mb-1">Percentage</p>
                  <p className="text-lg font-bold text-yellow-300">{(f.percentage * 100).toFixed(1)}%</p>
                </div>
              )}
              {f.total_amount != null && (
                <div className="bg-dark-700/40 rounded-xl p-3 text-center">
                  <p className="text-xs text-gray-500 mb-1">Total Amount</p>
                  <p className="text-sm font-bold text-red-300">{fmt(f.total_amount, currencySymbol)}</p>
                </div>
              )}
              {f.gap_days != null && (
                <div className="bg-dark-700/40 rounded-xl p-3 text-center">
                  <p className="text-xs text-gray-500 mb-1">Gap Days</p>
                  <p className="text-lg font-bold text-violet-300">{f.gap_days}</p>
                </div>
              )}
            </div>

            {f.recommendation && (
              <div className="mt-4 bg-blue-500/10 border border-blue-500/20 rounded-xl p-3 text-xs text-blue-300">
                <span className="font-semibold">Recommendation: </span>{f.recommendation}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
