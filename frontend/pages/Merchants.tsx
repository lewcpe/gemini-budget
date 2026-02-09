
import React, { useEffect, useState } from 'react';
import { apiService } from '../apiService';
import { Merchant, Category } from '../types';
import {
  Store,
  Plus,
  Search,
  Edit3,
  Trash2,
  X,
  Loader2,
  AlertCircle,
  ChevronDown,
  Tags
} from 'lucide-react';

const Merchants: React.FC = () => {
  const [merchants, setMerchants] = useState<Merchant[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [merchantToDelete, setMerchantToDelete] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    id: '',
    name: '',
    default_category_id: ''
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [merchantData, categoryData] = await Promise.all([
        apiService.getMerchants({ q: searchTerm }),
        apiService.getCategories()
      ]);
      setMerchants(merchantData);
      setCategories(categoryData);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load merchant directory.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchData();
    }, 400);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const openCreateModal = () => {
    setError(null);
    setFormData({ id: '', name: '', default_category_id: '' });
    setIsModalOpen(true);
  };

  const openEditModal = (merchant: Merchant) => {
    setError(null);
    setFormData({
      id: merchant.id,
      name: merchant.name,
      default_category_id: merchant.default_category_id || ''
    });
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (formData.id) {
        await apiService.updateMerchant(formData.id, {
          name: formData.name,
          default_category_id: formData.default_category_id || null
        });
      } else {
        await apiService.createMerchant({
          name: formData.name,
          default_category_id: formData.default_category_id || null
        });
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
    setMerchantToDelete(id);
  };

  const confirmDelete = async () => {
    if (!merchantToDelete) return;
    try {
      await apiService.deleteMerchant(merchantToDelete);
      setMerchants(prev => prev.filter(m => m.id !== merchantToDelete));
      setMerchantToDelete(null);
    } catch (err: any) {
      setError(err.message || "Delete failed");
      setMerchantToDelete(null);
    }
  };

  const getCategoryName = (id: string | null) =>
    id ? categories.find(c => c.id === id)?.name : 'No Default Category';

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight">Merchant Database</h1>
          <p className="text-gray-500 font-medium">Link merchants to default categories for better AI automation.</p>
        </div>
        <button
          onClick={openCreateModal}
          className="flex items-center justify-center space-x-2 bg-blue-600 text-white px-6 py-3 rounded-2xl font-black shadow-xl shadow-blue-100 hover:bg-blue-700 transition-all transform active:scale-95"
        >
          <Plus size={20} />
          <span>New Merchant</span>
        </button>
      </header>

      <div className="bg-white p-4 rounded-3xl border border-gray-100 shadow-sm">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
          <input
            type="text"
            placeholder="Search merchant directory..."
            className="w-full pl-12 pr-4 py-3 bg-gray-50 border-none rounded-2xl text-sm font-bold outline-none ring-4 ring-transparent focus:ring-blue-50/50 transition-all"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      {error && (
        <div className="bg-rose-50 border border-rose-100 p-4 rounded-3xl flex items-center justify-between text-rose-600">
          <div className="flex items-center space-x-3">
            <AlertCircle size={20} />
            <span className="font-bold text-sm">{error}</span>
          </div>
          <button onClick={() => setError(null)} className="p-1 hover:bg-rose-100 rounded-full"><X size={16} /></button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading && merchants.length === 0 ? (
          [1, 2, 3, 4, 5, 6].map(i => (
            <div key={i} className="h-32 bg-white rounded-3xl border border-gray-100 animate-pulse"></div>
          ))
        ) : (
          merchants.map(merchant => (
            <div key={merchant.id} className="bg-white p-6 rounded-[32px] border border-gray-100 shadow-sm group hover:shadow-xl hover:shadow-blue-50/50 transition-all duration-300 relative">
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center shadow-sm">
                    <Store size={22} />
                  </div>
                  <div>
                    <h3 className="font-black text-gray-900 truncate max-w-[140px]">{merchant.name}</h3>
                    <div className="flex items-center space-x-1.5 mt-1">
                      <Tags size={12} className="text-gray-400" />
                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest truncate max-w-[120px]">
                        {getCategoryName(merchant.default_category_id)}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-all">
                  <button
                    onClick={() => openEditModal(merchant)}
                    className="p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-xl transition-colors"
                  >
                    <Edit3 size={16} />
                  </button>
                  <button
                    onClick={() => handleDeleteClick(merchant.id)}
                    className="p-2 text-gray-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-colors"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}

        {merchants.length === 0 && !loading && !error && (
          <div className="col-span-full py-20 text-center bg-white border-2 border-dashed border-gray-100 rounded-[40px] flex flex-col items-center justify-center">
            <div className="w-20 h-20 bg-gray-50 rounded-full flex items-center justify-center mb-6 text-gray-300">
              <Store size={40} />
            </div>
            <h3 className="text-xl font-black text-gray-900">No matching merchants</h3>
            <p className="text-gray-400 mt-2 max-w-xs mx-auto">Start building your lookup table to automate future categorization.</p>
            <button onClick={openCreateModal} className="mt-8 px-8 py-3 bg-gray-900 text-white rounded-2xl font-bold shadow-lg">Add First Merchant</button>
          </div>
        )}
      </div>

      {/* Merchant Edit/Create Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-md animate-in fade-in duration-300">
          <div className="bg-white w-full max-w-md rounded-[40px] p-8 shadow-2xl animate-in zoom-in duration-300">
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-2xl font-black text-gray-900 tracking-tight">
                {formData.id ? 'Edit Merchant' : 'New Merchant'}
              </h2>
              <button onClick={() => setIsModalOpen(false)} className="p-2 text-gray-400 hover:text-gray-900 transition-colors">
                <X size={24} />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="space-y-4">
                <label className="block text-[10px] font-black text-gray-400 uppercase tracking-widest px-1">Merchant Identity</label>
                <input
                  required
                  className="w-full px-6 py-4 bg-gray-50 border-none rounded-2xl text-sm font-bold outline-none ring-4 ring-transparent focus:ring-blue-50 transition-all"
                  placeholder="e.g. Starbucks, Amazon, Shell"
                  value={formData.name}
                  onChange={e => setFormData({ ...formData, name: e.target.value })}
                />
              </div>

              <div className="space-y-4">
                <label className="block text-[10px] font-black text-gray-400 uppercase tracking-widest px-1">Default Categorization</label>
                <div className="relative">
                  <select
                    className="appearance-none w-full px-6 py-4 bg-gray-50 border-none rounded-2xl text-sm font-bold outline-none cursor-pointer"
                    value={formData.default_category_id}
                    onChange={e => setFormData({ ...formData, default_category_id: e.target.value })}
                  >
                    <option value="">No Default Category</option>
                    {categories.map(cat => (
                      <option key={cat.id} value={cat.id}>{cat.name}</option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-6 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={20} />
                </div>
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full py-5 bg-blue-600 text-white rounded-[24px] font-black shadow-xl shadow-blue-100 hover:bg-blue-700 transition-all flex items-center justify-center space-x-2 disabled:opacity-50 disabled:bg-gray-400"
              >
                {submitting ? <Loader2 size={20} className="animate-spin" /> : <span>{formData.id ? 'Save Changes' : 'Create Merchant'}</span>}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {merchantToDelete && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-md animate-in fade-in duration-300">
          <div className="bg-white w-full max-w-sm rounded-[40px] p-10 text-center shadow-2xl animate-in zoom-in duration-300">
            <div className="w-20 h-20 bg-rose-50 text-rose-600 rounded-3xl flex items-center justify-center mx-auto mb-6">
              <Trash2 size={40} />
            </div>
            <h2 className="text-2xl font-black text-gray-900 mb-2">Delete Merchant?</h2>
            <p className="text-gray-500 font-medium mb-10">This will remove the merchant from your directory. Automatic categorization won't be affected for existing transactions.</p>

            <div className="flex flex-col space-y-3">
              <button
                onClick={confirmDelete}
                className="w-full py-4 bg-rose-600 text-white rounded-2xl font-black shadow-xl shadow-rose-100 hover:bg-rose-700 transition-all active:scale-95"
              >
                Confirm Delete
              </button>
              <button
                onClick={() => setMerchantToDelete(null)}
                className="w-full py-4 bg-gray-50 text-gray-500 rounded-2xl font-black hover:bg-gray-100 transition-all active:scale-95"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Merchants;