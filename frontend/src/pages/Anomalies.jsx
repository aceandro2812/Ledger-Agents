import React, { useState } from 'react';
import { AlertOctagon, ChevronDown, ChevronUp, ArrowRight, ShieldAlert } from 'lucide-react';

export default function Anomalies({ results, currencySymbol = 'Rs.' }) {
  const { anomalies = [] } = results;
  const [filter, setFilter] = useState('ALL');
  const [expandedRows, setExpandedRows] = useState({});

  const toggleRow = (id) => {
    setExpandedRows((prev) => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const filteredAnoms = anomalies.filter((a) => {
    if (filter === 'ALL') return true;
    return a.severity === filter;
  });

  // Group by anomaly type
  const anomalyTypes = [...new Set(filteredAnoms.map((a) => a.anomaly_type))];

  const getSeverityBadge = (sev) => {
    if (sev === 'CRITICAL') return 'bg-red-950/60 text-red-400 border border-red-800/40';
    if (sev === 'HIGH') return 'bg-orange-950/60 text-orange-400 border border-orange-800/40';
    if (sev === 'MEDIUM') return 'bg-yellow-950/60 text-yellow-400 border border-yellow-800/40';
    return 'bg-blue-950/60 text-blue-400 border border-blue-800/40';
  };

  const fmt = (val) => `${currencySymbol} ${Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  return (
    <div className="space-y-6">
      {/* Title */}
      <div>
        <h2 className="text-2xl font-bold text-white mb-1.5 flex items-center gap-2">
          <AlertOctagon className="w-6 h-6 text-red-500" />
          Forensic Anomaly Register
        </h2>
        <p className="text-sm text-gray-400">Scans all ledger records for audit risk patterns such as reversals, holiday bookings, round-trips, and limit splits.</p>
      </div>

      {/* Severity Filter Tabs */}
      <div className="flex gap-2.5">
        {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((t) => (
          <button
            key={t}
            onClick={() => setFilter(t)}
            className={`text-sm font-semibold px-4 py-2 rounded-xl transition-all ${
              filter === t
                ? 'bg-red-600 text-white'
                : 'bg-dark-800 text-gray-400 hover:bg-dark-700/60 border border-dark-700'
            }`}
          >
            {t} ({t === 'ALL' ? anomalies.length : anomalies.filter((a) => a.severity === t).length})
          </button>
        ))}
      </div>

      {/* Group List */}
      {anomalyTypes.length === 0 ? (
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-16 text-center text-gray-500 italic shadow-xl">
          No anomalies found matching selected severity level.
        </div>
      ) : (
        <div className="space-y-6">
          {anomalyTypes.map((type) => {
            const items = filteredAnoms.filter((a) => a.anomaly_type === type);
            
            return (
              <div key={type} className="bg-dark-800 border border-dark-700 rounded-2xl shadow-xl overflow-hidden">
                {/* Section Header */}
                <div className="bg-dark-950/20 border-b border-dark-700 px-6 py-4 flex justify-between items-center">
                  <h3 className="text-sm font-bold text-white tracking-wider uppercase flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                    {type}
                  </h3>
                  <span className="text-xs font-bold bg-dark-700 text-gray-300 px-3 py-1 rounded-full border border-dark-600">
                    {items.length} Flags
                  </span>
                </div>

                {/* Section Items Table */}
                <div className="divide-y divide-dark-700/50">
                  {items.map((an) => {
                    const isExpanded = !!expandedRows[an.finding_id];
                    return (
                      <div key={an.finding_id} className="transition-colors hover:bg-dark-700/10">
                        {/* Table Row */}
                        <div
                          onClick={() => toggleRow(an.finding_id)}
                          className="px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4 cursor-pointer text-sm"
                        >
                          <div className="flex-1 space-y-1">
                            <h4 className="font-bold text-white truncate max-w-md">{an.party}</h4>
                            <p className="text-gray-400 text-xs line-clamp-1">{an.description}</p>
                          </div>
                          
                          <div className="flex items-center gap-6 justify-between md:justify-end">
                            <span className={`text-xs px-2.5 py-1 rounded-full font-bold ${getSeverityBadge(an.severity)}`}>
                              {an.severity}
                            </span>
                            
                            <div className="text-gray-400">
                              {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                            </div>
                          </div>
                        </div>

                        {/* Expandable Evidence Details */}
                        {isExpanded && (
                          <div className="px-6 pb-6 pt-2 bg-dark-950/30 border-t border-dark-700/50 space-y-5">
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                              {/* Evidence Text */}
                              <div className="lg:col-span-2 space-y-3.5">
                                <h5 className="text-xs font-bold text-red-400 uppercase tracking-wider">Detailed Observations</h5>
                                <p className="text-gray-300 text-sm leading-relaxed">{an.description}</p>
                                
                                <div className="bg-red-950/20 border border-red-800/30 rounded-xl p-4 text-sm flex gap-3 text-red-300">
                                  <ArrowRight className="w-5 h-5 flex-shrink-0 mt-0.5" />
                                  <div>
                                    <h6 className="font-bold mb-1">Recommended Auditor Action</h6>
                                    <p className="text-red-300/90 leading-relaxed">{an.recommendation}</p>
                                  </div>
                                </div>
                              </div>

                              {/* Evidence Data Block */}
                              <div className="lg:col-span-1 space-y-3.5">
                                <h5 className="text-xs font-bold text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
                                  <ShieldAlert className="w-4 h-4" />
                                  Source Evidence Reference
                                </h5>
                                <div className="bg-dark-800/80 border border-dark-700 rounded-xl p-4 font-mono text-xs overflow-x-auto max-h-48 text-gray-300">
                                  <pre className="whitespace-pre-wrap">{JSON.stringify(an.evidence, null, 2)}</pre>
                                </div>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
