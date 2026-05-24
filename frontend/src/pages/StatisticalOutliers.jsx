import React, { useState } from 'react';
import { TrendingUp, CheckCircle, AlertTriangle } from 'lucide-react';

const SEVERITY_BG = {
  HIGH: 'bg-red-500/20 text-red-400 border border-red-500/30',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  LOW: 'bg-green-500/20 text-green-400 border border-green-500/30',
  CRITICAL: 'bg-red-700/30 text-red-300 border border-red-600/40',
};

function fmt(val, sym = 'Rs.') {
  return `${sym} ${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function StatisticalOutliers({ results, currencySymbol = 'Rs.' }) {
  const findings = results?.statistical_outliers ?? [];
  const outliers = findings.filter((f) => f.detection_type === 'Z_SCORE_OUTLIER');
  const structuring = findings.filter((f) => f.detection_type === 'STRUCTURING');
  const [tab, setTab] = useState('outliers');

  if (findings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <CheckCircle className="w-12 h-12 text-green-400 mb-4" />
        <p className="text-lg font-semibold text-white mb-2">No Statistical Outliers Found</p>
        <p className="text-sm text-gray-400">No z-score anomalies or structuring patterns detected.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-1.5 flex items-center gap-2">
          <TrendingUp className="w-6 h-6 text-cyan-400" />
          Statistical Outlier Detection
        </h2>
        <p className="text-sm text-gray-400">
          Z-score analysis per party flags unusually large transactions. Structuring detection identifies transactions
          just below reporting thresholds (Rs. 50k, 2L, 10L, etc.).
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2.5">
        {[
          { key: 'outliers', label: `Z-Score Outliers (${outliers.length})` },
          { key: 'structuring', label: `Structuring (${structuring.length})` },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`text-sm font-semibold px-4 py-2 rounded-xl transition-all ${
              tab === t.key ? 'bg-cyan-600 text-white' : 'bg-dark-800 text-gray-400 hover:bg-dark-700/60 border border-dark-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'outliers' && (
        <div className="overflow-x-auto rounded-2xl border border-dark-700">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-500 bg-dark-800 border-b border-dark-700 text-xs uppercase tracking-wide">
                <th className="py-3 px-4 text-left">Party</th>
                <th className="py-3 px-4 text-right">Transaction Amount</th>
                <th className="py-3 px-4 text-right">Party Mean</th>
                <th className="py-3 px-4 text-right">Z-Score</th>
                <th className="py-3 px-4 text-right">Date</th>
                <th className="py-3 px-4 text-center">Severity</th>
              </tr>
            </thead>
            <tbody>
              {outliers.map((f, i) => (
                <tr key={i} className="border-b border-dark-700/50 hover:bg-dark-700/20 text-gray-300">
                  <td className="py-3 px-4 font-medium text-white">{f.party}</td>
                  <td className="py-3 px-4 text-right text-red-300 font-semibold">{fmt(f.amount, currencySymbol)}</td>
                  <td className="py-3 px-4 text-right text-gray-400">{fmt(f.party_mean || 0, currencySymbol)}</td>
                  <td className="py-3 px-4 text-right font-bold text-yellow-300">{f.z_score?.toFixed(2)}</td>
                  <td className="py-3 px-4 text-right text-gray-400">{f.date}</td>
                  <td className="py-3 px-4 text-center">
                    <span className={`text-xs font-bold px-2.5 py-1 rounded-lg ${SEVERITY_BG[f.severity] || SEVERITY_BG.MEDIUM}`}>
                      {f.severity}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'structuring' && (
        <div className="space-y-4">
          {structuring.length === 0 ? (
            <p className="text-gray-400 text-sm py-10 text-center">No structuring patterns detected.</p>
          ) : (
            structuring.map((f, i) => (
              <div key={i} className="bg-dark-800 border border-dark-700 rounded-2xl p-5">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <p className="font-semibold text-white">{f.party}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{f.description}</p>
                  </div>
                  <span className={`text-xs font-bold px-2.5 py-1 rounded-lg ${SEVERITY_BG[f.severity] || SEVERITY_BG.MEDIUM}`}>
                    {f.severity}
                  </span>
                </div>
                <div className="grid grid-cols-3 gap-3 mt-3">
                  <div className="bg-dark-700/40 rounded-xl p-3 text-center">
                    <p className="text-xs text-gray-500 mb-1">Threshold</p>
                    <p className="text-sm font-bold text-white">{fmt(f.threshold || 0, currencySymbol)}</p>
                  </div>
                  <div className="bg-dark-700/40 rounded-xl p-3 text-center">
                    <p className="text-xs text-gray-500 mb-1">Count Below</p>
                    <p className="text-sm font-bold text-yellow-300">{f.count_below_threshold || f.count}</p>
                  </div>
                  <div className="bg-dark-700/40 rounded-xl p-3 text-center">
                    <p className="text-xs text-gray-500 mb-1">Total Amount</p>
                    <p className="text-sm font-bold text-red-300">{fmt(f.amount, currencySymbol)}</p>
                  </div>
                </div>
                {f.recommendation && (
                  <div className="mt-3 bg-blue-500/10 border border-blue-500/20 rounded-xl p-3 text-xs text-blue-300">
                    {f.recommendation}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
