import React, { useState } from 'react';
import { ShoppingCart, CheckCircle, ChevronDown, ChevronUp } from 'lucide-react';

const SEVERITY_BG = {
  HIGH: 'bg-red-500/20 text-red-400 border border-red-500/30',
  MEDIUM: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  LOW: 'bg-green-500/20 text-green-400 border border-green-500/30',
  CRITICAL: 'bg-red-700/30 text-red-300 border border-red-600/40',
};

const CHECK_LABEL = {
  YEAR_END_LOADING: 'Year-End Loading',
  PERSONAL_EXPENSE: 'Personal Expense',
  CASH_ABOVE_10K: 'Cash Payment > Rs.10k (Sec 40A(3))',
  ROUND_NUMBER_EXPENSE: 'Round Number Expense',
  VENDOR_CONCENTRATION: 'Vendor Concentration',
  SPLIT_PAYMENT: 'Split Payment (TDS Bypass)',
  PREPAID_UNSETTLED: 'Prepaid / Unsettled',
  SUSPENSE_ABUSE: 'Suspense Account Abuse',
  EXPENSE_WITHOUT_GST: 'B2B Expense Without GST',
};

function fmt(val, sym = 'Rs.') {
  return `${sym} ${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function GroupCard({ checkType, items, currencySymbol }) {
  const [open, setOpen] = useState(false);
  const totalAmt = items.reduce((s, i) => s + (i.amount || 0), 0);
  const maxSev = items.some((i) => i.severity === 'HIGH' || i.severity === 'CRITICAL')
    ? 'HIGH'
    : items.some((i) => i.severity === 'MEDIUM')
    ? 'MEDIUM'
    : 'LOW';

  return (
    <div className="bg-dark-800 border border-dark-700 rounded-2xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-dark-700/40 transition-colors text-left"
      >
        <div className="flex items-center gap-3">
          <ShoppingCart className="w-5 h-5 text-orange-400" />
          <div>
            <p className="font-semibold text-white text-sm">{CHECK_LABEL[checkType] || checkType}</p>
            <p className="text-xs text-gray-400 mt-0.5">{items.length} findings · {fmt(totalAmt, currencySymbol)}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-xs font-bold px-2.5 py-1 rounded-lg ${SEVERITY_BG[maxSev]}`}>{maxSev}</span>
          {open ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
        </div>
      </button>
      {open && (
        <div className="px-5 pb-4 border-t border-dark-700/60">
          <div className="overflow-x-auto mt-3">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 border-b border-dark-700 uppercase tracking-wide">
                  <th className="py-2 text-left">Date</th>
                  <th className="py-2 text-left">Party / Account</th>
                  <th className="py-2 text-right">Amount</th>
                  <th className="py-2 text-left">Description</th>
                  <th className="py-2 text-center">Sev</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, i) => (
                  <tr key={i} className="border-b border-dark-700/40 text-gray-300">
                    <td className="py-1.5">{item.date || '—'}</td>
                    <td className="py-1.5 font-medium">{item.party || item.account || '—'}</td>
                    <td className="py-1.5 text-right text-red-300">{fmt(item.amount || 0, currencySymbol)}</td>
                    <td className="py-1.5 text-gray-400 max-w-xs truncate">{item.description || item.narration || '—'}</td>
                    <td className="py-1.5 text-center">
                      <span className={`px-1.5 py-0.5 rounded text-xs font-bold ${SEVERITY_BG[item.severity] || SEVERITY_BG.MEDIUM}`}>
                        {item.severity?.[0] || '?'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ExpenseScrutiny({ results, currencySymbol = 'Rs.' }) {
  const findings = results?.expense_scrutiny ?? [];

  if (findings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center">
        <CheckCircle className="w-12 h-12 text-green-400 mb-4" />
        <p className="text-lg font-semibold text-white mb-2">No Expense Irregularities Found</p>
        <p className="text-sm text-gray-400">All expense transactions pass the scrutiny checks.</p>
      </div>
    );
  }

  // Group by check_type
  const groups = findings.reduce((acc, f) => {
    const key = f.check_type || 'OTHER';
    (acc[key] = acc[key] || []).push(f);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white mb-1.5 flex items-center gap-2">
          <ShoppingCart className="w-6 h-6 text-orange-400" />
          Expense Scrutiny
        </h2>
        <p className="text-sm text-gray-400">
          9-point expense audit: personal expenses, cash payments above Rs.10k (Sec 40A(3)), vendor concentration,
          split payments, suspense abuse, and B2B invoices lacking GST.
        </p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Total Flags</p>
          <p className="text-3xl font-bold text-orange-300">{findings.length}</p>
        </div>
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Check Types</p>
          <p className="text-3xl font-bold text-white">{Object.keys(groups).length}</p>
        </div>
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4 text-center">
          <p className="text-xs text-gray-500 mb-1">Total Flagged Amount</p>
          <p className="text-xl font-bold text-red-300">
            {fmt(findings.reduce((s, f) => s + (f.amount || 0), 0), currencySymbol)}
          </p>
        </div>
      </div>

      {/* Group cards */}
      <div className="space-y-4">
        {Object.entries(groups).map(([checkType, items]) => (
          <GroupCard key={checkType} checkType={checkType} items={items} currencySymbol={currencySymbol} />
        ))}
      </div>
    </div>
  );
}
