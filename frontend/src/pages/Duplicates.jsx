import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Copy, ShieldAlert, ArrowRight, ExternalLink } from 'lucide-react';

export default function Duplicates({ results, currencySymbol = 'Rs.', onDownloadExcel }) {
  const { duplicates = [] } = results;
  const [filter, setFilter] = useState('ALL');
  const [expandedRows, setExpandedRows] = useState({});

  const toggleRow = (id) => {
    setExpandedRows((prev) => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const filteredDups = duplicates.filter((d) => {
    if (filter === 'ALL') return true;
    return d.confidence === filter;
  });

  const getConfidenceBadge = (conf) => {
    if (conf === 'HIGH') return 'bg-red-500/20 text-red-400 border border-red-500/30';
    if (conf === 'MEDIUM') return 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30';
    return 'bg-green-500/20 text-green-400 border border-green-500/30';
  };

  const fmt = (val) => `${currencySymbol} ${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  return (
    <div className="space-y-6">
      {/* Title block */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-white mb-1.5 flex items-center gap-2">
            <Copy className="w-6 h-6 text-blue-400" />
            Duplicate Payment Detective
          </h2>
          <p className="text-sm text-gray-400">Identifies exact matches, near-duplicates, same-voucher overlaps, and round numbers.</p>
        </div>

        <button
          onClick={onDownloadExcel}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-colors flex items-center gap-2"
        >
          <ExternalLink className="w-4 h-4" />
          Export styled Excel
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2.5">
        {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map((t) => (
          <button
            key={t}
            onClick={() => setFilter(t)}
            className={`text-sm font-semibold px-4 py-2 rounded-xl transition-all ${
              filter === t
                ? 'bg-blue-600 text-white'
                : 'bg-dark-800 text-gray-400 hover:bg-dark-700/60 border border-dark-700'
            }`}
          >
            {t} ({t === 'ALL' ? duplicates.length : duplicates.filter((d) => d.confidence === t).length})
          </button>
        ))}
      </div>

      {/* Table Card */}
      <div className="bg-dark-800 border border-dark-700 rounded-2xl shadow-xl overflow-hidden">
        {filteredDups.length === 0 ? (
          <div className="text-center text-gray-500 italic py-16">No duplicate payments found matching filter criteria.</div>
        ) : (
          <div className="divide-y divide-dark-700">
            {/* Table Header */}
            <div className="grid grid-cols-12 gap-4 px-6 py-4 text-xs font-bold text-gray-400 uppercase tracking-wider bg-dark-950/20">
              <div className="col-span-3">Party Name</div>
              <div className="col-span-3">Pass / Pattern</div>
              <div className="col-span-2 text-right">Amount</div>
              <div className="col-span-2 text-center">Confidence</div>
              <div className="col-span-1 text-center">Days Delta</div>
              <div className="col-span-1"></div>
            </div>

            {/* Table Body */}
            {filteredDups.map((d) => {
              const isExpanded = !!expandedRows[d.finding_id];
              const tA_amt = d.transaction_A?.amount || 0;
              
              return (
                <div key={d.finding_id} className="transition-colors hover:bg-dark-700/10">
                  <div
                    onClick={() => toggleRow(d.finding_id)}
                    className="grid grid-cols-12 gap-4 px-6 py-4 items-center cursor-pointer text-sm"
                  >
                    <div className="col-span-3 font-bold text-white truncate max-w-[200px]" title={d.party}>
                      {d.party}
                    </div>
                    <div className="col-span-3">
                      <span className="text-gray-400 text-xs block mb-0.5">Pass {d.pass_number}</span>
                      <span className="text-white font-medium">{d.pass_name}</span>
                    </div>
                    <div className="col-span-2 text-right font-bold text-white">
                      {fmt(tA_amt)}
                    </div>
                    <div className="col-span-2 text-center">
                      <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold ${getConfidenceBadge(d.confidence)}`}>
                        {d.confidence}
                      </span>
                    </div>
                    <div className="col-span-1 text-center text-gray-300 font-semibold">
                      {d.pass_number === 5 ? '-' : `${d.delta_days} d`}
                    </div>
                    <div className="col-span-1 flex justify-end text-gray-400">
                      {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                    </div>
                  </div>

                  {/* Expandable Content Panel */}
                  {isExpanded && (
                    <div className="px-6 pb-6 pt-2 bg-dark-950/30 border-t border-dark-700/50 space-y-5">
                      {/* Grid comparison (if Pass 5, might only have A) */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Transaction A Card */}
                        <div className="bg-dark-800/80 border border-dark-700 rounded-xl p-4 space-y-3">
                          <h4 className="text-xs font-bold text-blue-400 uppercase tracking-wider">Transaction A (Source Record)</h4>
                          <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                            <span className="text-gray-400">Excel Row No. :</span>
                            <span className="text-white font-semibold">Row {d.transaction_A.row_idx}</span>
                            <span className="text-gray-400">Voucher / Ref:</span>
                            <span className="text-white font-mono">{d.transaction_A.voucher_no || 'N/A'}</span>
                            <span className="text-gray-400">Transaction Date:</span>
                            <span className="text-white">{d.transaction_A.date}</span>
                            <span className="text-gray-400">Amount Status:</span>
                            <span className="text-white font-bold">{fmt(d.transaction_A.amount)} ({d.transaction_A.type})</span>
                            <span className="text-gray-400">Contra Ledger:</span>
                            <span className="text-white truncate max-w-[140px]" title={d.transaction_A.contra_ledger}>{d.transaction_A.contra_ledger || 'N/A'}</span>
                          </div>
                        </div>

                        {/* Transaction B Card */}
                        {d.pass_number !== 5 ? (
                          <div className="bg-dark-800/80 border border-dark-700 rounded-xl p-4 space-y-3">
                            <h4 className="text-xs font-bold text-blue-400 uppercase tracking-wider">Transaction B (Duplicate Match)</h4>
                            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                              <span className="text-gray-400">Excel Row No. :</span>
                              <span className="text-white font-semibold">Row {d.transaction_B.row_idx}</span>
                              <span className="text-gray-400">Voucher / Ref:</span>
                              <span className="text-white font-mono">{d.transaction_B.voucher_no || 'N/A'}</span>
                              <span className="text-gray-400">Transaction Date:</span>
                              <span className="text-white">{d.transaction_B.date}</span>
                              <span className="text-gray-400">Amount Status:</span>
                              <span className="text-white font-bold">{fmt(d.transaction_B.amount)} ({d.transaction_B.type})</span>
                              <span className="text-gray-400">Contra Ledger:</span>
                              <span className="text-white truncate max-w-[140px]" title={d.transaction_B.contra_ledger}>{d.transaction_B.contra_ledger || 'N/A'}</span>
                            </div>
                          </div>
                        ) : (
                          <div className="bg-dark-800/20 border border-dashed border-dark-700 rounded-xl p-4 flex flex-col justify-center items-center text-center">
                            <ShieldAlert className="w-8 h-8 text-yellow-500/60 mb-2" />
                            <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">Round Number Warning</h4>
                            <p className="text-xs text-gray-500 max-w-[200px]">This is an informational warning. No pairing transaction was matched.</p>
                          </div>
                        )}
                      </div>

                      {/* Auditor Recommendation */}
                      <div className="bg-blue-950/20 border border-blue-800/30 rounded-xl p-4 text-sm flex gap-3 text-blue-300">
                        <ArrowRight className="w-5 h-5 flex-shrink-0 mt-0.5" />
                        <div>
                          <h5 className="font-bold mb-1">Auditor Recommendation</h5>
                          <p className="text-blue-300/90 leading-relaxed">{d.recommendation}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
