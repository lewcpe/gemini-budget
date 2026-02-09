
import React, { useEffect, useState } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import {
  Wallet,
  ArrowUpRight,
  ArrowDownRight,
  Banknote,
  TrendingUp,
  Clock,
  ChevronRight,
  Receipt,
  AlertTriangle,
  RefreshCw,
  Settings as SettingsIcon
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { apiService } from '../apiService';
import { Account, WealthReport, Transaction, AccountType } from '../types';
import { format } from 'date-fns';

const StatCard = ({ title, amount, icon: Icon, color }: any) => (
  <div className="bg-white p-6 rounded-3xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
    <div className={`w-12 h-12 rounded-2xl ${color} flex items-center justify-center mb-6 shadow-lg shadow-gray-100`}>
      <Icon size={24} className="text-white" />
    </div>
    <p className="text-sm text-gray-400 font-bold uppercase tracking-wider">{title}</p>
    <h3 className="text-3xl font-black mt-1 text-gray-900">${amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</h3>
  </div>
);

const Dashboard: React.FC = () => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [wealthData, setWealthData] = useState<WealthReport | null>(null);
  const [recentTransactions, setRecentTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [accs, wealth, trans] = await Promise.all([
        apiService.getAccounts(),
        apiService.getWealthChart(),
        apiService.getTransactions({ limit: 5 })
      ]);
      setAccounts(accs);
      setWealthData(wealth);
      setRecentTransactions(trans);
    } catch (err: any) {
      console.error('Dashboard Error:', err);
      setError(err.message || 'Unable to load dashboard data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Robust calculation:
  // Assets are sum of positive balances, Liabilities (absolute) are sum of negative balances.
  const totalAssets = accounts
    .filter(a => a.current_balance > 0)
    .reduce((sum, a) => sum + a.current_balance, 0);

  const totalLiabilities = Math.abs(accounts
    .filter(a => a.current_balance < 0)
    .reduce((sum, a) => sum + a.current_balance, 0));

  const netWorth = accounts.reduce((sum, a) => sum + a.current_balance, 0);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-96 space-y-4">
        <Loader size={48} className="text-blue-600 animate-spin" />
        <p className="text-gray-400 font-bold animate-pulse uppercase tracking-widest text-xs">Syncing with Gemini...</p>
      </div>
    );
  }

  if (error) {
    const is405 = error.includes('405');
    return (
      <div className="max-w-xl mx-auto py-20 text-center space-y-8 animate-in fade-in zoom-in duration-300">
        <div className="w-20 h-20 bg-rose-50 text-rose-600 rounded-[32px] flex items-center justify-center mx-auto shadow-xl shadow-rose-100/50">
          <AlertTriangle size={40} />
        </div>
        <div>
          <h2 className="text-2xl font-black text-gray-900">Backend Connection Error</h2>
          <p className="text-gray-500 mt-3 leading-relaxed">
            {is405
              ? "The backend rejected our request (405). This usually means your server doesn't allow the 'X-Forwarded-Email' header or hasn't handled the CORS OPTIONS preflight."
              : error}
          </p>
        </div>
        <div className="flex items-center justify-center space-x-4">
          <button onClick={fetchData} className="px-6 py-3 bg-gray-900 text-white rounded-2xl font-bold shadow-lg hover:bg-black transition-all flex items-center space-x-2">
            <RefreshCw size={18} />
            <span>Try Again</span>
          </button>
          <Link to="/settings" className="px-6 py-3 bg-white border border-gray-100 text-gray-900 rounded-2xl font-bold shadow-sm hover:bg-gray-50 transition-all flex items-center space-x-2">
            <SettingsIcon size={18} />
            <span>Connection Settings</span>
          </Link>
        </div>
        {is405 && (
          <div className="p-6 bg-blue-50 rounded-3xl text-left border border-blue-100">
            <h4 className="text-sm font-bold text-blue-900 mb-2">How to fix (FastAPI):</h4>
            <code className="text-xs text-blue-700 block whitespace-pre-wrap leading-relaxed">
              allow_headers=["X-Forwarded-Email", "Content-Type"],<br />
              allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
            </code>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-4xl font-black text-gray-900 tracking-tight">Financial Health</h1>
          <p className="text-gray-500 mt-2 font-medium">Tracking {accounts.length} accounts across your net wealth.</p>
        </div>
        <div className="flex items-center space-x-3 text-xs font-bold text-gray-400 uppercase tracking-widest bg-white px-4 py-2 rounded-xl border border-gray-50 shadow-sm">
          <Clock size={14} className="text-blue-500" />
          <span>Updated {format(new Date(), 'hh:mm a')}</span>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <StatCard title="Net Worth" amount={netWorth} icon={TrendingUp} color="bg-gray-900" />
        <StatCard title="Total Assets" amount={totalAssets} icon={Wallet} color="bg-emerald-500" />
        <StatCard title="Liabilities" amount={totalLiabilities} icon={Banknote} color="bg-rose-500" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
        <div className="lg:col-span-2 bg-white p-8 rounded-[40px] border border-gray-100 shadow-sm">
          <div className="flex items-center justify-between mb-10">
            <h3 className="font-black text-xl text-gray-900 tracking-tight">Net Worth Curve</h3>
            <div className="flex bg-gray-50 p-1.5 rounded-2xl">
              <button className="px-5 py-2 text-xs font-bold rounded-xl bg-white shadow-sm text-gray-900">Month</button>
              <button className="px-5 py-2 text-xs font-bold text-gray-400">Year</button>
            </div>
          </div>
          <div className="h-[360px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={wealthData?.data_points || []}>
                <defs>
                  <linearGradient id="colorNet" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2563eb" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="6 6" vertical={false} stroke="#f1f5f9" />
                <XAxis
                  dataKey="date"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: '#94a3b8', fontSize: 11, fontWeight: 700 }}
                  tickFormatter={(val) => format(new Date(val), 'MMM d')}
                  dy={10}
                />
                <YAxis hide />
                <Tooltip
                  contentStyle={{ borderRadius: '24px', border: 'none', boxShadow: '0 20px 50px rgba(0,0,0,0.1)', padding: '16px' }}
                  labelStyle={{ fontWeight: 800, marginBottom: '4px' }}
                  formatter={(value: any) => [`$${value.toLocaleString()}`, 'Net Worth']}
                />
                <Area
                  type="monotone"
                  dataKey="net_worth"
                  stroke="#2563eb"
                  strokeWidth={4}
                  fillOpacity={1}
                  fill="url(#colorNet)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white p-8 rounded-[40px] border border-gray-100 shadow-sm">
          <h3 className="font-black text-xl text-gray-900 mb-8 tracking-tight">Accounts</h3>
          <div className="space-y-6">
            {accounts.slice(0, 5).map((acc) => (
              <div key={acc.id} className="flex items-center justify-between group cursor-pointer hover:bg-gray-50 p-3 -mx-3 rounded-2xl transition-all">
                <div className="flex items-center space-x-4">
                  <div className={`w-12 h-12 rounded-2xl flex items-center justify-center shadow-sm ${acc.type === AccountType.ASSET ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'}`}>
                    <Wallet size={20} />
                  </div>
                  <div>
                    <p className="text-sm font-black text-gray-900">{acc.name}</p>
                    <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">{acc.sub_type || acc.type}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className={`text-sm font-black ${acc.type === AccountType.ASSET ? 'text-gray-900' : 'text-rose-600'}`}>
                    {acc.type === AccountType.LIABILITY ? '-' : ''}${Math.abs(acc.current_balance).toLocaleString()}
                  </p>
                  <div className="flex justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                    <ChevronRight size={14} className="text-gray-300" />
                  </div>
                </div>
              </div>
            ))}
          </div>
          <Link to="/accounts" className="mt-10 block w-full py-4 text-center text-sm font-black text-blue-600 bg-blue-50 rounded-2xl hover:bg-blue-100 transition-colors">
            Manage Portfolio
          </Link>
        </div>
      </div>
    </div>
  );
};

const Loader = ({ size, className }: any) => (
  <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a9 9 0 1 1-6.219-8.56" /></svg>
);

export default Dashboard;
