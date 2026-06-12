import React, { useState } from 'react';
import { ShieldAlert, Search, ArrowUpDown, HelpCircle } from 'lucide-react';

export default function Aging({ results, currencySymbol = 'Rs.' }) {
  const rawAging = results?.aging ?? [];
  // GL mode: show only debtors (AR) — creditors have their own dedicated mode
  const aging = rawAging.filter((p) => !p.is_creditor);
  const [searchTerm, setSearchTerm] = useState('');
  const [viewMode, setViewMode] = useState('amount'); // 'amount' or 'count'
  const [sortField, setSortField] = useState('outstanding_balance');
  const [sortAsc, setSortAsc] = useState(false);

  // Helper to count bills by bucket
  const getBillCountByBucket = (bills, minAge, maxAge) => {
    return bills.filter((b) => {
      const age = b.age_days;
      if (minAge !== null && age < minAge) return false;
      if (maxAge !== null && age > maxAge) return false;
      return b.outstanding_amount > 0;
    }).length;
  };

  const handleSort = (field) => {
    if (sortField === field) {
      setSortAsc(!sortAsc);
    } else {
      setSortField(field);
      setSortAsc(false);
    }
  };

  const fmt = (val) => `${currencySymbol} ${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  // Filter and Sort data
  const processedData = aging
    .filter((a) => a.party.toLowerCase().includes(searchTerm.toLowerCase()))
    .sort((a, b) => {
      let aVal = 0;
      let bVal = 0;

      if (sortField === 'party') {
        aVal = a.party.toLowerCase();
        bVal = b.party.toLowerCase();
        return sortAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      } else if (sortField === 'outstanding_balance') {
        aVal = a.outstanding_balance;
        bVal = b.outstanding_balance;
      } else {
        // bucket fields
        aVal = a.aging_buckets?.[sortField] || 0;
        bVal = b.aging_buckets?.[sortField] || 0;
      }

      return sortAsc ? aVal - bVal : bVal - aVal;
    });

  const getBucketCell = (a, bucketName, minAge, maxAge) => {
    const amt = a.aging_buckets?.[bucketName] || 0;
    if (viewMode === 'amount') {
      if (amt === 0) return <span className="text-gray-600">-</span>;
      return <span className="text-white font-semibold">{fmt(amt)}</span>;
    } else {
      const count = getBillCountByBucket(a.outstanding_bills || [], minAge, maxAge);
      if (count === 0) return <span className="text-gray-600">-</span>;
      return <span className="text-white font-semibold">{count} bills</span>;
    }
  };

  const getBucketStyle = (a, bucketName) => {
    const amt = a.aging_buckets?.[bucketName] || 0;
    if (amt === 0) return '';
    if (bucketName === '0-30') return 'bg-green-500/10 text-green-400 border border-green-500/20';
    if (bucketName === '31-60' || bucketName === '61-90') return 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20';
    if (bucketName === '91-180') return 'bg-orange-500/10 text-orange-400 border border-orange-500/20';
    return 'bg-red-500/10 text-red-400 border border-red-500/20';
  };

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-2xl font-bold text-white mb-1.5 flex items-center gap-2">
          <ShieldAlert className="w-6 h-6 text-green-400" />
          Outstanding Aging Schedule
        </h2>
        <p className="text-sm text-gray-400">Aging buckets representing outstanding payables or receivables matching FIFO bill schedules.</p>
      </div>

      {/* Controls Bar */}
      <div className="flex flex-col md:flex-row gap-4 items-stretch md:items-center justify-between">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search party by name..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-dark-800 border border-dark-700 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors"
          />
        </div>

        {/* View Toggle */}
        <div className="flex bg-dark-850 p-1 border border-dark-700 rounded-xl">
          <button
            onClick={() => setViewMode('amount')}
            className={`text-xs font-semibold px-4.5 py-2 rounded-lg transition-all ${
              viewMode === 'amount'
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Outstanding Amount
          </button>
          <button
            onClick={() => setViewMode('count')}
            className={`text-xs font-semibold px-4.5 py-2 rounded-lg transition-all ${
              viewMode === 'count'
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Outstanding Bills Count
          </button>
        </div>
      </div>

      {/* Schedule Table */}
      <div className="bg-dark-800 border border-dark-700 rounded-2xl shadow-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left border-collapse">
            <thead>
              <tr className="border-b border-dark-700 text-gray-400 bg-dark-950/20 text-xs font-bold uppercase tracking-wider">
                <th onClick={() => handleSort('party')} className="py-4 px-4 cursor-pointer hover:text-white select-none">
                  <div className="flex items-center gap-1">Party Name <ArrowUpDown className="w-3.5 h-3.5" /></div>
                </th>
                <th onClick={() => handleSort('outstanding_balance')} className="py-4 px-4 cursor-pointer hover:text-white text-right select-none">
                  <div className="flex items-center justify-end gap-1">Net Outstanding <ArrowUpDown className="w-3.5 h-3.5" /></div>
                </th>
                <th onClick={() => handleSort('0-30')} className="py-4 px-4 cursor-pointer hover:text-white text-center select-none">
                  <div className="flex items-center justify-center gap-1">0-30 d <ArrowUpDown className="w-3.5 h-3.5" /></div>
                </th>
                <th onClick={() => handleSort('31-60')} className="py-4 px-4 cursor-pointer hover:text-white text-center select-none">
                  <div className="flex items-center justify-center gap-1">31-60 d <ArrowUpDown className="w-3.5 h-3.5" /></div>
                </th>
                <th onClick={() => handleSort('61-90')} className="py-4 px-4 cursor-pointer hover:text-white text-center select-none">
                  <div className="flex items-center justify-center gap-1">61-90 d <ArrowUpDown className="w-3.5 h-3.5" /></div>
                </th>
                <th onClick={() => handleSort('91-180')} className="py-4 px-4 cursor-pointer hover:text-white text-center select-none">
                  <div className="flex items-center justify-center gap-1">91-180 d <ArrowUpDown className="w-3.5 h-3.5" /></div>
                </th>
                <th onClick={() => handleSort('181-365')} className="py-4 px-4 cursor-pointer hover:text-white text-center select-none">
                  <div className="flex items-center justify-center gap-1">181-365 d <ArrowUpDown className="w-3.5 h-3.5" /></div>
                </th>
                <th onClick={() => handleSort('>365')} className="py-4 px-4 cursor-pointer hover:text-white text-center select-none">
                  <div className="flex items-center justify-center gap-1">&gt;365 d <ArrowUpDown className="w-3.5 h-3.5" /></div>
                </th>
                <th className="py-4 px-4 text-center">Alerts</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-700/50">
              {processedData.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-gray-500 italic">No aging schedule records found.</td>
                </tr>
              ) : (
                processedData.map((a) => {
                  const flags = [];
                  if (a.flag_unsettled_opening) flags.push("Opening");
                  if (a.flag_zero_payments) flags.push("Zero Payments");
                  
                  return (
                    <tr key={a.party} className="hover:bg-dark-700/20 transition-colors">
                      <td className="py-4 px-4 font-bold text-white max-w-[200px] truncate">{a.party}</td>
                      <td className="py-4 px-4 text-right font-bold text-white">
                        {fmt(a.outstanding_balance)}
                      </td>
                      
                      {/* Bucket cells with style helpers */}
                      <td className="py-4 px-4 text-center">
                        <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-semibold ${getBucketStyle(a, '0-30')}`}>
                          {getBucketCell(a, '0-30', 0, 30)}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-center">
                        <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-semibold ${getBucketStyle(a, '31-60')}`}>
                          {getBucketCell(a, '31-60', 31, 60)}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-center">
                        <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-semibold ${getBucketStyle(a, '61-90')}`}>
                          {getBucketCell(a, '61-90', 61, 90)}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-center">
                        <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-semibold ${getBucketStyle(a, '91-180')}`}>
                          {getBucketCell(a, '91-180', 91, 180)}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-center">
                        <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-semibold ${getBucketStyle(a, '181-365')}`}>
                          {getBucketCell(a, '181-365', 181, 365)}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-center">
                        <span className={`inline-block px-2.5 py-1 rounded-lg text-xs font-semibold ${getBucketStyle(a, '>365')}`}>
                          {getBucketCell(a, '>365', 366, null)}
                        </span>
                      </td>

                      {/* Alerts column */}
                      <td className="py-4 px-4 text-center">
                        {a.flag_unsettled_opening || a.flag_zero_payments ? (
                          <div className="flex items-center justify-center gap-1">
                            {a.flag_unsettled_opening && (
                              <span className="text-[10px] bg-red-950/40 text-red-400 border border-red-800/40 px-2 py-0.5 rounded font-extrabold" title="Opening balance remains unsettled">
                                OPENING
                              </span>
                            )}
                            {a.flag_zero_payments && (
                              <span className="text-[10px] bg-yellow-950/40 text-yellow-400 border border-yellow-800/40 px-2 py-0.5 rounded font-bold" title="No payments received in period">
                                ZERO PAY
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
