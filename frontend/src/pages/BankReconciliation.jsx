import React, { useState } from 'react';
import { CreditCard, CheckCircle, RefreshCw } from 'lucide-react';

function fmt(val, sym = 'Rs.') {
  return `${sym} ${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const STATUS_BG = {
  MATCHED: 'bg-green-500/20 text-green-400 border border-green-500/30',
  GL_ONLY: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  BANK_ONLY: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
};

export default function BankReconciliation({ results, currencySymbol = 'Rs.' }) {
  const recon = results?.bank_reconciliation;
  const [tab, setTab] = useState('matched');

  if (!recon) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <RefreshCw className="w-12 h-12 text-gray-500 mb-4" />
        <p className="text-lg font-semibold text-white mb-2">No Bank Statement Attached</p>
        <p className="text-sm text-gray-400">
          Attach a bank statement file using the <span className="text-blue-400 font-semibold">BANK_STATEMENT</span> tag on the Upload page to enable reconciliation.
        </p>
      </div>
    );
  }

  const matched = (recon.items || []).filter((i) => i.status === 'MATCHED');
  const glOnly = (recon.items || []).filter((i) => i.status === 'GL_ONLY');
  const bankOnly = (recon.items || []).filter((i) => i.status === 'BANK_ONLY');

  const matchRate = recon.match_rate != null ? (recon.match_rate * 100).toFixed(1) : '—';

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-1.5 flex items-center gap-2">
          <CreditCard className="w-6 h-6 text-emerald-400" />
          Bank Reconciliation
        </h2>
        <p className="text-sm text-gray-400">
          Matches GL entries against bank statement transactions within ±3 days / ±Rs. 1. Highlights timing differences and missing entries.
        </p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Match Rate</p>
          <p className="text-3xl font-bold text-green-300">{matchRate}%</p>
        </div>
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Matched</p>
          <p className="text-3xl font-bold text-white">{matched.length}</p>
        </div>
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">GL Only</p>
          <p className="text-3xl font-bold text-yellow-300">{glOnly.length}</p>
        </div>
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Bank Only</p>
          <p className="text-3xl font-bold text-blue-300">{bankOnly.length}</p>
        </div>
      </div>

      {/* Bank name */}
      {recon.bank_name && (
        <p className="text-sm text-gray-400">
          Bank detected: <span className="text-white font-semibold">{recon.bank_name}</span>
          {recon.statement_period && ` · Period: ${recon.statement_period}`}
        </p>
      )}

      {/* Tabs */}
      <div className="flex gap-2.5">
        {[
          { key: 'matched', label: `Matched (${matched.length})`, color: 'bg-green-600' },
          { key: 'gl_only', label: `GL Only (${glOnly.length})`, color: 'bg-yellow-600' },
          { key: 'bank_only', label: `Bank Only (${bankOnly.length})`, color: 'bg-blue-600' },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`text-sm font-semibold px-4 py-2 rounded-xl transition-all ${
              tab === t.key ? `${t.color} text-white` : 'bg-dark-800 text-gray-400 hover:bg-dark-700/60 border border-dark-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Table */}
      {(() => {
        const rows = tab === 'matched' ? matched : tab === 'gl_only' ? glOnly : bankOnly;
        return (
          <div className="overflow-x-auto rounded-2xl border border-dark-700">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 bg-dark-800 border-b border-dark-700 text-xs uppercase tracking-wide">
                  <th className="py-3 px-4 text-left">GL Date</th>
                  <th className="py-3 px-4 text-left">Bank Date</th>
                  <th className="py-3 px-4 text-left">Narration</th>
                  <th className="py-3 px-4 text-right">GL Amount</th>
                  <th className="py-3 px-4 text-right">Bank Amount</th>
                  <th className="py-3 px-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-10 text-center text-gray-500">No entries</td>
                  </tr>
                ) : (
                  rows.map((item, i) => (
                    <tr key={i} className="border-b border-dark-700/50 hover:bg-dark-700/20 text-gray-300">
                      <td className="py-3 px-4">{item.gl_date || '—'}</td>
                      <td className="py-3 px-4">{item.bank_date || '—'}</td>
                      <td className="py-3 px-4 text-xs text-gray-400 max-w-xs truncate">{item.narration || item.description || '—'}</td>
                      <td className="py-3 px-4 text-right">{item.gl_amount != null ? fmt(item.gl_amount, currencySymbol) : '—'}</td>
                      <td className="py-3 px-4 text-right">{item.bank_amount != null ? fmt(item.bank_amount, currencySymbol) : '—'}</td>
                      <td className="py-3 px-4 text-center">
                        <span className={`text-xs font-bold px-2.5 py-1 rounded-lg ${STATUS_BG[item.status] || ''}`}>
                          {item.status?.replace('_', ' ')}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        );
      })()}
    </div>
  );
}
