
import React, { useEffect, useState } from 'react';
import { apiService } from '../apiService';
import { Pricing } from '../types';
import { 
  CircleDollarSign, 
  RefreshCw, 
  Search, 
  TrendingUp, 
  Clock,
  Loader2,
  AlertCircle
} from 'lucide-react';
import { format } from 'date-fns';

const PricingPage: React.FC = () => {
  const [pricingList, setPricingList] = useState<Pricing[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshingId, setRefreshingId] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const data = await apiService.getPricing();
      setPricingList(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load pricing data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefresh = async (assetCode: string) => {
    setRefreshingId(assetCode);
    try {
      await apiService.refreshPrice(assetCode);
      await fetchData();
    } catch (err: any) {
      alert(`Failed to refresh ${assetCode}: ${err.message}`);
    } finally {
      setRefreshingId(null);
    }
  };

  const filteredList = pricingList.filter(p => 
    p.asset_code.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight">Market Data</h1>
          <p className="text-gray-500 font-medium">Real-time asset pricing powered by Gemini.</p>
        </div>
        <button 
          onClick={fetchData}
          disabled={loading}
          className="p-3 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-2xl transition-all"
        >
          <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
        </button>
      </header>

      {error && (
        <div className="bg-rose-50 border border-rose-100 p-6 rounded-3xl flex items-center space-x-4">
          <AlertCircle className="text-rose-600" size={24} />
          <p className="text-rose-700 text-sm font-bold">{error}</p>
          <button onClick={fetchData} className="ml-auto text-xs font-black uppercase text-rose-600 underline">Retry</button>
        </div>
      )}

      <div className="bg-white p-4 rounded-3xl border border-gray-100 shadow-sm">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
          <input 
            type="text" 
            placeholder="Search assets (e.g. BTC, ETH, AAPL)..." 
            className="w-full pl-12 pr-4 py-3 bg-gray-50 border-none rounded-2xl text-sm font-bold outline-none ring-4 ring-transparent focus:ring-blue-50/50 transition-all"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading && pricingList.length === 0 ? (
          [1, 2, 3].map(i => (
            <div key={i} className="h-40 bg-white rounded-[32px] border border-gray-100 animate-pulse"></div>
          ))
        ) : (
          filteredList.map(item => (
            <div key={item.id} className="bg-white p-6 rounded-[32px] border border-gray-100 shadow-sm hover:shadow-xl hover:shadow-emerald-50/50 transition-all duration-300">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center shadow-sm">
                    <TrendingUp size={22} />
                  </div>
                  <div>
                    <h3 className="font-black text-gray-900 text-lg">{item.asset_code}</h3>
                    <p className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">Asset</p>
                  </div>
                </div>
                <button 
                  onClick={() => handleRefresh(item.asset_code)}
                  disabled={refreshingId === item.asset_code}
                  className="p-2.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-all disabled:opacity-50"
                >
                  <RefreshCw size={18} className={refreshingId === item.asset_code ? 'animate-spin' : ''} />
                </button>
              </div>

              <div className="flex flex-col space-y-4">
                <div>
                   <span className="text-gray-400 text-[10px] font-bold uppercase tracking-widest block mb-1">Current Price (USD)</span>
                   <span className="text-3xl font-black text-gray-900 tracking-tight">
                      ${item.price_in_usd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 6 })}
                   </span>
                </div>
                
                <div className="flex items-center space-x-2 text-gray-400 text-xs font-medium pt-4 border-t border-gray-50">
                   <Clock size={12} />
                   <span>Updated {format(new Date(item.last_updated), 'MMM d, HH:mm:ss')}</span>
                </div>
              </div>
            </div>
          ))
        )}

        {filteredList.length === 0 && !loading && !error && (
           <div className="col-span-full py-20 text-center text-gray-400">
              <div className="w-16 h-16 bg-gray-100 text-gray-400 rounded-full flex items-center justify-center mx-auto mb-4">
                 <CircleDollarSign size={32} />
              </div>
              <p className="font-bold">No pricing data found.</p>
              <p className="text-xs mt-1">Pricing entries are created automatically when assets are detected.</p>
           </div>
        )}
      </div>
    </div>
  );
};

export default PricingPage;
