import { useState, useEffect } from 'react';
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
import HomeLanding from './pages/HomeLanding';
import {
  Shield, ChevronLeft, BarChart2, Copy, AlertOctagon, Calendar,
  FileText, Settings as SettingsIcon, AlertTriangle, Activity,
  TrendingUp, GitMerge, CreditCard, ShoppingCart, UploadCloud, ArrowLeft, Home
} from 'lucide-react';

export default function App() {
  // ── Top-level mode ─────────────────────────────────────────────────────────
  // 'home' | 'gl' | 'bank' | 'creditors'
  const [appMode, setAppMode] = useState('home');

  // ── GL mode state ───────────────────────────────────────────────────────────
  const [glPage, setGlPage] = useState('results'); // 'results' | 'audit' | 'loading' | 'settings'
  const [glResults, setGlResults] = useState(null);
  const [glAuditId, setGlAuditId] = useState(null);
  const [glFilename, setGlFilename] = useState('');
  const [glTab, setGlTab] = useState('upload');

  // ── Shared settings state ───────────────────────────────────────────────────
  const [llmConfigured, setLlmConfigured] = useState(true);
  const [showSettings, setShowSettings] = useState(false);

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
          setShowSettings(true);
        }
      })
      .catch(() => {
        // Server not reachable yet
      });
  }, []);

  // ── GL mode helpers ─────────────────────────────────────────────────────────
  const handleUploadSuccess = (auditId, config) => {
    setGlAuditId(auditId);
    setGlPage('audit');
    startAudit(auditId, config);
  };

  const handleLoadPastAudit = (auditId) => {
    setGlAuditId(auditId);
    setGlPage('loading');
    fetchAuditResults(auditId);
  };

  const fetchAuditResults = (auditId) => {
    fetch(`${backendUrl}/audit/${auditId}`)
      .then((res) => res.json())
      .then((data) => {
        setGlFilename(data.filename);
        setGlResults(data.results);
        setGlPage('results');
        setGlTab('dashboard');
      })
      .catch((err) => {
        console.error('Failed to load past audit details', err);
        setGlPage('results');
        setGlTab('upload');
      });
  };

  useEffect(() => {
    if (isCompleted && glAuditId) {
      setTimeout(() => {
        fetchAuditResults(glAuditId);
      }, 800);
    }
  }, [isCompleted, glAuditId]);

  const handleDownloadExcel = () => {
    if (glAuditId) {
      window.open(`${backendUrl}/audit/${glAuditId}/excel`);
    }
  };

  const handleBackToUpload = () => {
    setGlAuditId(null);
    setGlResults(null);
    setGlTab('upload');
  };

  const handleSettingsSaved = () => {
    setLlmConfigured(true);
    setShowSettings(false);
  };

  // Navigate to a mode from home (or back button)
  const handleSelectMode = (mode) => {
    setAppMode(mode);
    if (mode === 'gl') {
      setGlPage('results');
      setGlTab('upload');
    }
  };

  const handleGoHome = () => {
    setAppMode('home');
    setShowSettings(false);
  };

  const renderGLPlaceholder = (tabName) => (
    <div className="flex flex-col items-center justify-center py-20 text-center max-w-md mx-auto gap-5">
      <div className="p-4 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-2xl">
        <Shield className="w-8 h-8" />
      </div>
      <div>
        <h3 className="text-lg font-bold text-white mb-2">General Ledger Audit Required</h3>
        <p className="text-sm text-gray-400">
          The <span className="font-semibold text-white">{tabName}</span> feature requires performing a General Ledger or Debtors Ledger audit.
        </p>
      </div>
      <button
        onClick={() => setGlTab('upload')}
        className="bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm px-5 py-2.5 rounded-xl transition-all shadow-md"
      >
        Go to Upload &amp; Ingestion
      </button>
    </div>
  );

  // ── Shared Navbar ───────────────────────────────────────────────────────────
  const renderNavbar = () => (
    <header className="border-b border-dark-700 bg-dark-950/40 px-6 py-4 flex items-center justify-between sticky top-0 z-50 backdrop-blur-md">
      <div className="flex items-center gap-3">
        {/* Logo / Home button */}
        <div
          className="flex items-center gap-2.5 cursor-pointer"
          onClick={handleGoHome}
        >
          <div className="p-2 bg-blue-600/10 border border-blue-500/20 text-blue-400 rounded-xl">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <span className="font-extrabold text-white text-base tracking-wider uppercase block">Ledger Forensic Audit</span>
            <span className="text-[10px] text-gray-500 font-bold uppercase tracking-widest block">Forensic Ledger Engine</span>
          </div>
        </div>

        {/* Mode breadcrumb */}
        {appMode !== 'home' && (
          <div className="flex items-center gap-2 ml-2">
            <span className="text-gray-600">/</span>
            <span className={`text-xs font-bold px-2.5 py-1 rounded-lg border ${
              appMode === 'gl'
                ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                : appMode === 'creditors'
                ? 'bg-purple-500/10 text-purple-400 border-purple-500/20'
                : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
            }`}>
              {appMode === 'gl' ? 'GL & Debtors' : appMode === 'creditors' ? 'Creditors (AP)' : 'Bank Statement'}
            </span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        {!llmConfigured && !showSettings && (
          <button
            onClick={() => setShowSettings(true)}
            className="flex items-center gap-1.5 text-xs font-bold text-amber-400 bg-amber-950/30 border border-amber-700/40 px-3 py-1.5 rounded-lg hover:bg-amber-900/40 transition-colors"
          >
            <AlertTriangle className="w-3.5 h-3.5" />
            API Key not set
          </button>
        )}

        {/* Back to Home button (non-home modes) */}
        {appMode !== 'home' && !showSettings && (
          <button
            onClick={handleGoHome}
            className="text-xs font-bold text-gray-400 hover:text-white transition-colors bg-dark-800 hover:bg-dark-700 border border-dark-700 px-3.5 py-1.5 rounded-lg flex items-center gap-1"
          >
            <Home className="w-3.5 h-3.5" />
            Home
          </button>
        )}

        {/* GL: active file indicator + New GL Audit button */}
        {appMode === 'gl' && glResults && glPage === 'results' && (
          <>
            <span className="text-xs text-gray-400 font-medium bg-dark-800 border border-dark-700 px-3.5 py-1.5 rounded-lg truncate max-w-[240px]">
              Active: <strong>{glFilename}</strong>
            </span>
            <button
              onClick={handleBackToUpload}
              className="text-xs font-bold text-gray-400 hover:text-white transition-colors bg-dark-800 hover:bg-dark-700 border border-dark-700 px-3.5 py-1.5 rounded-lg flex items-center gap-1"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              New GL Audit
            </button>
          </>
        )}

        <button
          onClick={() => setShowSettings(!showSettings)}
          className={`p-2 rounded-xl border transition-all ${
            showSettings
              ? 'bg-blue-600/20 border-blue-500/40 text-blue-400'
              : 'bg-dark-800 border-dark-700 text-gray-400 hover:text-white hover:bg-dark-700'
          }`}
          title="LLM Settings"
        >
          <SettingsIcon className="w-4 h-4" />
        </button>
      </div>
    </header>
  );

  // ── Settings overlay ────────────────────────────────────────────────────────
  if (showSettings) {
    return (
      <div className="min-h-screen flex flex-col bg-dark-900 text-gray-100">
        {renderNavbar()}
        <main className="flex-1 flex flex-col">
          <Settings onSaved={handleSettingsSaved} initialConfigured={llmConfigured} />
        </main>
      </div>
    );
  }

  // ── Home mode ───────────────────────────────────────────────────────────────
  if (appMode === 'home') {
    return (
      <div className="min-h-screen flex flex-col bg-dark-900 text-gray-100">
        {renderNavbar()}
        <main className="flex-1 flex flex-col">
          <HomeLanding onSelectMode={handleSelectMode} />
        </main>
      </div>
    );
  }

  // ── Bank Statement mode (standalone) ───────────────────────────────────────
  if (appMode === 'bank') {
    return (
      <div className="min-h-screen flex flex-col bg-dark-900 text-gray-100">
        {renderNavbar()}
        <main className="flex-1 p-6 md:p-8 bg-dark-900 overflow-y-auto">
          <BankReconciliation currencySymbol="Rs." />
        </main>
      </div>
    );
  }

  // ── Creditors mode (standalone) ────────────────────────────────────────────
  if (appMode === 'creditors') {
    return (
      <div className="min-h-screen flex flex-col bg-dark-900 text-gray-100">
        {renderNavbar()}
        <main className="flex-1 p-6 md:p-8 bg-dark-900 overflow-y-auto max-w-7xl mx-auto w-full">
          <CreditorsLedger />
        </main>
      </div>
    );
  }

  // ── GL mode ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen flex flex-col bg-dark-900 text-gray-100">
      {renderNavbar()}

      <main className="flex-1 flex flex-col">
        {glPage === 'loading' && (
          <div className="flex-1 flex flex-col justify-center items-center gap-4 py-20">
            <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-gray-400">Loading audit findings from local database...</p>
          </div>
        )}

        {glPage === 'audit' && (
          <LiveAudit
            statusLogs={statusLogs}
            progress={progress}
            activeAgent={activeAgent}
            error={isFailed ? error : null}
          />
        )}

        {glPage === 'results' && (
          <div className="flex-1 flex flex-col md:flex-row">
            {/* GL Sidebar Navigation */}
            <aside className="w-full md:w-64 bg-dark-950/20 border-r border-dark-700 p-4 flex flex-col gap-1.5 overflow-y-auto max-h-[calc(100vh-73px)]">

              <div className="text-[10px] font-extrabold uppercase tracking-widest text-gray-500 px-3 mt-2 mb-1.5">Ingestion &amp; Setup</div>
              {[
                { key: 'upload', label: 'Upload & Ingestion', icon: UploadCloud }
              ].map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setGlTab(tab.key)}
                  className={`w-full text-left text-xs font-bold px-3 py-2.5 rounded-xl transition-all flex items-center gap-2.5 ${
                    glTab === tab.key
                      ? 'bg-blue-600/15 text-blue-400 border border-blue-500/20 shadow-[0_2px_8px_rgba(37,99,235,0.1)]'
                      : 'text-gray-400 hover:bg-dark-800 hover:text-white border border-transparent'
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}

              <div className="text-[10px] font-extrabold uppercase tracking-widest text-gray-500 px-3 mt-4 mb-1.5">General Ledger Suite</div>
              {[
                { key: 'dashboard', label: 'Overview Dashboard', icon: BarChart2 },
                { key: 'duplicates', label: 'Duplicate Payments', icon: Copy },
                { key: 'anomalies', label: 'Forensic Anomalies', icon: AlertOctagon },
                { key: 'aging', label: 'Aging (AR) Schedule', icon: Calendar },
                { key: 'benfords', label: "Benford's Law", icon: Activity },
                { key: 'statistical_outliers', label: 'Statistical Outliers', icon: TrendingUp },
                { key: 'circular_funds', label: 'Circular Funds', icon: GitMerge },
                { key: 'temporal', label: 'Temporal Patterns', icon: Calendar },
                { key: 'expense_scrutiny', label: 'Expense Scrutiny', icon: ShoppingCart },
                { key: 'sales_scrutiny', label: 'Sales Scrutiny', icon: TrendingUp },
                { key: 'gst_tds', label: 'GST/TDS Compliance', icon: FileText },
                { key: 'memo', label: 'CA Observations Memo', icon: FileText }
              ].map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setGlTab(tab.key)}
                  className={`w-full text-left text-xs font-bold px-3 py-2.5 rounded-xl transition-all flex items-center gap-2.5 ${
                    glTab === tab.key
                      ? 'bg-blue-600 text-white shadow-[0_4px_12px_rgba(37,99,235,0.2)]'
                      : 'text-gray-400 hover:bg-dark-800 hover:text-white border border-transparent'
                  }`}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              ))}
            </aside>

            {/* Tab panel content */}
            <section className="flex-1 p-6 md:p-8 bg-dark-900 overflow-y-auto max-h-[calc(100vh-73px)]">
              {glTab === 'upload' && (
                <Upload
                  onUploadSuccess={handleUploadSuccess}
                  onLoadPastAudit={handleLoadPastAudit}
                />
              )}
              {glTab === 'dashboard' && (glResults ? <Dashboard results={glResults} /> : renderGLPlaceholder('Overview Dashboard'))}
              {glTab === 'duplicates' && (
                glResults ? (
                  <Duplicates
                    results={glResults}
                    onDownloadExcel={handleDownloadExcel}
                  />
                ) : renderGLPlaceholder('Duplicate Payments')
              )}
              {glTab === 'anomalies' && (glResults ? <Anomalies results={glResults} /> : renderGLPlaceholder('Forensic Anomalies'))}
              {glTab === 'aging' && (glResults ? <Aging results={glResults} /> : renderGLPlaceholder('Aging Schedule'))}
              {glTab === 'benfords' && (glResults ? <BenfordsLaw results={glResults} /> : renderGLPlaceholder("Benford's Law"))}
              {glTab === 'statistical_outliers' && (glResults ? <StatisticalOutliers results={glResults} /> : renderGLPlaceholder('Statistical Outliers'))}
              {glTab === 'circular_funds' && (glResults ? <CircularFunds results={glResults} /> : renderGLPlaceholder('Circular Funds'))}
              {glTab === 'temporal' && (glResults ? <TemporalPatterns results={glResults} /> : renderGLPlaceholder('Temporal Patterns'))}
              {glTab === 'expense_scrutiny' && (glResults ? <ExpenseScrutiny results={glResults} /> : renderGLPlaceholder('Expense Scrutiny'))}
              {glTab === 'sales_scrutiny' && (glResults ? <SalesScrutiny results={glResults} /> : renderGLPlaceholder('Sales Scrutiny'))}
              {glTab === 'gst_tds' && (glResults ? <GSTCompliance results={glResults} /> : renderGLPlaceholder('GST/TDS Compliance'))}
              {glTab === 'memo' && (glResults ? <AuditMemo results={glResults} /> : renderGLPlaceholder('CA Observations Memo'))}
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
