
import React, { useEffect, useState } from 'react';
import { apiService } from '../apiService';
import { Account, AccountType } from '../types';
import { 
  Plus, 
  Trash2, 
  Pencil,
  Landmark,
  CreditCard,
  Loader2,
  AlertCircle
} from 'lucide-react';

const Accounts: React.FC = () => {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [accountToDelete, setAccountToDelete] = useState<Account | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    id: '',
    name: '',
    type: AccountType.ASSET,
    sub_type: '',
    current_balance: 0,
    currency: 'USD',
    description: ''
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const data = await apiService.getAccounts();
      setAccounts(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load accounts.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const openCreateModal = () => {
    setFormData({
      id: '',
      name: '',
      type: AccountType.ASSET,
      sub_type: '',
      current_balance: 0,
      currency: 'USD',
      description: ''
    });
    setIsModalOpen(true);
  };

  const openEditModal = (acc: Account) => {
    setFormData({
      id: acc.id,
      name: acc.name,
      type: acc.type,
      sub_type: acc.sub_type || '',
      current_balance: acc.current_balance,
      currency: acc.currency,
      description: acc.description || ''
    });
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (formData.id) {
        const { id, ...updatePayload } = formData;
        await apiService.updateAccount(id, updatePayload);
      } else {
        const { id, ...createPayload } = formData;
        await apiService.createAccount(createPayload);
      }
      setIsModalOpen(false);
      fetchData();
    } catch (err: any) {
      alert(err.message || "Operation failed");
    } finally {
      setSubmitting(false);
    }
  };

  const executeDelete = async () => {
    if (!accountToDelete) return;
    setIsDeleting(true);
    try {
      await apiService.deleteAccount(accountToDelete.id);
      setAccounts(prev => prev.filter(a => a.id !== accountToDelete.id));
      setAccountToDelete(null);
    } catch (err: any) {
      alert(err.message || "Delete failed");
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight">Accounts</h1>
          <p className="text-gray-500 font-medium">Manage your bank accounts, credit cards and assets.</p>
        </div>
        <button 
          onClick={openCreateModal}
          className="flex items-center justify-center space-x-2 bg-blue-600 text-white px-6 py-3 rounded-2xl font-black shadow-xl shadow-blue-100 hover:bg-blue-700 transition-all transform active:scale-95"
        >
          <Plus size={20} />
          <span>New Account</span>
        </button>
      </header>

      {error && (
        <div className="bg-rose-50 border border-rose-100 p-6 rounded-3xl flex items-center space-x-4">
          <AlertCircle className="text-rose-600" size={24} />
          <p className="text-rose-700 text-sm font-bold">{error}</p>
          <button onClick={fetchData} className="ml-auto text-xs font-black uppercase text-rose-600 underline">Retry</button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {loading && accounts.length === 0 ? (
          [1, 2, 3].map(i => (
            <div key={i} className="h-48 bg-white rounded-[32px] border border-gray-100 animate-pulse"></div>
          ))
        ) : (
          accounts.map(acc => (
            <div key={acc.id} className="bg-white p-8 rounded-[40px] border border-gray-100 shadow-sm relative group hover:shadow-xl hover:shadow-blue-50/50 transition-all duration-300 flex flex-col h-full">
              <div className="flex items-center justify-between mb-8">
                <div className={`p-4 rounded-2xl shadow-sm ${acc.type === AccountType.ASSET ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'}`}>
                  {acc.sub_type?.toLowerCase().includes('card') ? <CreditCard size={28} /> : <Landmark size={28} />}
                </div>
                <div className="flex items-center space-x-2 opacity-0 group-hover:opacity-100 transition-all transform translate-y-2 group-hover:translate-y-0">
                  <button onClick={() => openEditModal(acc)} className="p-2.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-colors"><Pencil size={18} /></button>
                  <button onClick={() => setAccountToDelete(acc)} className="p-2.5 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-colors"><Trash2 size={18} /></button>
                </div>
              </div>
              <h3 className="font-black text-xl text-gray-900 leading-tight">{acc.name}</h3>
              <div className="flex items-center space-x-2 mt-2 mb-6">
                <span className={`text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-md ${acc.type === AccountType.ASSET ? 'bg-emerald-50 text-emerald-600' : 'bg-rose-50 text-rose-600'}`}>{acc.type}</span>
                {acc.sub_type && <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">• {acc.sub_type}</span>}
              </div>
              <div className="mt-auto pt-6 border-t border-gray-50 flex flex-col">
                <span className="text-gray-400 text-[10px] font-bold uppercase tracking-widest mb-1">Available Balance</span>
                <span className={`text-3xl font-black tracking-tight ${acc.type === AccountType.LIABILITY ? 'text-rose-600' : 'text-gray-900'}`}>
                  {acc.type === AccountType.LIABILITY ? '-' : ''}${Math.abs(acc.current_balance).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
                <span className="text-[10px] text-gray-400 font-bold uppercase mt-1">{acc.currency}</span>
              </div>
            </div>
          ))
        )}
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-md animate-in fade-in duration-300">
          <div className="bg-white w-full max-w-lg rounded-[48px] p-10 shadow-2xl animate-in zoom-in duration-300">
            <h2 className="text-3xl font-black text-gray-900 mb-8">{formData.id ? 'Edit Account' : 'New Account'}</h2>
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label className="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2 px-1">Account Name</label>
                <input required className="w-full px-6 py-4 bg-gray-50 border-none rounded-2xl text-sm font-bold outline-none ring-4 ring-transparent focus:ring-blue-50 transition-all" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2 px-1">Type</label>
                  <select className="w-full px-6 py-4 bg-gray-50 border-none rounded-2xl text-sm font-bold outline-none" value={formData.type} onChange={e => setFormData({...formData, type: e.target.value as AccountType})}>
                    <option value={AccountType.ASSET}>Asset</option>
                    <option value={AccountType.LIABILITY}>Liability</option>
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2 px-1">Balance</label>
                  <input type="number" step="0.01" className="w-full px-6 py-4 bg-gray-50 border-none rounded-2xl text-sm font-bold outline-none" value={formData.current_balance} onChange={e => setFormData({...formData, current_balance: parseFloat(e.target.value) || 0})} />
                </div>
              </div>
              <div className="flex gap-4 mt-10">
                <button type="button" onClick={() => setIsModalOpen(false)} className="flex-1 px-8 py-4 text-sm font-black text-gray-500 hover:bg-gray-100 rounded-2xl">Cancel</button>
                <button type="submit" disabled={submitting} className="flex-2 px-10 py-4 text-sm font-black text-white bg-blue-600 rounded-2xl shadow-xl shadow-blue-100">
                  {submitting ? <Loader2 size={18} className="animate-spin" /> : 'Save Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {accountToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-md animate-in fade-in duration-300">
          <div className="bg-white w-full max-w-md rounded-[40px] p-8 shadow-2xl animate-in zoom-in duration-300">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-rose-50 text-rose-600 rounded-full flex items-center justify-center mx-auto mb-4"><Trash2 size={32} /></div>
              <h2 className="text-2xl font-black text-gray-900">Delete Account?</h2>
              <p className="text-gray-500 mt-2">Are you sure you want to delete <span className="text-gray-900 font-bold">{accountToDelete.name}</span>?</p>
            </div>
            <div className="flex gap-4">
              <button onClick={() => setAccountToDelete(null)} className="flex-1 px-6 py-4 text-sm font-black text-gray-500 hover:bg-gray-50 rounded-2xl">Cancel</button>
              <button onClick={executeDelete} disabled={isDeleting} className="flex-1 px-6 py-4 text-sm font-black text-white bg-rose-600 rounded-2xl shadow-xl shadow-rose-100">
                {isDeleting ? <Loader2 size={18} className="animate-spin" /> : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Accounts;
