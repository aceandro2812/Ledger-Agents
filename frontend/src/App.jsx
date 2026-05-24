import React, { useState, useEffect } from 'react';
import { useSSE } from './hooks/useSSE';
import Upload from './pages/Upload';
import LiveAudit from './pages/LiveAudit';
import Dashboard from './pages/Dashboard';
import Duplicates from './pages/Duplicates';
import Anomalies from './pages/Anomalies';
import Aging from './pages/Aging';
import AuditMemo from './pages/AuditMemo';
import Settings from './pages/Settings';
import BenfordsLaw from './pages/BenfordsLaw';
import StatisticalOutliers from './pages/StatisticalOutliers';
import CircularFunds from './pages/CircularFunds';
import TemporalPatterns from './pages/TemporalPatterns';
import BankReconciliation from './pages/BankReconciliation';
import ExpenseScrutiny from './pages/ExpenseScrutiny';
import SalesScrutiny from './pages/SalesScrutiny';
import CreditorsLedger from './pages/CreditorsLedger';
import GSTCompliance from './pages/GSTCompliance';
import {
  Shield, ChevronLeft, BarChart2, Copy, AlertOctagon, Calendar,
  FileText, Settings as SettingsIcon, AlertTriangle, Activity,
  TrendingUp, GitMerge, CreditCard, ShoppingCart, Users
} from 'lucide-react';

