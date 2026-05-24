import React, { useState, useEffect, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import { FileUp, Calendar, Coins, History, AlertTriangle, Play, Plus, X, Paperclip, CheckCircle2, ChevronRight, Users } from 'lucide-react';

// Creditors ledger has its own dedicated upload zone — NOT in this generic list
const LEDGER_TYPES = [
  { value: 'BANK_STATEMENT', label: 'Bank Statement' },
  { value: 'DEBTORS_LEDGER', label: 'Debtors Ledger' },
  { value: 'SALES_LEDGER', label: 'Sales Ledger' },
  { value: 'EXPENSE_LEDGER', label: 'Expense Ledger' },
];

function AttachFileRow({ auditId, backendUrl, onAttached }) {
  const [file, setFile] = useState(null);
  const [ledgerType, setLedgerType] = useState('BANK_STATEMENT');
  const [status, setStatus] = useState('idle'); // idle | uploading | done | error
  const [errMsg, setErrMsg] = useState('');
  const inputRef = useRef();

  const handleAttach = async () => {
    if (!file) return;
    setStatus('uploading');
    setErrMsg('');
    const fd = new FormData();
    fd.append('file', file);
    fd.append('ledger_type', ledgerType);
    try {
      const res = await fetch(`${backendUrl}/audit/${auditId}/attach`, { method: 'POST', body: fd });
      if (!res.ok) {
        const e = await res.json();
        throw new Error(e.detail || 'Attach failed');
      }
      setStatus('done');
      onAttached(ledgerType);
    } catch (e) {
      setStatus('error');
      setErrMsg(e.message);
    }
  };

  if (status === 'done') {
    return (
      <div className="flex items-center gap-2 text-green-400 text-sm font-semibold py-2">
        <CheckCircle2 className="w-4 h-4" />
        {LEDGER_TYPES.find((l) => l.value === ledgerType)?.label} attached
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2 items-center">
        <select
          value={ledgerType}
          onChange={(e) => setLedgerType(e.target.value)}
          className="bg-dark-900 border border-dark-600 text-sm text-white rounded-lg px-2 py-2 focus:outline-none focus:border-blue-500"
        >
          {LEDGER_TYPES.map((lt) => (
            <option key={lt.value} value={lt.value}>{lt.label}</option>
          ))}
        </select>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xlsm,.csv"
          className="hidden"
          onChange={(e) => setFile(e.target.files[0] || null)}
        />
        <button
          onClick={() => inputRef.current.click()}
          className="bg-dark-700 border border-dark-600 text-gray-300 hover:text-white text-sm px-3 py-2 rounded-lg transition-colors truncate max-w-[160px]"
        >
          {file ? file.name : 'Choose file…'}
        </button>
        <button
          onClick={handleAttach}
          disabled={!file || status === 'uploading'}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-semibold px-3 py-2 rounded-lg transition-colors"
        >
          {status === 'uploading' ? 'Attaching…' : 'Attach'}
        </button>
      </div>
      {status === 'error' && <p className="text-xs text-red-400">{errMsg}</p>}
    </div>
  );
}

// ── Dedicated Creditors Ledger upload widget ─────────────────────────────────
function CreditorFileSection({ auditId, backendUrl, onAttached, alreadyAttached }) {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState('idle'); // idle | uploading | done | error
  const [errMsg, setErrMsg] = useState('');
  const inputRef = useRef();

  const handleAttach = async () => {
    if (!file) return;
    setStatus('uploading');
    setErrMsg('');
    const fd = new FormData();
    fd.append('file', file);
    fd.append('ledger_type', 'CREDITORS_LEDGER');
    try {
      const res = await fetch(`${backendUrl}/audit/${auditId}/attach`, { method: 'POST', body: fd });
      if (!res.ok) {
        const e = await res.json();
        throw new Error(e.detail || 'Attach failed');
      }
      setStatus('done');
      onAttached('CREDITORS_LEDGER');
    } catch (e) {
      setStatus('error');
      setErrMsg(e.message);
    }
  };

  if (alreadyAttached || status === 'done') {
    return (
      <div className="flex items-center gap-2 text-green-400 text-sm font-semibold py-1">
        <CheckCircle2 className="w-4 h-4" />
        Creditors Ledger attached successfully
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2 items-center">
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xlsm,.csv"
          className="hidden"
          onChange={(e) => setFile(e.target.files[0] || null)}
        />
        <button
          onClick={() => inputRef.current.click()}
          className="flex-1 bg-dark-900 border border-purple-500/30 hover:border-purple-400/60 text-gray-300 hover:text-white text-sm px-3 py-2.5 rounded-lg transition-colors truncate text-left"
        >
          {file ? file.name : 'Choose creditors ledger file (.xlsx / .csv)…'}
        </button>
        <button
          onClick={handleAttach}
          disabled={!file || status === 'uploading'}
          className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white text-sm font-bold px-4 py-2.5 rounded-lg transition-colors whitespace-nowrap"
        >
          {status === 'uploading' ? 'Attaching…' : 'Attach'}
        </button>
      </div>
      {status === 'error' && <p className="text-xs text-red-400">{errMsg}</p>}
    </div>
  );
}

export default function Upload({ onUploadSuccess, onLoadPastAudit }) {
  const [asOnDate, setAsOnDate] = useState('');
  const [currencySymbol, setCurrencySymbol] = useState('Rs.');
  const [duplicateWindowDays, setDuplicateWindowDays] = useState(7);
  const [uploadedAuditId, setUploadedAuditId] = useState(null);
  const [attachRows, setAttachRows] = useState([0]); // each element is a unique key
  const [attachedTypes, setAttachedTypes] = useState([]);
  const [auditConfig, setAuditConfig] = useState(null);
  const [holidays, setHolidays] = useState([
    '2026-01-26', // Republic Day
    '2026-05-01', // May Day
    '2026-08-15', // Independence Day
    '2026-10-02', // Gandhi Jayanti
    '2026-12-25'  // Christmas Day
  ]);
  const [newHoliday, setNewHoliday] = useState('');
  const [pastAudits, setPastAudits] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  const backendUrl = import.meta.env.VITE_API_URL || (window.location.port === '5173' ? 'http://localhost:8000' : '');

  // Fetch past audits
  useEffect(() => {
    fetch(`${backendUrl}/audits`)
      .then((res) => res.json())
      .then((data) => setPastAudits(data))
      .catch((err) => console.error('Failed to load past audits', err));
  }, []);

  const onDrop = async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return;
    setUploading(true);
    setError(null);

    const file = acceptedFiles[0];
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${backendUrl}/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Upload failed');
      }

      const data = await res.json();
      const config = {
        asOnDate,
        currencySymbol,
        duplicateWindowDays,
        customHolidays: holidays
      };
      setUploadedAuditId(data.audit_id);
      setAuditConfig(config);
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

  const addHoliday = () => {
    if (newHoliday && !holidays.includes(newHoliday)) {
      setHolidays([...holidays, newHoliday].sort());
      setNewHoliday('');
    }
  };

  const removeHoliday = (dateToRemove) => {
    setHolidays(holidays.filter((h) => h !== dateToRemove));
  };

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Title */}
      <div className="mb-10 text-center">
        <h1 className="text-4xl font-extrabold tracking-tight text-white mb-2 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-300">
          GL Forensic Audit Ledger Suite
        </h1>
        <p className="text-gray-400 max-w-2xl mx-auto">
          Upload any General Ledger dump (Tally, SAP, Busy, Marg, CSV) to detect duplicate payments, anomalies, aging, and reconciliation discrepancies locally.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Configurations Column */}
        <div className="lg:col-span-1 bg-dark-800 border border-dark-700 rounded-2xl p-6 shadow-xl">
          <h2 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
            <Coins className="w-5 h-5 text-blue-400" />
            Audit Parameters
          </h2>

          {/* As-On Date */}
          <div className="mb-5">
            <label className="block text-sm font-medium text-gray-300 mb-2 flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              As-on Date (for aging)
            </label>
            <input
              type="date"
              value={asOnDate}
              onChange={(e) => setAsOnDate(e.target.value)}
              className="w-full bg-dark-900 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500 transition-colors"
              placeholder="Default: last transaction date"
            />
          </div>

          {/* Currency */}
          <div className="mb-5">
            <label className="block text-sm font-medium text-gray-300 mb-2">Currency Symbol</label>
            <input
              type="text"
              value={currencySymbol}
              onChange={(e) => setCurrencySymbol(e.target.value)}
              className="w-full bg-dark-900 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>

          {/* Duplicate payment window */}
          <div className="mb-6">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Duplicate Window (days)
            </label>
            <input
              type="number"
              value={duplicateWindowDays}
              onChange={(e) => setDuplicateWindowDays(Number(e.target.value))}
              min={1}
              className="w-full bg-dark-900 border border-dark-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500 transition-colors"
            />
          </div>

          {/* Indian Public Holidays */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Public Holidays List (India Default)
            </label>
            <div className="flex gap-2 mb-3">
              <input
                type="date"
                value={newHoliday}
                onChange={(e) => setNewHoliday(e.target.value)}
                className="flex-1 bg-dark-900 border border-dark-600 rounded-lg px-2 py-1 text-sm text-white focus:outline-none focus:border-blue-500"
              />
              <button
                onClick={addHoliday}
                className="bg-blue-600 hover:bg-blue-700 text-white rounded-lg p-2 transition-colors"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>

            <div className="max-h-36 overflow-y-auto space-y-1.5 pr-1">
              {holidays.map((date) => (
                <div key={date} className="flex justify-between items-center bg-dark-900 border border-dark-600 px-3 py-1.5 rounded-lg text-sm">
                  <span className="text-gray-300">{date}</span>
                  <button onClick={() => removeHoliday(date)} className="text-gray-500 hover:text-red-400">
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Upload Zone Column */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          {/* Drag & Drop */}
          <div
            {...getRootProps()}
            className={`flex-1 min-h-[300px] border-2 border-dashed rounded-2xl p-10 flex flex-col justify-center items-center cursor-pointer transition-all duration-300 ${
              isDragActive
                ? 'border-blue-500 bg-blue-950/20'
                : 'border-dark-600 bg-dark-800 hover:border-dark-500 hover:bg-dark-800/80'
            }`}
          >
            <input {...getInputProps()} />
            <div className="p-4 bg-dark-700 rounded-full text-blue-400 mb-4 shadow-inner">
              <FileUp className="w-10 h-10 animate-pulse" />
            </div>
            
            {uploading ? (
              <div className="text-center">
                <p className="text-lg font-bold text-white mb-2">Ingesting spreadsheet...</p>
                <p className="text-sm text-gray-400">Verifying file structure & columns</p>
              </div>
            ) : isDragActive ? (
              <p className="text-lg font-bold text-blue-400">Drop ledger file here...</p>
            ) : (
              <div className="text-center">
                <p className="text-lg font-bold text-white mb-2">Drag & Drop ledger dump here</p>
                <p className="text-sm text-gray-400 mb-6">Supports .xlsx, .xlsm, or .csv formats</p>
                <span className="bg-dark-700 border border-dark-600 text-blue-400 hover:bg-dark-600 text-sm font-semibold px-4 py-2.5 rounded-xl transition-colors">
                  Select File From Computer
                </span>
              </div>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-950/30 border border-red-500/50 rounded-xl p-4 flex gap-3 text-red-300">
              <AlertTriangle className="w-5 h-5 flex-shrink-0" />
              <div>
                <h4 className="font-bold">Upload Failed</h4>
                <p className="text-sm">{error}</p>
              </div>
            </div>
          )}

          {/* Secondary File Attachment Panels */}
          {uploadedAuditId && (
            <div className="flex flex-col gap-4">

              {/* ── Creditors Ledger — dedicated section ── */}
              <div className="bg-dark-800 border border-purple-500/30 rounded-2xl p-5 shadow-xl">
                <div className="flex items-start gap-3 mb-4">
                  <div className="p-2 bg-purple-500/10 border border-purple-500/20 rounded-xl flex-shrink-0">
                    <Users className="w-4 h-4 text-purple-400" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white">
                      Creditors Ledger
                      <span className="ml-2 text-xs font-semibold text-purple-400 bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 rounded-full">Recommended</span>
                    </h3>
                    <p className="text-xs text-gray-400 mt-0.5">
                      Upload your AP / Purchase ledger (Tally, SAP, Busy) to enable vendor aging, overdue payables, and duplicate vendor payment detection.
                    </p>
                  </div>
                </div>
                <CreditorFileSection
                  auditId={uploadedAuditId}
                  backendUrl={backendUrl}
                  onAttached={(type) => setAttachedTypes((prev) => [...prev, type])}
                  alreadyAttached={attachedTypes.includes('CREDITORS_LEDGER')}
                />
              </div>

              {/* ── Other Additional Files ── */}
              <div className="bg-dark-800 border border-blue-500/20 rounded-2xl p-5 shadow-xl">
                <div className="flex items-center gap-2 mb-4">
                  <Paperclip className="w-5 h-5 text-blue-400" />
                  <h3 className="text-base font-bold text-white">
                    Attach Additional Files
                    <span className="text-gray-500 text-sm font-normal ml-2">(optional)</span>
                  </h3>
                </div>
                <p className="text-xs text-gray-400 mb-4">
                  Attach a bank statement, debtors ledger, sales or expense ledger to enable deeper analysis. Each file is tagged so the engine knows how to use it.
                </p>
                <div className="space-y-3">
                  {attachRows.map((key) => (
                    <AttachFileRow
                      key={key}
                      auditId={uploadedAuditId}
                      backendUrl={backendUrl}
                      onAttached={(type) => setAttachedTypes((prev) => [...prev, type])}
                    />
                  ))}
                </div>
                <button
                  onClick={() => setAttachRows((prev) => [...prev, Date.now()])}
                  className="mt-3 text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" /> Add another file
                </button>

                {/* Start Audit CTA */}
                <div className="mt-5 pt-4 border-t border-dark-700 flex justify-end">
                  <button
                    onClick={() => onUploadSuccess(uploadedAuditId, auditConfig)}
                    className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold px-6 py-2.5 rounded-xl flex items-center gap-2 shadow-lg transition-all"
                  >
                    Start Forensic Audit
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>

            </div>
          )}

          {/* Audit History Card */}
          <div className="bg-dark-800 border border-dark-700 rounded-2xl p-6 shadow-xl">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <History className="w-5 h-5 text-gray-400" />
              Local Audit History
            </h3>
            
            {pastAudits.length === 0 ? (
              <p className="text-sm text-gray-500 italic">No historical audits run on this machine.</p>
            ) : (
              <div className="max-h-48 overflow-y-auto space-y-2 pr-1">
                {pastAudits.map((a) => (
                  <div
                    key={a.id}
                    onClick={() => a.status === 'completed' && onLoadPastAudit(a.id)}
                    className={`flex items-center justify-between p-3.5 bg-dark-900 border rounded-xl transition-all ${
                      a.status === 'completed' 
                        ? 'border-dark-600 cursor-pointer hover:border-blue-500 hover:bg-dark-900/60' 
                        : 'border-red-900/50 opacity-60'
                    }`}
                  >
                    <div>
                      <h4 className="text-sm font-semibold text-white truncate max-w-xs">{a.filename}</h4>
                      <span className="text-xs text-gray-500">
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
                        <Play className="w-4 h-4 text-blue-400 hover:text-blue-300" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
