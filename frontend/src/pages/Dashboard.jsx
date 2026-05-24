import React from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ShieldAlert, TrendingUp, Users, Copy, AlertOctagon, Activity, GitMerge, FileText, ShoppingCart, CreditCard } from 'lucide-react';

export default function Dashboard({ results, currencySymbol = 'Rs.' }) {
  const {
    aging = [], duplicates = [], anomalies = [], reconciliation = [],
    benfords_findings = [], circular_funds = [], gst_tds = [],
    expense_scrutiny = [], sales_scrutiny = [], bank_reconciliation = null
  } = results;

  // 1. Calculate KPIs
  const totalParties = aging.length;
  const grossOutstanding = aging.reduce((acc, a) => acc + (a.outstanding_balance || 0), 0);
  const duplicateRisk = duplicates
    .filter((d) => d.pass_number !== 5) // Skip Pass 5 round numbers for risk amount calculation
    .reduce((acc, d) => acc + (d.transaction_A?.amount || 0), 0);
  const totalAnomalies = anomalies.length;
  const overYearOutstanding = aging.reduce((acc, a) => acc + (a.aging_buckets?.['>365'] || 0), 0);

  // 2. Aggregate Aging Donut Chart Data
  const agingTotals = {
    '0-30': 0,
    '31-60': 0,
    '61-90': 0,
    '91-180': 0,
    '181-365': 0,
    '>365': 0
  };
  
  aging.forEach((a) => {
    Object.keys(agingTotals).forEach((bucket) => {
      agingTotals[bucket] += (a.aging_buckets?.[bucket] || 0);
    });
  });

  const agingChartData = Object.keys(agingTotals).map((name) => ({
    name,
    value: agingTotals[name]
  })).filter(d => d.value > 0);

  const AGING_COLORS = {
    '0-30': '#10b981',    // green
    '31-60': '#f59e0b',   // yellow
    '61-90': '#d97706',   // dark yellow/orange
    '91-180': '#f97316',  // orange
    '181-365': '#ef4444', // red
    '>365': '#b91c1c'     // dark red
  };

  // 3. Top 10 Parties by Outstanding
  const topPartiesData = [...aging]
    .sort((a, b) => b.outstanding_balance - a.outstanding_balance)
    .slice(0, 10)
    .map((a) => ({
      name: a.party.length > 15 ? a.party.substring(0, 15) + '...' : a.party,
      amount: a.outstanding_balance
    }));

  // 4. Heatmap Data calculation
  // Find top 8 parties by total anomalies count
  const anomalyCountsByParty = {};
  anomalies.forEach((a) => {
    anomalyCountsByParty[a.party] = (anomalyCountsByParty[a.party] || 0) + 1;
  });

  const topAnomalyParties = Object.keys(anomalyCountsByParty)
    .sort((a, b) => anomalyCountsByParty[b] - anomalyCountsByParty[a])
    .slice(0, 8);

  const riskCategories = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'];

  // format currency helper
  const fmt = (val) => `${currencySymbol} ${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  return (
    <div className="space-y-8">
      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-5">
        {[
          { label: 'Total Parties', val: totalParties, icon: Users, color: 'text-blue-400', bg: 'bg-blue-950/20' },
          { label: 'Gross Outstanding', val: fmt(grossOutstanding), icon: TrendingUp, color: 'text-green-400', bg: 'bg-green-950/20' },
          { label: 'Duplicate Payments Risk', val: fmt(duplicateRisk), icon: Copy, color: 'text-yellow-400', bg: 'bg-yellow-950/20' },
          { label: 'Anomalies Flagged', val: totalAnomalies, icon: AlertOctagon, color: 'text-red-400', bg: 'bg-red-950/20' },
          { label: 'Outstanding > 1 Year', val: fmt(overYearOutstanding), icon: ShieldAlert, color: 'text-red-400', bg: 'bg-red-950/20' }
        ].map((kpi, idx) => (
          <div key={idx} className="bg-dark-800 border border-dark-700 rounded-2xl p-5 shadow-lg flex items-center gap-4">
            <div className={`p-3 rounded-xl ${kpi.bg} ${kpi.color}`}>
              <kpi.icon className="w-6 h-6" />
            </div>
            <div>
              <span className="text-xs font-semibold text-gray-400 block mb-0.5">{kpi.label}</span>
              <h3 className="text-lg font-bold text-white truncate max-w-[160px]">{kpi.val}</h3>
            </div>
          </div>
        ))}
      </div>

      {/* Tier-2 KPI Cards Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {[
          { label: "Benford's Violations", val: benfords_findings.filter(f => f.conformity_status !== 'CLOSE').length, icon: Activity, color: 'text-purple-400', bg: 'bg-purple-950/20' },
          { label: 'Circular Funds', val: circular_funds.length, icon: GitMerge, color: 'text-orange-400', bg: 'bg-orange-950/20' },
          { label: 'TDS Gaps', val: fmt(gst_tds.reduce((s, f) => s + (f.expected_tds_amount || 0), 0)), icon: FileText, color: 'text-indigo-400', bg: 'bg-indigo-950/20' },
          { label: 'Expense Flags', val: expense_scrutiny.length, icon: ShoppingCart, color: 'text-yellow-400', bg: 'bg-yellow-950/20' },
          { label: 'Sales Flags', val: sales_scrutiny.length, icon: TrendingUp, color: 'text-cyan-400', bg: 'bg-cyan-950/20' },
          { label: 'Bank Unmatched', val: bank_reconciliation ? (bank_reconciliation.gl_only_count || 0) + (bank_reconciliation.bank_only_count || 0) : '—', icon: CreditCard, color: 'text-rose-400', bg: 'bg-rose-950/20' },
        ].map((kpi, idx) => (
          <div key={idx} className="bg-dark-800 border border-dark-700 rounded-xl p-4 flex items-center gap-3">
            <div className={`p-2 rounded-lg ${kpi.bg} ${kpi.color}`}>
              <kpi.icon className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[10px] font-semibold text-gray-500 block">{kpi.label}</span>
              <h3 className="text-sm font-bold text-white">{kpi.val}</h3>
            </div>
          </div>
        ))}
      </div>

      {/* Charts section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Aging Donut chart */}
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-6 shadow-xl">
          <h3 className="text-lg font-bold text-white mb-6">Aging Distribution</h3>
          {agingChartData.length === 0 ? (
            <div className="flex h-64 justify-center items-center text-gray-500 italic">No aging balance outstanding.</div>
          ) : (
            <div className="flex flex-col md:flex-row items-center justify-around h-64">
              <div className="w-48 h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={agingChartData}
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={4}
                      dataKey="value"
                    >
                      {agingChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={AGING_COLORS[entry.name] || '#8884d8'} />
                      ))}
                    </Pie>
                    <Tooltip 
                      formatter={(val) => fmt(val)}
                      contentStyle={{ backgroundColor: '#151b2d', border: '1px solid #2d3b55', color: '#fff' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="grid grid-cols-2 gap-x-6 gap-y-2 mt-4 md:mt-0">
                {agingChartData.map((d) => (
                  <div key={d.name} className="flex items-center gap-2 text-sm">
                    <span className="w-3.5 h-3.5 rounded-full" style={{ backgroundColor: AGING_COLORS[d.name] }} />
                    <span className="text-gray-300 font-semibold">{d.name} :</span>
                    <span className="text-white font-bold">{fmt(d.value)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Top 10 Outstanding Bar Chart */}
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-6 shadow-xl">
          <h3 className="text-lg font-bold text-white mb-6 font-bold">Top 10 Parties by Outstanding Balance</h3>
          {topPartiesData.length === 0 ? (
            <div className="flex h-64 justify-center items-center text-gray-500 italic">No balances to display.</div>
          ) : (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={topPartiesData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f293d" />
                  <XAxis dataKey="name" stroke="#9ca3af" fontSize={11} tickLine={false} />
                  <YAxis stroke="#9ca3af" fontSize={11} tickLine={false} tickFormatter={(val) => val / 1000 + 'k'} />
                  <Tooltip
                    formatter={(val) => fmt(val)}
                    contentStyle={{ backgroundColor: '#151b2d', border: '1px solid #2d3b55', color: '#fff' }}
                  />
                  <Bar dataKey="amount" fill="#388dff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {/* Heatmap Section */}
      <div className="bg-dark-800 border border-dark-700 rounded-2xl p-6 shadow-xl">
        <h3 className="text-lg font-bold text-white mb-4">Risk Exposure Matrix</h3>
        <p className="text-sm text-gray-400 mb-6">Heatmap mapping severity categories for the top 8 parties by flag count.</p>

        {topAnomalyParties.length === 0 ? (
          <div className="text-center text-gray-500 italic py-8">No anomalies detected.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left border-collapse">
              <thead>
                <tr className="border-b border-dark-700 text-gray-400">
                  <th className="py-3 px-4 font-bold">Party Name</th>
                  {riskCategories.map((cat) => (
                    <th key={cat} className="py-3 px-4 text-center font-bold">{cat}</th>
                  ))}
                  <th className="py-3 px-4 text-center font-bold">Total Flags</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-700">
                {topAnomalyParties.map((party) => {
                  const partyAnoms = anomalies.filter((a) => a.party === party);
                  const total = partyAnoms.length;

                  return (
                    <tr key={party} className="hover:bg-dark-700/30 transition-colors">
                      <td className="py-4 px-4 font-bold text-white max-w-[200px] truncate">{party}</td>
                      {riskCategories.map((cat) => {
                        const count = partyAnoms.filter((a) => a.severity === cat).length;
                        
                        // Color coding blocks: red for critical/high, orange/yellow for medium, green for low, dark-900 for 0
                        let blockClass = 'bg-dark-900 text-gray-600';
                        if (count > 0) {
                          if (cat === 'CRITICAL' || cat === 'HIGH') blockClass = 'bg-red-500/20 text-red-400 border border-red-500/30 font-extrabold';
                          else if (cat === 'MEDIUM') blockClass = 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 font-bold';
                          else if (cat === 'LOW') blockClass = 'bg-green-500/20 text-green-400 border border-green-500/30 font-semibold';
                        }

                        return (
                          <td key={cat} className="py-4 px-4 text-center">
                            <span className={`inline-block w-8 h-8 rounded-lg flex items-center justify-center text-xs ${blockClass}`}>
                              {count}
                            </span>
                          </td>
                        );
                      })}
                      <td className="py-4 px-4 text-center font-bold text-gray-300">
                        {total}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