export default function App() {
  const [page, setPage] = useState('upload'); // 'upload', 'audit', 'results', 'settings'
  const [activeAuditId, setActiveAuditId] = useState(null);
  const [activeFilename, setActiveFilename] = useState('');
  const [results, setResults] = useState(null);
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [llmConfigured, setLlmConfigured] = useState(true); // assume true until checked

  const {
    statusLogs,
    progress,
    activeAgent,
    isCompleted,
    isFailed,
    error,
    startAudit
  } = useSSE();

  const backendUrl = import.meta.env.VITE_API_URL || (window.location.port === '5173' ? 'http://localhost:8000' : '');

  // On startup, check if API key is configured
  useEffect(() => {
    fetch(`${backendUrl}/settings/status`)
      .then(r => r.json())
      .then(data => {
        setLlmConfigured(data.configured);
        if (!data.configured) {
          setPage('settings');
        }
      })
      .catch(() => {
        // Server not reachable yet — don't block the UI
      });
  }, []);

  const handleUploadSuccess = (auditId, config) => {
    setActiveAuditId(auditId);
    setPage('audit');
    startAudit(auditId, config);
  };

  const handleLoadPastAudit = (auditId) => {
    setActiveAuditId(auditId);
    setPage('loading');
    fetchAuditResults(auditId);
  };

  const fetchAuditResults = (auditId) => {
    fetch(`${backendUrl}/audit/${auditId}`)
      .then((res) => res.json())
      .then((data) => {
        setActiveFilename(data.filename);
        setResults(data.results);
        setPage('results');
        setCurrentTab('dashboard');
      })
      .catch((err) => {
        console.error('Failed to load past audit details', err);
        setPage('upload');
      });
  };

  useEffect(() => {
    if (isCompleted && activeAuditId) {
      setTimeout(() => {
        fetchAuditResults(activeAuditId);
      }, 800);
    }
  }, [isCompleted, activeAuditId]);

  const handleDownloadExcel = () => {
    if (activeAuditId) {
      window.open(`${backendUrl}/audit/${activeAuditId}/excel`);
    }
  };

  const handleBackToUpload = () => {
    setPage('upload');
    setActiveAuditId(null);
    setResults(null);
  };

  const handleSettingsSaved = () => {
    setLlmConfigured(true);
    setPage('upload');
  };

  return (
    <div className="min-h-screen flex flex-col bg-dark-900 text-gray-100">
      {/* Top Navbar */}
      <header className="border-b border-dark-700 bg-dark-950/40 px-6 py-4 flex items-center justify-between sticky top-0 z-50 backdrop-blur-md">
        <div className="flex items-center gap-2.5 cursor-pointer" onClick={handleBackToUpload}>
          <div className="p-2 bg-blue-600/10 border border-blue-500/20 text-blue-400 rounded-xl">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <span className="font-extrabold text-white text-base tracking-wider uppercase block">Antigravity</span>
            <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest block">Forensic Ledger Engine</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* LLM not configured warning pill */}
          {!llmConfigured && page !== 'settings' && (
            <button
              onClick={() => setPage('settings')}
              className="flex items-center gap-1.5 text-xs font-bold text-amber-400 bg-amber-950/30 border border-amber-700/40 px-3 py-1.5 rounded-lg hover:bg-amber-900/40 transition-colors"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              API Key not set
            </button>
          )}

          {page === 'results' && (
            <>
              <span className="text-xs text-gray-400 font-medium bg-dark-800 border border-dark-700 px-3.5 py-1.5 rounded-lg truncate max-w-[240px]">
                Active: <strong>{activeFilename}</strong>
              </span>
              <button
                onClick={handleBackToUpload}
                className="text-xs font-bold text-gray-400 hover:text-white transition-colors bg-dark-800 hover:bg-dark-700 border border-dark-700 px-3.5 py-1.5 rounded-lg flex items-center gap-1"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                New Audit
              </button>
            </>
          )}

          {/* Settings gear button */}
          <button
            onClick={() => setPage(page === 'settings' ? 'upload' : 'settings')}
            className={`p-2 rounded-xl border transition-all ${
              page === 'settings'
                ? 'bg-blue-600/20 border-blue-500/40 text-blue-400'
                : 'bg-dark-800 border-dark-700 text-gray-400 hover:text-white hover:bg-dark-700'
            }`}
            title="LLM Settings"
          >
            <SettingsIcon className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col">
        {page === 'settings' && (
          <Settings onSaved={handleSettingsSaved} initialConfigured={llmConfigured} />
        )}

        {page === 'upload' && (
          <Upload
            onUploadSuccess={handleUploadSuccess}
            onLoadPastAudit={handleLoadPastAudit}
          />
        )}

        {page === 'loading' && (
          <div className="flex-1 flex flex-col justify-center items-center gap-4 py-20">
            <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-gray-400">Loading audit findings from local database...</p>
          </div>
        )}

        {page === 'audit' && (
          <LiveAudit
            statusLogs={statusLogs}
            progress={progress}
            activeAgent={activeAgent}
            error={isFailed ? error : null}
          />
        )}

        {page === 'results' && results && (
          <div className="flex-1 flex flex-col md:flex-row">
            {/* Sidebar Navigation */}
            <aside className="w-full md:w-64 bg-dark-950/20 border-r border-dark-700 p-4 flex flex-col gap-1.5">
              {[
                { key: 'dashboard', label: 'Overview Dashboard', icon: BarChart2 },
                { key: 'duplicates', label: 'Duplicate Payments', icon: Copy },
                { key: 'anomalies', label: 'Forensic Anomalies', icon: AlertOctagon },
                { key: 'aging', label: 'Aging Schedule', icon: Calendar },
                { key: 'creditors', label: 'Creditors (AP)', icon: Users },
                { key: 'benfords', label: "Benford's Law", icon: Activity },
                { key: 'statistical_outliers', label: 'Statistical Outliers', icon: TrendingUp },
                { key: 'circular_funds', label: 'Circular Funds', icon: GitMerge },
                { key: 'temporal', label: 'Temporal Patterns', icon: Calendar },
                { key: 'bank_recon', label: 'Bank Reconciliation', icon: CreditCard },
                { key: 'expense_scrutiny', label: 'Expense Scrutiny', icon: ShoppingCart },
                { key: 'sales_scrutiny', label: 'Sales Scrutiny', icon: TrendingUp },
                { key: 'gst_tds', label: 'GST/TDS Compliance', icon: FileText },
                { key: 'memo', label: 'CA Observations Memo', icon: FileText }
              ].map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setCurrentTab(tab.key)}
                  className={`w-full text-left text-sm font-semibold px-4 py-3 rounded-xl transition-all flex items-center gap-3 ${
                    currentTab === tab.key
                      ? 'bg-blue-600 text-white shadow-[0_4px_12px_rgba(37,99,235,0.2)]'
                      : 'text-gray-400 hover:bg-dark-800 hover:text-white'
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </aside>

            {/* Tab panel content */}
            <section className="flex-1 p-6 md:p-8 bg-dark-900 overflow-y-auto max-h-[calc(100vh-73px)]">
              {currentTab === 'dashboard' && <Dashboard results={results} />}
              {currentTab === 'duplicates' && (
                <Duplicates
                  results={results}
                  onDownloadExcel={handleDownloadExcel}
                />
              )}
              {currentTab === 'anomalies' && <Anomalies results={results} />}
              {currentTab === 'aging' && <Aging results={results} />}
              {currentTab === 'creditors' && <CreditorsLedger results={results} />}
              {currentTab === 'benfords' && <BenfordsLaw results={results} />}
              {currentTab === 'statistical_outliers' && <StatisticalOutliers results={results} />}
              {currentTab === 'circular_funds' && <CircularFunds results={results} />}
              {currentTab === 'temporal' && <TemporalPatterns results={results} />}
              {currentTab === 'bank_recon' && <BankReconciliation results={results} />}
              {currentTab === 'expense_scrutiny' && <ExpenseScrutiny results={results} />}
              {currentTab === 'sales_scrutiny' && <SalesScrutiny results={results} />}
              {currentTab === 'gst_tds' && <GSTCompliance results={results} />}
              {currentTab === 'memo' && <AuditMemo results={results} />}
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
