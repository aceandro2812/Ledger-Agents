import React, { useState } from 'react';
import { FileText, CheckCircle, ChevronDown, ChevronUp } from 'lucide-react';

const SEVERITY_BG = {
  HIGH: 'bg-red-500/20 text-red-400 border border-red-500/30',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  LOW: 'bg-green-500/20 text-green-400 border border-green-500/30',
  CRITICAL: 'bg-red-700/30 text-red-300 border border-red-600/40',
};

function fmt(val, sym = 'Rs.') {
  return `${sym} ${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export default function GSTCompliance({ results, currencySymbol = 'Rs.' }) {
  const findings = results?.gst_tds ?? [];
  const [expanded, setExpanded] = useState(null);

  if (findings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <CheckCircle className="w-12 h-12 text-green-400 mb-4" />
        <p className="text-lg font-semibold text-white mb-2">No TDS Gaps Detected</p>
        <p className="text-sm text-gray-400">
          All qualifying payments appear to have TDS deducted, or no payments crossed threshold limits.
        </p>
      </div>
    );
  }

  const totalExpected = findings.reduce((s, f) => s + (f.expected_tds_amount || 0), 0);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-1.5 flex items-center gap-2">
          <FileText className="w-6 h-6 text-indigo-400" />
          GST / TDS Compliance
        </h2>
        <p className="text-sm text-gray-400">
          Identifies payments to vendors that may require TDS deduction under sections 194C, 194J, 194H, 194I, 194A, and 194Q,
          but where no TDS evidence was found in the ledger.
        </p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">TDS Gaps Found</p>
          <p className="text-3xl font-bold text-indigo-300">{findings.length}</p>
        </div>
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Total Payments at Risk</p>
          <p className="text-xl font-bold text-yellow-300">
            {fmt(findings.reduce((s, f) => s + (f.total_payment || 0), 0), currencySymbol)}
          </p>
        </div>
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Expected TDS Liability</p>
          <p className="text-xl font-bold text-red-300">{fmt(totalExpected, currencySymbol)}</p>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-2xl border border-dark-700">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 bg-dark-800 border-b border-dark-700 text-xs uppercase tracking-wide">
              <th className="py-3 px-4 text-left">Section</th>
              <th className="py-3 px-4 text-left">Section Name</th>
              <th className="py-3 px-4 text-left">Party</th>
              <th className="py-3 px-4 text-right">Total Payment</th>
              <th className="py-3 px-4 text-right">Rate</th>
              <th className="py-3 px-4 text-right">Expected TDS</th>
              <th className="py-3 px-4 text-center">Severity</th>
              <th className="py-3 px-4 text-center">Details</th>
            </tr>
          </thead>
          <tbody>
            {findings.map((f) => (
              <React.Fragment key={f.finding_id}>
                <tr className="border-b border-dark-700/50 hover:bg-dark-700/20 text-gray-300">
                  <td className="py-3 px-4 font-bold text-indigo-300">{f.tds_section}</td>
                  <td className="py-3 px-4 text-gray-400 text-xs">{f.section_name || '—'}</td>
                  <td className="py-3 px-4 font-medium text-white">{f.party}</td>
                  <td className="py-3 px-4 text-right">{fmt(f.total_payment || 0, currencySymbol)}</td>
                  <td className="py-3 px-4 text-right text-gray-400">{f.tds_rate}%</td>
                  <td className="py-3 px-4 text-right font-bold text-red-300">{fmt(f.expected_tds_amount || 0, currencySymbol)}</td>
                  <td className="py-3 px-4 text-center">
                    <span className={`text-xs font-bold px-2.5 py-1 rounded-lg ${SEVERITY_BG[f.severity] || SEVERITY_BG.MEDIUM}`}>
                      {f.severity}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-center">
                    <button
                      onClick={() => setExpanded(expanded === f.finding_id ? null : f.finding_id)}
                      className="text-gray-500 hover:text-white"
                    >
                      {expanded === f.finding_id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </td>
                </tr>
                {expanded === f.finding_id && (
                  <tr className="border-b border-dark-700/50 bg-dark-700/10">
                    <td colSpan={8} className="px-6 py-4">
                      <p className="text-sm text-gray-300 mb-3">{f.description}</p>
                      {f.transactions && f.transactions.length > 0 && (
                        <table className="w-full text-xs mt-2">
                          <thead>
                            <tr className="text-gray-500 border-b border-dark-700/60 uppercase tracking-wide">
                              <th className="py-1.5 text-left">Date</th>
                              <th className="py-1.5 text-right">Amount</th>
                              <th className="py-1.5 text-left">Narration</th>
                            </tr>
                          </thead>
                          <tbody>
                            {f.transactions.slice(0, 10).map((t, i) => (
                              <tr key={i} className="border-b border-dark-700/30 text-gray-300">
                                <td className="py-1">{t.date}</td>
                                <td className="py-1 text-right text-red-300">{fmt(t.amount || 0, currencySymbol)}</td>
                                <td className="py-1 text-gray-400">{t.narration}</td>
                              </tr>
                            ))}
                            {f.transactions.length > 10 && (
                              <tr>
                                <td colSpan={3} className="py-1 text-gray-500 text-center">
                                  +{f.transactions.length - 10} more transactions
                                </td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      )}
                      {f.recommendation && (
                        <div className="mt-3 bg-blue-500/10 border border-blue-500/20 rounded-xl p-3 text-xs text-blue-300">
                          <span className="font-semibold">Recommendation: </span>{f.recommendation}
                        </div>
                      )}
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
