
import React, { useEffect, useState } from 'react';
import { apiService } from '../apiService';
import { Transaction, Account, Category, TransactionType } from '../types';
import {
  Search,
  Trash2,
  Edit,
  Receipt,
  Plus,
  X,
  Loader2,
  AlertCircle,
  ArrowRightLeft,
  TrendingDown,
  TrendingUp,
  ArrowRight
} from 'lucide-react';
import { format } from 'date-fns';

const Transactions: React.FC = () => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transactionToDelete, setTransactionToDelete] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    id: '',
    account_id: '',
    category_id: '',
    amount: 0,
    type: TransactionType.EXPENSE,
    target_account_id: '',
    transaction_date: format(new Date(), 'yyyy-MM-dd'),
    merchant: '',
    note: ''
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [txs, accs, cats] = await Promise.all([
        apiService.getTransactions({ q: searchTerm }),
        apiService.getAccounts(),
        apiService.getCategories()
      ]);
      setTransactions(txs);
      setAccounts(accs);
      setCategories(cats);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchData();
    }, 500);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const openCreateModal = () => {
    setError(null);
    setFormData({
      id: '',
      account_id: accounts.length > 0 ? accounts[0].id : '',
      category_id: '',
      amount: 0,
      type: TransactionType.EXPENSE,
      target_account_id: '',
      transaction_date: format(new Date(), 'yyyy-MM-dd'),
      merchant: '',
      note: ''
    });
    setIsModalOpen(true);
  };

  const openEditModal = (tx: Transaction) => {
    setError(null);
    setFormData({
      id: tx.id,
      account_id: tx.account_id,
      category_id: tx.category_id || '',
      amount: tx.amount,
      type: tx.type,
      target_account_id: tx.target_account_id || '',
      transaction_date: tx.transaction_date.split('T')[0],
      merchant: tx.merchant || '',
      note: tx.note === 'Internal ledger entry' ? '' : (tx.note || '')
    });
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.account_id) {
      setError("Please select an account");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        account_id: formData.account_id,
        category_id: formData.category_id || null,
        amount: Number(formData.amount),
        type: formData.type,
        target_account_id: formData.type === TransactionType.TRANSFER ? (formData.target_account_id || null) : null,
        transaction_date: new Date(formData.transaction_date).toISOString(),
        merchant: formData.merchant || null,
        note: formData.note || null
      };

      if (formData.id) {
        await apiService.updateTransaction(formData.id, payload);
      } else {
        await apiService.createTransaction(payload);
      }
      setIsModalOpen(false);
      fetchData();
    } catch (err: any) {
      setError(err.message || "Operation failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteClick = (id: string) => {
    setTransactionToDelete(id);
  };

  const confirmDelete = async () => {
    if (!transactionToDelete) return;
    try {
      await apiService.deleteTransaction(transactionToDelete);
      setTransactions(prev => prev.filter(t => t.id !== transactionToDelete));
      setTransactionToDelete(null);
    } catch (err: any) {
      setError('Failed to delete: ' + (err.message || 'Unknown error'));
      setTransactionToDelete(null);
    }
  };

  const getAccountName = (id: string) => accounts.find(a => a.id === id)?.name || 'Unknown';
  const getCategoryName = (id: string | null) => id ? categories.find(c => c.id === id)?.name : 'Uncategorized';

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight">Ledger</h1>
          <p className="text-gray-500 font-medium">Detailed log of all financial activities.</p>
        </div>
        <button
          onClick={openCreateModal}
          className="flex items-center space-x-2 px-6 py-2.5 bg-blue-600 text-white rounded-xl text-sm font-black shadow-xl shadow-blue-100 hover:bg-blue-700 transition-all transform active:scale-95"
        >
          <Plus size={18} />
          <span>Add Entry</span>
        </button>
      </header>

      <div className="bg-white p-5 rounded-[28px] border border-gray-100 shadow-sm flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input type="text" placeholder="Search entries..." className="w-full pl-11 pr-4 py-3 bg-gray-50 border-none rounded-2xl text-sm font-bold outline-none" value={searchTerm} onChange={e => setSearchTerm(e.target.value)} />
        </div>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-100 p-4 rounded-2xl flex items-center justify-between text-rose-600">
          <div className="flex items-center space-x-3">
            <AlertCircle size={20} />
            <span className="font-bold text-sm">{error}</span>
          </div>
          <button onClick={() => setError(null)} className="p-1 hover:bg-rose-100 rounded-full"><X size={16} /></button>
        </div>
      )}

      <div className="bg-white rounded-[32px] border border-gray-100 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50/50 text-[10px] uppercase tracking-wider font-black text-gray-400 border-b border-gray-50">
                <th className="px-8 py-5">Entry</th>
                <th className="px-6 py-5">Account</th>
                <th className="px-6 py-5">Category</th>
                <th className="px-6 py-5">Date</th>
                <th className="px-6 py-5 text-right">Amount</th>
                <th className="px-8 py-5"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {loading && transactions.length === 0 ? (
                <tr><td colSpan={6} className="px-6 py-20 text-center text-gray-400 italic font-medium">Syncing...</td></tr>
              ) : transactions.length > 0 ? (
                transactions.map(tx => (
                  <tr key={tx.id} className="hover:bg-gray-50/60 transition-colors group">
                    <td className="px-8 py-5">
                      <div className="flex items-center space-x-4">
                        <div className={`p-2.5 rounded-xl shadow-sm ${tx.type === TransactionType.INCOME ? 'bg-emerald-50 text-emerald-600' :
                            tx.type === TransactionType.TRANSFER ? 'bg-blue-50 text-blue-600' :
                              'bg-gray-50 text-gray-900'
                          }`}>
                          {tx.type === TransactionType.INCOME ? <TrendingUp size={18} /> :
                            tx.type === TransactionType.TRANSFER ? <ArrowRightLeft size={18} /> :
                              <TrendingDown size={18} />}
                        </div>
                        <div>
                          <div className="flex items-center space-x-2">
                            <p className="font-black text-gray-900 truncate">{tx.merchant || (tx.type === TransactionType.TRANSFER ? 'Funds Transfer' : 'General Entry')}</p>
                            {tx.type === TransactionType.TRANSFER && tx.target_account_id && (
                              <div className="flex items-center text-[10px] font-black text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md uppercase tracking-wider">
                                <ArrowRight size={10} className="mr-1" />
                                {getAccountName(tx.target_account_id)}
                              </div>
                            )}
                          </div>
                          <p className="text-[10px] text-gray-400 font-bold truncate">
                            {tx.note === 'Internal ledger entry' ? '' : tx.note}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-5 text-[10px] font-black uppercase text-gray-500">{getAccountName(tx.account_id)}</td>
                    <td className="px-6 py-5 text-xs font-bold text-gray-500">{getCategoryName(tx.category_id)}</td>
                    <td className="px-6 py-5 text-xs text-gray-400 uppercase">{format(new Date(tx.transaction_date), 'MMM d, yyyy')}</td>
                    <td className={`px-6 py-5 text-right font-black text-sm ${tx.type === TransactionType.INCOME ? 'text-emerald-600' :
                        tx.type === TransactionType.TRANSFER ? 'text-blue-600' :
                          'text-gray-900'
                      }`}>
                      {tx.type === TransactionType.INCOME ? '+' : tx.type === TransactionType.TRANSFER ? '→' : '-'}${Math.abs(tx.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-8 py-5 text-right">
                      <div className="flex items-center justify-end space-x-1 opacity-0 group-hover:opacity-100 transition-all">
                        <button onClick={() => openEditModal(tx)} className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl"><Edit size={16} /></button>
                        <button onClick={() => handleDeleteClick(tx.id)} className="p-2 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl"><Trash2 size={16} /></button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr><td colSpan={6} className="px-6 py-32 text-center text-gray-300 font-black">No entries found</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-md animate-in fade-in duration-300">
          <div className="bg-white w-full max-w-2xl rounded-[40px] p-8 md:p-12 shadow-2xl animate-in zoom-in duration-300 overflow-y-auto max-h-[90vh]">
            <h2 className="text-3xl font-black text-gray-900 mb-10">{formData.id ? 'Edit Entry' : 'New Entry'}</h2>
            {error && (
              <div className="bg-rose-50 border border-rose-100 p-4 mb-6 rounded-2xl flex items-center text-rose-600 space-x-3">
                <AlertCircle size={20} />
                <span className="font-bold text-sm">{error}</span>
              </div>
            )}
            <form onSubmit={handleSubmit} className="space-y-8">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-3">
                  <label className="block text-[10px] font-black text-gray-400 uppercase px-1">Merchant</label>
                  <input className="w-full px-6 py-4 bg-gray-50 border-none rounded-2xl text-sm font-bold outline-none ring-4 ring-transparent focus:ring-blue-50 transition-all" value={formData.merchant} onChange={e => setFormData({ ...formData, merchant: e.target.value })} />
                </div>
                <div className="space-y-3">
                  <label className="block text-[10px] font-black text-gray-400 uppercase px-1">Amount</label>
                  <input type="number" step="0.01" required className="w-full px-6 py-4 bg-gray-50 border-none rounded-2xl text-sm font-bold outline-none ring-4 ring-transparent focus:ring-blue-50 transition-all" value={formData.amount} onChange={e => setFormData({ ...formData, amount: parseFloat(e.target.value) || 0 })} />
                </div>
                <div className="space-y-3">
                  <label className="block text-[10px] font-black text-gray-400 uppercase px-1">Account</label>
                  <select required className="w-full px-6 py-4 bg-gray-50 border-none rounded-2xl text-sm font-bold outline-none ring-4 ring-transparent focus:ring-blue-50 transition-all" value={formData.account_id} onChange={e => setFormData({ ...formData, account_id: e.target.value })}>
                    <option value="" disabled>Select account...</option>
                    {accounts.map(acc => <option key={acc.id} value={acc.id}>{acc.name}</option>)}
                  </select>
                </div>
                <div className="space-y-3">
                  <label className="block text-[10px] font-black text-gray-400 uppercase px-1">Category</label>
                  <select className="w-full px-6 py-4 bg-gray-50 border-none rounded-2xl text-sm font-bold outline-none ring-4 ring-transparent focus:ring-blue-50 transition-all" value={formData.category_id} onChange={e => setFormData({ ...formData, category_id: e.target.value })}>
                    <option value="">Uncategorized</option>
                    {categories.map(cat => <option key={cat.id} value={cat.id}>{cat.name}</option>)}
                  </select>
                </div>
                <div className="space-y-3">
                  <label className="block text-[10px] font-black text-gray-400 uppercase px-1">Entry Type</label>
                  <select required className="w-full px-6 py-4 bg-gray-50 border-none rounded-2xl text-sm font-bold outline-none ring-4 ring-transparent focus:ring-blue-50 transition-all" value={formData.type} onChange={e => setFormData({ ...formData, type: e.target.value as TransactionType })}>
                    <option value={TransactionType.EXPENSE}>Expense</option>
                    <option value={TransactionType.INCOME}>Income</option>
                    <option value={TransactionType.TRANSFER}>Transfer</option>
                  </select>
                </div>
                {formData.type === TransactionType.TRANSFER && (
                  <div className="space-y-3">
                    <label className="block text-[10px] font-black text-gray-400 uppercase px-1">Target Account</label>
                    <select required className="w-full px-6 py-4 bg-gray-50 border-none rounded-2xl text-sm font-bold outline-none ring-4 ring-transparent focus:ring-blue-50 transition-all" value={formData.target_account_id} onChange={e => setFormData({ ...formData, target_account_id: e.target.value })}>
                      <option value="" disabled>Select target account...</option>
                      {accounts.filter(a => a.id !== formData.account_id).map(acc => <option key={acc.id} value={acc.id}>{acc.name}</option>)}
                    </select>
                  </div>
                )}
                <div className="md:col-span-2 space-y-3">
                  <label className="block text-[10px] font-black text-gray-400 uppercase px-1">Note</label>
                  <textarea className="w-full px-6 py-4 bg-gray-50 border-none rounded-2xl text-sm font-bold outline-none h-24 resize-none ring-4 ring-transparent focus:ring-blue-50 transition-all" placeholder="Enter transaction note..." value={formData.note} onChange={e => setFormData({ ...formData, note: e.target.value })} />
                </div>
              </div>
              <div className="flex gap-4 mt-8">
                <button type="button" onClick={() => setIsModalOpen(false)} className="flex-1 px-8 py-5 text-sm font-black text-gray-400 hover:bg-gray-50 rounded-2xl">Discard</button>
                <button type="submit" disabled={submitting} className="flex-[2] px-12 py-5 text-sm font-black text-white bg-blue-600 rounded-2xl shadow-xl shadow-blue-100 transition-all">
                  {submitting ? <Loader2 size={20} className="animate-spin mx-auto" /> : 'Commit Entry'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {transactionToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-md animate-in fade-in duration-300">
          <div className="bg-white w-full max-w-md rounded-[40px] p-8 shadow-2xl animate-in zoom-in slide-in-from-bottom-8 duration-500">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-rose-50 text-rose-600 rounded-full flex items-center justify-center mx-auto mb-4"><Trash2 size={32} /></div>
              <h2 className="text-2xl font-black text-gray-900">Delete Entry?</h2>
              <p className="text-gray-500 mt-2 font-medium">Are you sure you want to remove this transaction record?</p>
            </div>
            <div className="flex gap-4">
              <button
                onClick={() => setTransactionToDelete(null)}
                className="flex-1 px-6 py-4 text-sm font-black text-gray-500 hover:bg-gray-50 rounded-2xl transition-all"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                className="flex-1 px-6 py-4 text-sm font-black text-white bg-rose-600 hover:bg-rose-700 rounded-2xl shadow-xl shadow-rose-100 transition-all"
              >
                Confirm Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Transactions;
