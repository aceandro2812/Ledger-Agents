import { Shield, Users, CreditCard, ArrowRight, CheckCircle2, Zap, Lock, BarChart3 } from 'lucide-react';

const MODES = [
  {
    key: 'gl',
    icon: Shield,
    iconColor: 'text-blue-400',
    iconBg: 'bg-blue-500/10 border-blue-500/20',
    gradientFrom: 'from-blue-600/20',
    gradientTo: 'to-indigo-600/10',
    borderColor: 'border-blue-500/20 hover:border-blue-400/50',
    glowColor: 'shadow-blue-500/10',
    accentColor: 'bg-blue-600',
    badgeBg: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    title: 'General Ledger & Debtors Forensic Audit',
    badge: 'Full Multi-Agent Pipeline',
    description:
      'Upload Tally/SAP/Busy/CSV GL dumps for full forensic analysis: duplicate payments, anomalies, aging, Benford\'s Law, reconciliation and CA memo.',
    features: [
      'Duplicate payment detection (5 passes)',
      'Benford\'s Law & Statistical Outliers',
      'AR Aging (FIFO) + Reconciliation',
      'AI-generated CA Observation Memo',
    ],
  },
  {
    key: 'creditors',
    icon: Users,
    iconColor: 'text-purple-400',
    iconBg: 'bg-purple-500/10 border-purple-500/20',
    gradientFrom: 'from-purple-600/20',
    gradientTo: 'to-violet-600/10',
    borderColor: 'border-purple-500/20 hover:border-purple-400/50',
    glowColor: 'shadow-purple-500/10',
    accentColor: 'bg-purple-600',
    badgeBg: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    title: 'Creditors Ledger (AP) Analysis',
    badge: 'Independent Workspace',
    description:
      'Upload accounts payable or creditors purchase ledger for FIFO invoice aging, vendor payment tracking, and outstanding payables schedule.',
    features: [
      'FIFO invoice-to-payment matching',
      'Vendor aging in 6 standard buckets',
      'Overdue & critical payables flags',
      'Zero-payment & dormant vendor alerts',
    ],
  },
  {
    key: 'bank',
    icon: CreditCard,
    iconColor: 'text-emerald-400',
    iconBg: 'bg-emerald-500/10 border-emerald-500/20',
    gradientFrom: 'from-emerald-600/20',
    gradientTo: 'to-teal-600/10',
    borderColor: 'border-emerald-500/20 hover:border-emerald-400/50',
    glowColor: 'shadow-emerald-500/10',
    accentColor: 'bg-emerald-600',
    badgeBg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
    title: 'Bank Statement Analysis',
    badge: 'Independent Workspace',
    description:
      'Upload any bank statement (HDFC, SBI, ICICI, Axis, Kotak, or generic CSV) for category-wise spend analysis, pattern detection, and transaction review.',
    features: [
      'Auto bank format detection',
      '11-category spend classification',
      'Net cash flow & KPI dashboard',
      'Filtered CSV export with totals',
    ],
  },
];

export default function HomeLanding({ onSelectMode }) {
  return (
    <div className="min-h-[calc(100vh-73px)] flex flex-col items-center justify-center px-6 py-16 bg-dark-900 relative overflow-hidden">

      {/* Background ambient glows */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-48 -left-48 w-[600px] h-[600px] bg-blue-600/5 rounded-full blur-3xl" />
        <div className="absolute -bottom-48 -right-48 w-[600px] h-[600px] bg-purple-600/5 rounded-full blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-indigo-900/10 rounded-full blur-3xl" />
      </div>

      {/* Hero headline */}
      <div className="text-center mb-14 relative z-10 max-w-3xl">
        <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-bold uppercase tracking-widest px-4 py-1.5 rounded-full mb-6">
          <Zap className="w-3.5 h-3.5" />
          Forensic Ledger Engine · Powered by AI
        </div>
        <h1 className="text-5xl md:text-6xl font-extrabold text-white tracking-tight mb-5 leading-tight">
          Ledger{' '}
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400">
            Forensic
          </span>{' '}
          Audit Suite
        </h1>
        <p className="text-lg text-gray-400 leading-relaxed max-w-2xl mx-auto">
          Choose an analysis module below. Each workspace is fully independent — no setup
          required. Your data stays on-device for complete privacy.
        </p>
        <div className="flex items-center justify-center gap-6 mt-6 text-xs text-gray-500 font-medium">
          <span className="flex items-center gap-1.5"><Lock className="w-3.5 h-3.5 text-green-500" /> 100% Local Processing</span>
          <span className="flex items-center gap-1.5"><BarChart3 className="w-3.5 h-3.5 text-blue-400" /> CA-Grade Analysis</span>
          <span className="flex items-center gap-1.5"><Zap className="w-3.5 h-3.5 text-yellow-400" /> Instant Results</span>
        </div>
      </div>

      {/* Mode cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-6xl relative z-10">
        {MODES.map((mode) => {
          const Icon = mode.icon;
          return (
            <button
              key={mode.key}
              onClick={() => onSelectMode(mode.key)}
              className={`group relative text-left rounded-3xl border ${mode.borderColor} bg-dark-800 p-7 flex flex-col gap-5 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl ${mode.glowColor} shadow-xl cursor-pointer overflow-hidden`}
            >
              {/* Gradient shimmer background */}
              <div className={`absolute inset-0 bg-gradient-to-br ${mode.gradientFrom} ${mode.gradientTo} opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-3xl`} />

              {/* Top row: icon + badge */}
              <div className="relative z-10 flex items-start justify-between">
                <div className={`p-3.5 border rounded-2xl ${mode.iconBg}`}>
                  <Icon className={`w-6 h-6 ${mode.iconColor}`} />
                </div>
                <span className={`text-[10px] font-extrabold uppercase tracking-widest border px-2.5 py-1 rounded-full ${mode.badgeBg}`}>
                  {mode.badge}
                </span>
              </div>

              {/* Title & description */}
              <div className="relative z-10 flex-1">
                <h2 className="text-xl font-bold text-white mb-2.5 leading-snug group-hover:text-white transition-colors">
                  {mode.title}
                </h2>
                <p className="text-sm text-gray-400 leading-relaxed">
                  {mode.description}
                </p>
              </div>

              {/* Feature bullets */}
              <ul className="relative z-10 space-y-2">
                {mode.features.map((feat) => (
                  <li key={feat} className="flex items-start gap-2.5 text-xs text-gray-400">
                    <CheckCircle2 className={`w-4 h-4 ${mode.iconColor} flex-shrink-0 mt-px`} />
                    <span>{feat}</span>
                  </li>
                ))}
              </ul>

              {/* CTA row */}
              <div className={`relative z-10 flex items-center gap-2 ${mode.iconColor} text-sm font-bold pt-2 border-t border-white/5 group-hover:gap-3 transition-all`}>
                <span>Start Analysis</span>
                <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
              </div>
            </button>
          );
        })}
      </div>

      {/* Footer hint */}
      <p className="relative z-10 mt-10 text-xs text-gray-600 text-center">
        Supports .xlsx · .xlsm · .csv · Tally · SAP · Busy · Marg exports
      </p>
    </div>
  );
}
