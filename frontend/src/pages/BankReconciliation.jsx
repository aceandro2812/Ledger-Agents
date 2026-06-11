import { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { 
  CreditCard, RefreshCw, FileDown, Upload, 
  Search, Filter, ArrowUpRight, ArrowDownLeft, Info
} from 'lucide-react';

function fmt(val, sym = 'Rs.') {
  return `${sym} ${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

const STATUS_BG = {
  MATCHED: 'bg-green-500/20 text-green-400 border border-green-500/30',
  GL_ONLY: 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30',
  BANK_ONLY: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
};

const CATEGORY_COLORS = {
  'Salary / Payroll': 'bg-pink-500/20 text-pink-400 border border-pink-500/30',
  'Rent & Infrastructure': 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30',
  'Utilities': 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30',
  'Taxes & Compliance': 'bg-red-500/20 text-red-400 border border-red-500/30',
  'Bank Charges & Interest': 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  'Cash Deposit / Withdrawal': 'bg-teal-500/20 text-teal-400 border border-teal-500/30',
  'Loan Repayments / Receipts': 'bg-purple-500/20 text-purple-400 border border-purple-500/30',
  'Travel & Office Expense': 'bg-orange-500/20 text-orange-400 border border-orange-500/30',
  'Vendor Payments': 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  'Customer Receipts': 'bg-green-500/20 text-green-400 border border-green-500/30',
  'Uncategorized': 'bg-gray-500/20 text-gray-400 border border-gray-500/30',
};

export default function BankReconciliation({ results, currencySymbol = 'Rs.' }) {
  const backendUrl = import.meta.env.VITE_API_URL || (window.location.port === '5173' ? 'http://localhost:8000' : '');
  const recon = results?.bank_reconciliation;

  // States
  const [directAnalysis, setDirectAnalysis] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [subTab, setSubTab] = useState(recon ? 'reconciliation' : 'categorization'); // 'categorization' | 'reconciliation'
  const [reconTab, setReconTab] = useState('matched'); // 'matched' | 'gl_only' | 'bank_only'
  
  // Search & Filter States
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [selectedType, setSelectedType] = useState('All'); // 'All' | 'Debit' | 'Credit'

  // Derive activeData functionally to avoid setting state inside an effect (avoids set-state-in-effect)
  let activeData = null;
  if (recon) {
    const txns = (recon.items || [])
      .filter(i => i.item_type === 'MATCHED' || i.item_type === 'BANK_ONLY')
      .map((item, idx) => ({
        row_idx: item.bank_row_idx || idx,
        date: item.date,
        narration: item.bank_narration || '',
        debit: item.is_debit ? Number(item.amount) : 0,
        credit: !item.is_debit ? Number(item.amount) : 0,
        category: item.category || 'Uncategorized',
        ref_no: '',
        bank_name: recon.bank_name || ''
      }));

    let totalD = 0;
    let totalC = 0;
    const catSum = {};
    txns.forEach(t => {
      totalD += t.debit;
      totalC += t.credit;
      catSum[t.category] = (catSum[t.category] || 0) + (t.debit > 0 ? t.debit : t.credit);
    });

    activeData = {
      bank_name: recon.bank_name,
      filename: recon.bank_file,
      total_transactions: txns.length,
      total_debits: totalD,
      total_credits: totalC,
      category_summary: catSum,
      transactions: txns
    };
  } else {
    activeData = directAnalysis;
  }

  const onDrop = async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return;
    setUploading(true);
    setError(null);

    const file = acceptedFiles[0];
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${backendUrl}/analyze/bank-statement`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Analysis failed');
      }

      const data = await res.json();
      setDirectAnalysis(data);
      setSubTab('categorization');
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

  const handleDownloadCSV = () => {
    if (!activeData || !activeData.transactions) return;
    
    // Process filtered transactions
    const allTxns = activeData.transactions;
    const txnsToDownload = allTxns.filter(t => {
      const matchesSearch = t.narration.toLowerCase().includes(searchTerm.toLowerCase()) || 
                            (t.ref_no && t.ref_no.toLowerCase().includes(searchTerm.toLowerCase()));
      const matchesCategory = selectedCategory === 'All' || t.category === selectedCategory;
      const matchesType = selectedType === 'All' || 
                          (selectedType === 'Debit' && t.debit > 0) || 
                          (selectedType === 'Credit' && t.credit > 0);
      return matchesSearch && matchesCategory && matchesType;
    });

    // Calculate totals for filtered transactions
    let totalDebits = 0;
    let totalCredits = 0;
    txnsToDownload.forEach(t => {
      totalDebits += t.debit || 0;
      totalCredits += t.credit || 0;
    });
    const netFlow = totalCredits - totalDebits;

    // Build CSV Content
    const headers = ['Date', 'Narration', 'Category', 'Debit (Withdrawal)', 'Credit (Deposit)', 'Balance', 'Bank Name'];
    const rows = txnsToDownload.map(t => [
      t.date,
      `"${t.narration.replace(/"/g, '""')}"`,
      t.category,
      t.debit || 0,
      t.credit || 0,
      t.balance || 0,
      t.bank_name || ''
    ]);

    // Append a spacer and a summary row
    rows.push(['', '', '', '', '', '', '']);
    rows.push([
      'TOTALS',
      `"${txnsToDownload.length} items"`,
      '',
      totalDebits,
      totalCredits,
      netFlow,
      ''
    ]);
    
    const csvContent = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    
    const catClean = selectedCategory.replace(/[^a-zA-Z0-9]/g, '_');
    const typeClean = selectedType;
    const baseName = activeData.filename ? activeData.filename.split('.')[0] : 'statement';
    link.setAttribute("download", `${baseName}_filtered_${catClean}_${typeClean}.csv`);
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // If no bank statement analyzed/reconciled yet, show upload zone
  if (!activeData && !recon) {
    return (
      <div className="space-y-6 max-w-4xl mx-auto py-6">
        <div>
          <h2 className="text-2xl font-bold text-white mb-1.5 flex items-center gap-2">
            <CreditCard className="w-6 h-6 text-blue-400" />
            Bank Statement Analysis & Recon
          </h2>
          <p className="text-sm text-gray-400">
            Upload your corporate bank statement (HDFC, SBI, ICICI, Axis, Kotak or standard CSV) to categorize transactions, analyze income/expenses, or match with General Ledger records.
          </p>
        </div>

        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-2xl p-16 flex flex-col justify-center items-center cursor-pointer transition-all duration-300 ${
            isDragActive
              ? 'border-blue-500 bg-blue-950/20'
              : 'border-dark-600 bg-dark-800 hover:border-dark-500 hover:bg-dark-800/80'
          }`}
        >
          <input {...getInputProps()} />
          <div className="p-4 bg-dark-700 rounded-full text-blue-400 mb-4 shadow-inner">
            <Upload className="w-10 h-10 animate-bounce" />
          </div>
          
          {uploading ? (
            <div className="text-center">
              <p className="text-lg font-bold text-white mb-2">Analyzing bank statement...</p>
              <p className="text-sm text-gray-400">Parsing structure & running categorization engine</p>
            </div>
          ) : isDragActive ? (
            <p className="text-lg font-bold text-blue-400">Drop statement here...</p>
          ) : (
            <div className="text-center">
              <p className="text-lg font-bold text-white mb-2">Drag & Drop bank statement here</p>
              <p className="text-sm text-gray-400 mb-6">Supports .xlsx, .xlsm, or .csv formats</p>
              <span className="bg-dark-700 border border-dark-600 text-blue-400 hover:bg-dark-600 text-sm font-semibold px-5 py-3 rounded-xl transition-colors">
                Select Statement File
              </span>
            </div>
          )}
        </div>

        {error && (
          <div className="bg-red-950/30 border border-red-500/50 rounded-xl p-4 flex gap-3 text-red-300">
            <Info className="w-5 h-5 flex-shrink-0" />
            <div>
              <h4 className="font-bold">Error</h4>
              <p className="text-sm">{error}</p>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Define lists for Reconciled views if recon exists
  const matchedList = recon ? (recon.items || []).filter((i) => i.item_type === 'MATCHED') : [];
  const glOnlyList = recon ? (recon.items || []).filter((i) => i.item_type === 'GL_ONLY') : [];
  const bankOnlyList = recon ? (recon.items || []).filter((i) => i.item_type === 'BANK_ONLY') : [];
  const matchRate = recon?.match_rate_pct != null ? recon.match_rate_pct : '—';

  // Process direct analysis transactions for filtering
  const allTxns = activeData?.transactions || [];
  const filteredTxns = allTxns.filter(t => {
    const matchesSearch = t.narration.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          (t.ref_no && t.ref_no.toLowerCase().includes(searchTerm.toLowerCase()));
    const matchesCategory = selectedCategory === 'All' || t.category === selectedCategory;
    const matchesType = selectedType === 'All' || 
                        (selectedType === 'Debit' && t.debit > 0) || 
                        (selectedType === 'Credit' && t.credit > 0);
    return matchesSearch && matchesCategory && matchesType;
  });

  // Calculate totals for filtered transactions
  let filteredDebits = 0;
  let filteredCredits = 0;
  filteredTxns.forEach(t => {
    filteredDebits += t.debit || 0;
    filteredCredits += t.credit || 0;
  });
  const filteredNetFlow = filteredCredits - filteredDebits;
  const isFiltered = searchTerm !== '' || selectedCategory !== 'All' || selectedType !== 'All';

  const categories = ['All', ...Object.keys(activeData?.category_summary || {})];

  return (
    <div className="space-y-6">
      {/* Header section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-dark-700 pb-5">
        <div>
          <h2 className="text-2xl font-bold text-white mb-1.5 flex items-center gap-2">
            <CreditCard className="w-6 h-6 text-emerald-400" />
            Bank Statement Suite
          </h2>
          <p className="text-sm text-gray-400">
            Statement: <strong className="text-white">{activeData?.filename || recon?.bank_file}</strong>
            {activeData?.bank_name && ` · Detected Bank: ${activeData.bank_name}`}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {activeData && (
            <button
              onClick={handleDownloadCSV}
              className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm px-4.5 py-2.5 rounded-xl flex items-center gap-2 transition-all shadow-md shadow-emerald-900/10"
            >
              <FileDown className="w-4 h-4" />
              Download Categorized CSV
            </button>
          )}
          <button
            onClick={() => {
              setDirectAnalysis(null);
              setError(null);
            }}
            className="bg-dark-800 hover:bg-dark-700 border border-dark-700 text-gray-300 font-bold text-sm px-4 py-2.5 rounded-xl flex items-center gap-2 transition-all"
          >
            <RefreshCw className="w-4 h-4" />
            Upload New File
          </button>
        </div>
      </div>

      {/* Main navigation subtabs */}
      <div className="flex gap-2 border-b border-dark-800 pb-px">
        <button
          onClick={() => setSubTab('categorization')}
          className={`pb-3 text-sm font-bold border-b-2 px-4 transition-all ${
            subTab === 'categorization'
              ? 'border-blue-500 text-blue-400'
              : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          Statement Categorization
        </button>
        {recon && (
          <button
            onClick={() => setSubTab('reconciliation')}
            className={`pb-3 text-sm font-bold border-b-2 px-4 transition-all ${
              subTab === 'reconciliation'
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-400 hover:text-white'
            }`}
          >
            Books vs Bank Reconciliation ({matchRate}% match)
          </button>
        )}
      </div>

      {/* SUBTAB 1: STATEMENT CATEGORIZATION */}
      {subTab === 'categorization' && activeData && (
        <div className="space-y-6">
          {/* Quick Guide Card */}
          <div className="bg-blue-500/5 border border-blue-500/20 rounded-2xl p-5 flex gap-4 text-sm text-gray-300">
            <div className="p-3 bg-blue-500/10 text-blue-400 rounded-xl h-fit">
              <Info className="w-5.5 h-5.5" />
            </div>
            <div className="space-y-1.5 flex-1">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-white text-base">Quick Guide: Bank Statement Analysis</h4>
                <span className="text-[10px] bg-blue-500/20 text-blue-400 px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider">Independent Workspace</span>
              </div>
              <p className="text-xs text-gray-400 leading-relaxed">
                This workspace operates independently of the General Ledger audit. Use the search bar to locate specific transaction narrations, or filter by category and type (Debits/Credits).
              </p>
              <ul className="list-disc pl-4 space-y-1 text-xs text-gray-400">
                <li><strong>Dynamic Calculations:</strong> The KPI cards and the bottom **TOTALS** row update in real time to reflect the active filters.</li>
                <li><strong>Filtered Download:</strong> Clicking **Download Categorized CSV** exports only your filtered results and appends matching totals at the bottom.</li>
              </ul>
            </div>
          </div>

          {/* KPI Dashboard */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4.5 flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 mb-0.5">Total Deposits (Credits)</p>
                <p className="text-2xl font-bold text-green-400">
                  {fmt(isFiltered ? filteredCredits : activeData.total_credits, currencySymbol)}
                </p>
                {isFiltered && (
                  <p className="text-[10px] text-gray-500 mt-0.5">
                    Overall: {fmt(activeData.total_credits, currencySymbol)}
                  </p>
                )}
              </div>
              <div className="p-3 bg-green-500/10 border border-green-500/20 text-green-400 rounded-xl">
                <ArrowUpRight className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4.5 flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 mb-0.5">Total Withdrawals (Debits)</p>
                <p className="text-2xl font-bold text-red-400">
                  {fmt(isFiltered ? filteredDebits : activeData.total_debits, currencySymbol)}
                </p>
                {isFiltered && (
                  <p className="text-[10px] text-gray-500 mt-0.5">
                    Overall: {fmt(activeData.total_debits, currencySymbol)}
                  </p>
                )}
              </div>
              <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl">
                <ArrowDownLeft className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4.5 flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 mb-0.5">Net cash flow</p>
                <p className={`text-2xl font-bold ${
                  (isFiltered ? filteredNetFlow : (activeData.total_credits - activeData.total_debits)) >= 0 
                    ? 'text-green-400' 
                    : 'text-red-400'
                }`}>
                  {fmt(isFiltered ? filteredNetFlow : (activeData.total_credits - activeData.total_debits), currencySymbol)}
                </p>
                {isFiltered && (
                  <p className="text-[10px] text-gray-500 mt-0.5">
                    Overall: {fmt(activeData.total_credits - activeData.total_debits, currencySymbol)}
                  </p>
                )}
              </div>
              <div className={`p-3 rounded-xl ${
                (isFiltered ? filteredNetFlow : (activeData.total_credits - activeData.total_debits)) >= 0 
                  ? 'bg-green-500/10 border-green-500/20 text-green-400' 
                  : 'bg-red-500/10 border-red-500/20 text-red-400'
              }`}>
                <RefreshCw className="w-5 h-5" />
              </div>
            </div>

            <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4.5 flex items-center justify-between">
              <div>
                <p className="text-xs text-gray-500 mb-0.5">Transactions Analyzed</p>
                <p className="text-2xl font-bold text-white">
                  {isFiltered ? filteredTxns.length : activeData.total_transactions}
                </p>
                {isFiltered && (
                  <p className="text-[10px] text-gray-500 mt-0.5">
                    Overall: {activeData.total_transactions}
                  </p>
                )}
              </div>
              <div className="p-3 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-xl">
                <CreditCard className="w-5 h-5" />
              </div>
            </div>
          </div>

          {/* Category Share & Aggregations */}
          <div className="bg-dark-800 border border-dark-700 rounded-2xl p-6">
            <h3 className="text-base font-bold text-white mb-4">Financial Categorization Share</h3>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Left Column: Visual progress list */}
              <div className="space-y-3.5">
                {Object.entries(activeData.category_summary)
                  .sort((a, b) => b[1] - a[1])
                  .map(([cat, amount]) => {
                    const totalVal = activeData.total_debits + activeData.total_credits;
                    const pct = totalVal > 0 ? (amount / totalVal * 100).toFixed(1) : 0;
                    return (
                      <div key={cat} className="space-y-1">
                        <div className="flex justify-between text-xs font-semibold">
                          <span className="text-gray-300">{cat}</span>
                          <span className="text-gray-400">{fmt(amount, currencySymbol)} ({pct}%)</span>
                        </div>
                        <div className="w-full bg-dark-900 rounded-full h-2">
                          <div 
                            className="bg-blue-500 h-2 rounded-full transition-all duration-500" 
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
              </div>

              {/* Right Column: Quick category cards */}
              <div className="grid grid-cols-2 gap-3.5">
                {Object.entries(activeData.category_summary)
                  .sort((a, b) => b[1] - a[1])
                  .slice(0, 6)
                  .map(([cat, amount]) => (
                    <div key={cat} className="bg-dark-900/60 border border-dark-600/40 p-3.5 rounded-xl">
                      <span className={`text-[10px] uppercase font-extrabold tracking-wider px-2 py-0.5 rounded-md ${CATEGORY_COLORS[cat] || 'bg-gray-800 text-gray-400 border border-gray-700'}`}>
                        {cat}
                      </span>
                      <p className="text-base font-bold text-white mt-2.5">{fmt(amount, currencySymbol)}</p>
                    </div>
                  ))}
              </div>
            </div>
          </div>

          {/* Filtering and transaction listing */}
          <div className="bg-dark-800 border border-dark-700 rounded-2xl p-6">
            <div className="flex flex-col md:flex-row gap-4 justify-between items-center mb-6">
              <h3 className="text-base font-bold text-white">Categorized Transactions Ledger</h3>
              
              <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
                {/* Search */}
                <div className="relative flex-1 md:w-60">
                  <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-500" />
                  <input
                    type="text"
                    placeholder="Search narration..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 text-sm bg-dark-900 border border-dark-600 rounded-xl text-white focus:outline-none focus:border-blue-500 transition-colors"
                  />
                </div>

                {/* Category Dropdown */}
                <div className="relative">
                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="appearance-none bg-dark-900 border border-dark-600 rounded-xl px-4 py-2 pr-8 text-sm text-gray-300 focus:outline-none focus:border-blue-500 cursor-pointer"
                  >
                    {categories.map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                  <Filter className="absolute right-3 top-3 w-3.5 h-3.5 text-gray-500 pointer-events-none" />
                </div>

                {/* Type filter */}
                <div className="relative">
                  <select
                    value={selectedType}
                    onChange={(e) => setSelectedType(e.target.value)}
                    className="appearance-none bg-dark-900 border border-dark-600 rounded-xl px-4 py-2 pr-8 text-sm text-gray-300 focus:outline-none focus:border-blue-500 cursor-pointer"
                  >
                    <option value="All">All Types</option>
                    <option value="Debit">Withdrawals (Debits)</option>
                    <option value="Credit">Deposits (Credits)</option>
                  </select>
                  <Filter className="absolute right-3 top-3 w-3.5 h-3.5 text-gray-500 pointer-events-none" />
                </div>
              </div>
            </div>

            <div className="overflow-x-auto rounded-xl border border-dark-700">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 bg-dark-900 border-b border-dark-700 text-xs uppercase tracking-wide">
                    <th className="py-3 px-4 text-left">Date</th>
                    <th className="py-3 px-4 text-left">Narration</th>
                    <th className="py-3 px-4 text-center">Category</th>
                    <th className="py-3 px-4 text-right">Withdrawal (Debit)</th>
                    <th className="py-3 px-4 text-right">Deposit (Credit)</th>
                    <th className="py-3 px-4 text-right">Balance</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTxns.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-10 text-center text-gray-500">No transactions match the filters.</td>
                    </tr>
                  ) : (
                    <>
                      {filteredTxns.map((item, i) => (
                        <tr key={i} className="border-b border-dark-700/50 hover:bg-dark-700/20 text-gray-300">
                          <td className="py-3.5 px-4 font-semibold text-xs whitespace-nowrap">{item.date}</td>
                          <td className="py-3.5 px-4 text-xs font-medium max-w-sm break-all text-gray-400">{item.narration}</td>
                          <td className="py-3.5 px-4 text-center">
                            <span className={`text-[10px] font-extrabold uppercase px-2.5 py-0.5 rounded-lg whitespace-nowrap ${CATEGORY_COLORS[item.category] || 'bg-gray-800 text-gray-400 border border-gray-700'}`}>
                              {item.category}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-right font-bold text-red-400/90">{item.debit > 0 ? fmt(item.debit, currencySymbol) : '—'}</td>
                          <td className="py-3.5 px-4 text-right font-bold text-green-400/90">{item.credit > 0 ? fmt(item.credit, currencySymbol) : '—'}</td>
                          <td className="py-3.5 px-4 text-right text-gray-400">{item.balance != null ? fmt(item.balance, currencySymbol) : '—'}</td>
                        </tr>
                      ))}
                      <tr className="bg-dark-900/40 border-t-2 border-dark-700 font-semibold text-white">
                        <td className="py-4 px-4 text-xs font-bold text-blue-400">TOTALS</td>
                        <td className="py-4 px-4 text-xs text-gray-400">{filteredTxns.length} items</td>
                        <td className="py-4 px-4"></td>
                        <td className="py-4 px-4 text-right font-bold text-red-400/90">{filteredDebits > 0 ? fmt(filteredDebits, currencySymbol) : '—'}</td>
                        <td className="py-4 px-4 text-right font-bold text-green-400/90">{filteredCredits > 0 ? fmt(filteredCredits, currencySymbol) : '—'}</td>
                        <td className="py-4 px-4 text-right font-bold text-blue-400/90">{fmt(filteredNetFlow, currencySymbol)}</td>
                      </tr>
                    </>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SUBTAB 2: BOOKS VS BANK RECONCILIATION */}
      {subTab === 'reconciliation' && recon && (
        <div className="space-y-6">
          {/* Summary stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4 text-center">
              <p className="text-xs text-gray-500 mb-1">Match Rate</p>
              <p className="text-3xl font-bold text-green-300">{matchRate}%</p>
            </div>
            <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4 text-center">
              <p className="text-xs text-gray-500 mb-1">Matched</p>
              <p className="text-3xl font-bold text-white">{matchedList.length}</p>
            </div>
            <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4 text-center">
              <p className="text-xs text-gray-500 mb-1">GL Only (Unrecorded Bank)</p>
              <p className="text-3xl font-bold text-yellow-300">{glOnlyList.length}</p>
            </div>
            <div className="bg-dark-800 border border-dark-700 rounded-2xl p-4 text-center">
              <p className="text-xs text-gray-500 mb-1">Bank Only (Unrecorded Books)</p>
              <p className="text-3xl font-bold text-blue-300">{bankOnlyList.length}</p>
            </div>
          </div>

          {/* Recon specific tabs */}
          <div className="flex gap-2.5">
            {[
              { key: 'matched', label: `Matched (${matchedList.length})`, color: 'bg-green-600' },
              { key: 'gl_only', label: `GL Only (${glOnlyList.length})`, color: 'bg-yellow-600' },
              { key: 'bank_only', label: `Bank Only (${bankOnlyList.length})`, color: 'bg-blue-600' },
            ].map((t) => (
              <button
                key={t.key}
                onClick={() => setReconTab(t.key)}
                className={`text-sm font-semibold px-4 py-2.5 rounded-xl transition-all ${
                  reconTab === t.key ? `${t.color} text-white` : 'bg-dark-800 text-gray-400 hover:bg-dark-700 border border-dark-700'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Table */}
          {(() => {
            const rows = reconTab === 'matched' ? matchedList : reconTab === 'gl_only' ? glOnlyList : bankOnlyList;
            return (
              <div className="overflow-x-auto rounded-2xl border border-dark-700">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-gray-500 bg-dark-800 border-b border-dark-700 text-xs uppercase tracking-wide">
                      <th className="py-3 px-4 text-left">GL Date</th>
                      <th className="py-3 px-4 text-left">Bank Date</th>
                      <th className="py-3 px-4 text-left">Narration</th>
                      <th className="py-3 px-4 text-center">Category</th>
                      <th className="py-3 px-4 text-right">GL Amount</th>
                      <th className="py-3 px-4 text-right">Bank Amount</th>
                      <th className="py-3 px-4 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-10 text-center text-gray-500">No reconciliation records found in this category.</td>
                      </tr>
                    ) : (
                      rows.map((item, i) => (
                        <tr key={i} className="border-b border-dark-700/50 hover:bg-dark-700/20 text-gray-300">
                          <td className="py-3.5 px-4 font-semibold text-xs">{item.date || '—'}</td>
                          <td className="py-3.5 px-4 font-semibold text-xs">{item.date || '—'}</td>
                          <td className="py-3.5 px-4 text-xs max-w-sm text-gray-400">
                            {item.item_type === 'GL_ONLY' ? (item.gl_narration || '—') : (item.bank_narration || '—')}
                          </td>
                          <td className="py-3.5 px-4 text-center">
                            <span className={`text-[10px] font-extrabold uppercase px-2 py-0.5 rounded-lg ${CATEGORY_COLORS[item.category] || 'bg-gray-800 text-gray-400'}`}>
                              {item.category}
                            </span>
                          </td>
                          <td className="py-3.5 px-4 text-right font-bold">{item.gl_row_idx !== null ? fmt(item.amount, currencySymbol) : '—'}</td>
                          <td className="py-3.5 px-4 text-right font-bold">{item.bank_row_idx !== null ? fmt(item.amount, currencySymbol) : '—'}</td>
                          <td className="py-3.5 px-4 text-center">
                            <span className={`text-xs font-bold px-2.5 py-1 rounded-lg ${STATUS_BG[item.item_type] || ''}`}>
                              {item.item_type?.replace('_', ' ')}
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
      )}
    </div>
  );
}
