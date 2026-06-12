import { useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { 
  Users, AlertCircle, Clock, Search, ChevronUp, ChevronDown, 
  ArrowUpDown, TrendingDown, CheckCircle, Upload, 
  RefreshCw, Info, Loader2, History, Play
} from 'lucide-react';

const BUCKETS = ['0-30', '31-60', '61-90', '91-180', '181-365', '>365'];

const BUCKET_STYLE = {
  '0-30':     'bg-green-500/10 text-green-400 border border-green-500/20',
  '31-60':    'bg-yellow-500/10 text-yellow-400 border border-yellow-500/20',
  '61-90':    'bg-yellow-600/10 text-yellow-500 border border-yellow-600/20',
  '91-180':   'bg-orange-500/10 text-orange-400 border border-orange-500/20',
  '181-365':  'bg-red-500/10 text-red-400 border border-red-500/20',
  '>365':     'bg-red-700/20 text-red-500 border border-red-700/20',
};

export default function CreditorsLedger() {
  const backendUrl = import.meta.env.VITE_API_URL || (window.location.port === '5173' ? 'http://localhost:8000' : '');

  // Local state for direct uploads
  const [directAnalysis, setDirectAnalysis] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  // Sorting & Filtering
  const [search, setSearch] = useState('');
  const [sortField, setSortField] = useState('outstanding_abs');
  const [sortAsc, setSortAsc] = useState(false);

  // History States
  const [pastAudits, setPastAudits] = useState([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

  useEffect(() => {
    if (!directAnalysis) {
      setLoadingHistory(true);
      fetch(`${backendUrl}/audits`)
        .then((res) => res.json())
        .then((data) => {
          setPastAudits(data.filter((a) => a.audit_type === 'creditors'));
          setLoadingHistory(false);
        })
        .catch((err) => {
          console.error('Failed to load past audits', err);
          setLoadingHistory(false);
        });
    }
  }, [directAnalysis]);

  const handleLoadPastAudit = async (auditId) => {
    setLoadingHistory(true);
    setError(null);
    try {
      const res = await fetch(`${backendUrl}/audit/${auditId}`);
      if (!res.ok) {
        throw new Error('Failed to load past audit');
      }
      const data = await res.json();
      setDirectAnalysis(data.results);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingHistory(false);
    }
  };

  // Determine active aging list — local state only, never bleeds GL results
  const activeAging = directAnalysis?.aging ?? [];
  const currencySymbol = directAnalysis?.currency_symbol ?? 'Rs.';

  // Identify creditors: prefer backend is_creditor flag, fall back to heuristic
  const creditors = activeAging.filter((p) => {
    if (p.is_creditor !== undefined) return p.is_creditor === true;
    return Number(p.total_credits) > 0 || Number(p.outstanding_balance) < 0;
  });

  const fmt = (val) => {
    const abs = Math.abs(Number(val));
    return `${currencySymbol} ${abs.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const onDrop = async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return;
    setUploading(true);
    setError(null);

    const file = acceptedFiles[0];
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${backendUrl}/analyze/creditors`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Analysis failed');
      }

      const data = await res.json();
      setDirectAnalysis(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel.sheet.macroEnabled.12': ['.xlsm'],
      'text/csv': ['.csv']
    },
    multiple: false
  });

  // ── Direct Creditors Upload screen if empty ──────────────────────────────────────────
  if (!directAnalysis) {
    return (
      <div className="space-y-6 max-w-4xl mx-auto py-6">
        <div>
          <h2 className="text-2xl font-bold text-white mb-1.5 flex items-center gap-2">
            <Users className="w-6 h-6 text-purple-400" />
            Creditors Ledger Audit (AP Suite)
          </h2>
          <p className="text-sm text-gray-400">
            Upload your accounts payable or creditors purchase ledger dump to calculate invoice aging, identify vendor credit buckets, and monitor outstanding payments.
          </p>
        </div>

        {uploading ? (
          <div className="border border-dark-700 bg-dark-800 rounded-2xl p-16 flex flex-col justify-center items-center shadow-xl">
            <div className="p-4 bg-purple-500/10 border border-purple-500/20 text-purple-400 rounded-2xl mb-4">
              <Loader2 className="w-10 h-10 animate-spin text-purple-400" />
            </div>
            <div className="text-center max-w-sm">
              <h3 className="text-lg font-bold text-white mb-1.5">Analyzing Creditors Ledger...</h3>
              <p className="text-sm text-gray-400">
                Parsing transaction mappings, matching settlements chronologically via FIFO, and computing outstanding aging buckets.
              </p>
              <div className="w-48 bg-dark-900 h-1.5 rounded-full mt-5 mx-auto overflow-hidden">
                <div className="bg-gradient-to-r from-purple-500 to-indigo-500 h-full rounded-full animate-pulse w-full" />
              </div>
            </div>
          </div>
        ) : (
          <div
            {...getRootProps()}
            className={`border-2 border-dashed rounded-2xl p-16 flex flex-col justify-center items-center cursor-pointer transition-all duration-300 ${
              isDragActive
                ? 'border-purple-500 bg-purple-950/20'
                : 'border-dark-600 bg-dark-800 hover:border-purple-500/50 hover:bg-dark-800/80'
            }`}
          >
            <input {...getInputProps()} />
            <div className="p-4 bg-dark-700 rounded-full text-purple-400 mb-4 shadow-inner">
              <Upload className="w-10 h-10 animate-pulse" />
            </div>
            {isDragActive ? (
              <p className="text-lg font-bold text-purple-400">Drop creditors ledger here...</p>
            ) : (
              <div className="text-center">
                <p className="text-lg font-bold text-white mb-2">Drag & Drop creditors ledger here</p>
                <p className="text-sm text-gray-400 mb-6">Supports .xlsx, .xlsm, or .csv formats</p>
                <span className="bg-dark-700 border border-dark-600 text-purple-400 hover:bg-dark-600 text-sm font-semibold px-5 py-3 rounded-xl transition-colors">
                  Select Ledger File
                </span>
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="bg-red-950/30 border border-red-500/50 rounded-xl p-4 flex gap-3 text-red-300">
            <Info className="w-5 h-5 flex-shrink-0" />
            <div>
              <h4 className="font-bold">Error</h4>
              <p className="text-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Audit History Card */}
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-6 shadow-xl mt-6">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <History className="w-5 h-5 text-gray-400" />
            Local Creditors Audit History
          </h3>
          
          {loadingHistory ? (
            <div className="flex justify-center items-center py-6 gap-2 text-sm text-gray-500">
              <Loader2 className="w-4.5 h-4.5 animate-spin text-purple-400" />
              <span>Loading history...</span>
            </div>
          ) : pastAudits.length === 0 ? (
            <p className="text-sm text-gray-500 italic">No historical creditors ledgers analyzed on this machine.</p>
          ) : (
            <div className="max-h-48 overflow-y-auto space-y-2 pr-1">
              {pastAudits.map((a) => (
                <div
                  key={a.id}
                  onClick={() => a.status === 'completed' && handleLoadPastAudit(a.id)}
                  className={`flex items-center justify-between p-3.5 bg-dark-900 border rounded-xl transition-all ${
                    a.status === 'completed' 
                      ? 'border-dark-600 cursor-pointer hover:border-purple-500 hover:bg-dark-900/60' 
                      : 'border-red-900/50 opacity-60'
                  }`}
                >
                  <div className="flex-1 min-w-0 pr-4 text-left">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <h4 className="text-sm font-semibold text-white truncate max-w-[180px] sm:max-w-xs" title={a.filename}>
                        {a.filename}
                      </h4>
                      <span className="text-[9px] font-extrabold px-1.5 py-0.5 rounded border whitespace-nowrap bg-purple-500/10 text-purple-450 border-purple-500/20">
                        CREDITORS AP
                      </span>
                    </div>
                    <span className="text-xs text-gray-500 block">
                      {new Date(a.created_at).toLocaleString()}
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    <span className={`text-xs px-2.5 py-1 rounded-full font-bold ${
                      a.status === 'completed'
                        ? 'bg-green-950/40 text-green-400 border border-green-800/40'
                        : a.status === 'failed'
                        ? 'bg-red-950/40 text-red-400 border border-red-800/40'
                        : 'bg-yellow-950/40 text-yellow-400 border border-yellow-800/40'
                    }`}>
                      {a.status.toUpperCase()}
                    </span>
                    {a.status === 'completed' && (
                      <Play className="w-4 h-4 text-purple-400 hover:text-purple-300" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // ── KPI calculations ─────────────────────────────────────────────────────────
  const totalAP = creditors.reduce((s, p) => s + Math.abs(Number(p.outstanding_balance)), 0);
  const overdueAP = creditors.reduce((s, p) => {
    const b = p.aging_buckets ?? {};
    return s + ['31-60', '61-90', '91-180', '181-365', '>365'].reduce((bs, k) => bs + Number(b[k] ?? 0), 0);
  }, 0);
  const criticalAP = creditors.reduce((s, p) => {
    const b = p.aging_buckets ?? {};
    return s + ['181-365', '>365'].reduce((bs, k) => bs + Number(b[k] ?? 0), 0);
  }, 0);
  const largestCreditor = creditors.length > 0
    ? creditors.reduce((a, b) => Math.abs(Number(a.outstanding_balance)) >= Math.abs(Number(b.outstanding_balance)) ? a : b)
    : null;
  const zeroPaymentCount = creditors.filter((p) => p.flag_zero_payments).length;
  const unsettledOpeningCount = creditors.filter((p) => p.flag_unsettled_opening).length;
  const overduePercent = totalAP > 0 ? ((overdueAP / totalAP) * 100).toFixed(1) : '0.0';

  // ── Sort & Filter ─────────────────────────────────────────────────────────────
  const displayed = creditors
    .filter((p) => (p.party || '').toLowerCase().includes(search.toLowerCase()))
    .map((p) => ({ ...p, outstanding_abs: Math.abs(Number(p.outstanding_balance)) }))
    .sort((a, b) => {
      let av, bv;
      if (sortField === 'party') {
        const aParty = a.party || '';
        const bParty = b.party || '';
        return sortAsc ? aParty.localeCompare(bParty) : bParty.localeCompare(aParty);
      }
      if (BUCKETS.includes(sortField)) {
        av = Number(a.aging_buckets?.[sortField] ?? 0);
        bv = Number(b.aging_buckets?.[sortField] ?? 0);
      } else {
        av = a[sortField] ?? 0;
        bv = b[sortField] ?? 0;
      }
      return sortAsc ? av - bv : bv - av;
    });

  const handleSort = (field) => {
    if (sortField === field) setSortAsc(!sortAsc);
    else { setSortField(field); setSortAsc(false); }
  };

  const SortIcon = ({ field }) => {
    if (sortField !== field) return <ArrowUpDown className="w-3 h-3 opacity-30 inline ml-1" />;
    return sortAsc
      ? <ChevronUp className="w-3 h-3 text-purple-400 inline ml-1" />
      : <ChevronDown className="w-3 h-3 text-purple-400 inline ml-1" />;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-dark-700 pb-5">
        <div>
          <h2 className="text-2xl font-bold text-white mb-1 flex items-center gap-2">
            <Users className="w-6 h-6 text-purple-400" />
            Creditors Ledger
            <span className="text-sm font-normal text-gray-500 ml-1">(AP Analysis)</span>
          </h2>
          <p className="text-sm text-gray-500">
            {creditors.length} creditors analysed · Accounts Payable aging and vendor payment review
          </p>
        </div>

        <div>
          <button
            onClick={() => {
              setDirectAnalysis(null);
              setError(null);
            }}
            className="bg-dark-800 hover:bg-dark-700 border border-dark-700 text-gray-300 font-bold text-sm px-4 py-2.5 rounded-xl flex items-center gap-2 transition-all"
          >
            <RefreshCw className="w-4 h-4" />
            Upload New Ledger
          </button>
        </div>
      </div>

      {creditors.length === 0 ? (
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-16 text-center flex flex-col items-center justify-center gap-4">
          <div className="p-4 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-2xl">
            <Info className="w-8 h-8" />
          </div>
          <div className="max-w-md mx-auto">
            <h3 className="text-lg font-bold text-white mb-2">No Creditors Found</h3>
            <p className="text-sm text-gray-400">
              The uploaded ledger does not contain any parties with creditor characteristics (accounts with net credits or negative outstanding balances).
            </p>
            <p className="text-xs text-gray-500 mt-2">
              Please check if you uploaded a debtors/receivables ledger by mistake.
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* Quick Guide Card */}
          <div className="bg-purple-500/5 border border-purple-500/20 rounded-2xl p-5 flex gap-4 text-sm text-gray-300">
        <div className="p-3 bg-purple-500/10 text-purple-400 rounded-xl h-fit">
          <Info className="w-5.5 h-5.5" />
        </div>
        <div className="space-y-1.5 flex-1">
          <div className="flex items-center justify-between">
            <h4 className="font-bold text-white text-base">Quick Guide: Creditors (AP) Ledger Audit</h4>
            <span className="text-[10px] bg-purple-500/20 text-purple-400 px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider">Independent Workspace</span>
          </div>
          <p className="text-xs text-gray-400 leading-relaxed">
            This workspace processes Accounts Payable data independently. Once you upload a creditors ledger dump:
          </p>
          <ul className="list-disc pl-4 space-y-1 text-xs text-gray-400">
            <li><strong>FIFO Settlement:</strong> Payments are matched to purchase invoices chronologically to compute true aging.</li>
            <li><strong>Outstanding Buckets:</strong> Balances are bucketed across standard intervals to track potential overdue liability.</li>
            <li><strong>Risk Flags:</strong> Identifies vendors with zero payment runs or carried forward opening balances requiring investigation.</li>
          </ul>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-dark-800 border border-purple-500/20 rounded-xl p-4">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider mb-1.5">Total AP Outstanding</p>
          <p className="text-xl font-bold text-white">{fmt(totalAP)}</p>
          <p className="text-xs text-gray-500 mt-1">{creditors.length} vendor{creditors.length !== 1 ? 's' : ''}</p>
        </div>

        <div className={`bg-dark-800 border rounded-xl p-4 ${overdueAP > 0 ? 'border-red-500/30' : 'border-dark-700'}`}>
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider mb-1.5">Overdue AP (&gt;30 days)</p>
          <p className={`text-xl font-bold ${overdueAP > 0 ? 'text-red-400' : 'text-green-400'}`}>{fmt(overdueAP)}</p>
          <p className="text-xs text-gray-500 mt-1">{overduePercent}% of total AP</p>
        </div>

        <div className={`bg-dark-800 border rounded-xl p-4 ${criticalAP > 0 ? 'border-red-700/40' : 'border-dark-700'}`}>
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider mb-1.5">Critical Overdue (&gt;180d)</p>
          <p className={`text-xl font-bold ${criticalAP > 0 ? 'text-red-500' : 'text-gray-400'}`}>{fmt(criticalAP)}</p>
          <p className="text-xs text-gray-500 mt-1">Potential supplier disputes</p>
        </div>

        <div className="bg-dark-800 border border-dark-700 rounded-xl p-4">
          <p className="text-xs text-gray-400 font-semibold uppercase tracking-wider mb-1.5">Largest Vendor</p>
          <p className="text-sm font-bold text-purple-300 truncate" title={largestCreditor ? largestCreditor.party : 'None'}>
            {largestCreditor ? largestCreditor.party : 'None'}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            {largestCreditor ? `${fmt(largestCreditor.outstanding_balance)} outstanding` : 'N/A'}
          </p>
        </div>
      </div>

      {/* Alert flags */}
      {(zeroPaymentCount > 0 || unsettledOpeningCount > 0) && (
        <div className="flex flex-wrap gap-3">
          {zeroPaymentCount > 0 && (
            <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm px-4 py-2.5 rounded-xl font-semibold">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {zeroPaymentCount} vendor{zeroPaymentCount !== 1 ? 's' : ''} — zero payments in audit period
              <span className="text-xs font-normal text-amber-500">(possible dormant payables)</span>
            </div>
          )}
          {unsettledOpeningCount > 0 && (
            <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/20 text-red-400 text-sm px-4 py-2.5 rounded-xl font-semibold">
              <Clock className="w-4 h-4 flex-shrink-0" />
              {unsettledOpeningCount} vendor{unsettledOpeningCount !== 1 ? 's' : ''} — unsettled opening balance carried forward
            </div>
          )}
        </div>
      )}

      {/* AP Aging Schedule table */}
      <div className="bg-dark-800 border border-dark-700 rounded-2xl overflow-hidden">
        <div className="p-4 border-b border-dark-700 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <TrendingDown className="w-4 h-4 text-purple-400" />
              AP Aging Schedule
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">FIFO-matched outstanding payables by age bucket</p>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 pointer-events-none" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search vendor…"
              className="bg-dark-900 border border-dark-600 rounded-lg pl-9 pr-3 py-2 text-sm text-white focus:outline-none focus:border-purple-500 w-52 transition-colors"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-dark-700 bg-dark-900/30">
                {[
                  { key: 'party', label: 'Vendor / Party' },
                  ...BUCKETS.map((b) => ({ key: b, label: b + ' days' })),
                  { key: 'outstanding_abs', label: 'AP Outstanding' },
                ].map((col) => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider cursor-pointer hover:text-white select-none whitespace-nowrap"
                  >
                    {col.label}
                    <SortIcon field={col.key} />
                  </th>
                ))}
              </tr>
            </thead>

            <tbody className="divide-y divide-dark-700/50">
              {displayed.map((p) => (
                <tr key={p.party} className="hover:bg-dark-700/30 transition-colors group">
                  <td className="px-4 py-3 font-semibold text-white max-w-[200px]">
                    <span className="truncate block" title={p.party}>{p.party}</span>
                    <div className="flex gap-1 mt-0.5">
                      {p.flag_unsettled_opening && (
                        <span className="text-[10px] bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded font-bold">O/P PENDING</span>
                      )}
                      {p.flag_zero_payments && (
                        <span className="text-[10px] bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded font-bold">NO PAYMENTS</span>
                      )}
                    </div>
                  </td>

                  {BUCKETS.map((bucket) => {
                    const amt = Number(p.aging_buckets?.[bucket] ?? 0);
                    return (
                      <td key={bucket} className="px-4 py-3 whitespace-nowrap">
                        {amt > 0 ? (
                          <span className={`px-2 py-1 rounded text-xs font-semibold ${BUCKET_STYLE[bucket]}`}>
                            {fmt(amt)}
                          </span>
                        ) : (
                          <span className="text-gray-700 text-xs">—</span>
                        )}
                      </td>
                    );
                  })}

                  <td className="px-4 py-3 font-bold text-purple-300 whitespace-nowrap">
                    {fmt(p.outstanding_balance)}
                  </td>
                </tr>
              ))}

              {displayed.length === 0 && (
                <tr>
                  <td colSpan={BUCKETS.length + 2} className="text-center py-12 text-gray-500 text-sm">
                    No vendors match your search.
                  </td>
                </tr>
              )}
            </tbody>

            {displayed.length > 0 && (
              <tfoot>
                <tr className="border-t-2 border-dark-600 bg-dark-900/50">
                  <td className="px-4 py-3 text-xs font-bold text-gray-300 uppercase tracking-wider">
                    Total ({displayed.length} vendor{displayed.length !== 1 ? 's' : ''})
                  </td>
                  {BUCKETS.map((bucket) => {
                    const total = displayed.reduce((s, p) => s + Number(p.aging_buckets?.[bucket] ?? 0), 0);
                    return (
                      <td key={bucket} className="px-4 py-3 text-xs font-bold text-gray-300 whitespace-nowrap">
                        {total > 0 ? fmt(total) : '—'}
                      </td>
                    );
                  })}
                  <td className="px-4 py-3 text-sm font-bold text-purple-300 whitespace-nowrap">
                    {fmt(displayed.reduce((s, p) => s + Math.abs(Number(p.outstanding_balance)), 0))}
                  </td>
                </tr>
              </tfoot>
            )}
          </table>
        </div>
      </div>

      {/* Vendors fully cleared section */}
      {(() => {
        const cleared = creditors.filter((p) => Math.abs(Number(p.outstanding_balance)) < 0.01);
        if (cleared.length === 0) return null;
        return (
          <div className="bg-dark-800 border border-green-500/20 rounded-xl p-4">
            <p className="text-sm font-semibold text-green-400 flex items-center gap-2">
              <CheckCircle className="w-4 h-4" />
              {cleared.length} vendor{cleared.length !== 1 ? 's' : ''} fully settled (zero outstanding balance)
            </p>
          </div>
        );
      })()}
        </>
      )}
    </div>
  );
}
