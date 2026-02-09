
import React, { useEffect, useState } from 'react';
import { apiService } from '../apiService';
import { Category, CategoryType } from '../types';
import { Tags, Plus, Trash2, AlertCircle, X } from 'lucide-react';

const Categories: React.FC = () => {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [newCat, setNewCat] = useState({ name: '', type: CategoryType.EXPENSE });
  const [error, setError] = useState<string | null>(null);
  const [categoryToDelete, setCategoryToDelete] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      const data = await apiService.getCategories();
      setCategories(data);
      setError(null);
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to load categories');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCat.name) return;
    setError(null);
    try {
      await apiService.createCategory(newCat);
      setNewCat({ ...newCat, name: '' });
      fetchData();
    } catch (err: any) {
      setError("Failed to create category: " + (err.message || "Unknown error"));
    }
  };

  const handleDeleteClick = (id: string) => {
    setCategoryToDelete(id);
  };

  const confirmDelete = async () => {
    if (!categoryToDelete) return;
    try {
      await apiService.deleteCategory(categoryToDelete);
      setCategoryToDelete(null);
      fetchData();
    } catch (err: any) {
      setError("Failed to delete category: " + (err.message || "Unknown error"));
      setCategoryToDelete(null);
    }
  };

  return (
    <div className="space-y-8 max-w-2xl">
      <header>
        <h1 className="text-2xl font-bold text-gray-900">Categories</h1>
        <p className="text-gray-500">Organize your spending with custom categories.</p>
      </header>

      {error && (
        <div className="bg-rose-50 border border-rose-100 p-4 rounded-2xl flex items-center justify-between text-rose-600">
          <div className="flex items-center space-x-3">
            <AlertCircle size={20} />
            <span className="font-bold text-sm">{error}</span>
          </div>
          <button onClick={() => setError(null)} className="p-1 hover:bg-rose-100 rounded-full"><X size={16} /></button>
        </div>
      )}

      <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm">
        <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest mb-4">Add Category</h3>
        <form onSubmit={handleCreate} className="flex gap-3">
          <input 
            className="flex-1 px-4 py-2.5 bg-gray-50 border-none rounded-xl text-sm outline-none ring-2 ring-transparent focus:ring-blue-100"
            placeholder="Category name (e.g. Groceries)"
            value={newCat.name}
            onChange={e => setNewCat({...newCat, name: e.target.value})}
          />
          <select 
            className="px-4 py-2.5 bg-gray-50 border-none rounded-xl text-sm outline-none"
            value={newCat.type}
            onChange={e => setNewCat({...newCat, type: e.target.value as CategoryType})}
          >
            <option value={CategoryType.EXPENSE}>Expense</option>
            <option value={CategoryType.INCOME}>Income</option>
          </select>
          <button className="bg-blue-600 text-white p-2.5 rounded-xl hover:bg-blue-700 transition-colors">
            <Plus size={20} />
          </button>
        </form>
      </div>

      <div className="space-y-6">
        <section>
          <div className="flex items-center space-x-2 mb-4">
            <div className="w-2 h-2 rounded-full bg-rose-500"></div>
            <h3 className="font-bold text-gray-700">Expense Categories</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {categories.filter(c => c.type === CategoryType.EXPENSE).map(cat => (
              <div key={cat.id} className="flex items-center justify-between p-4 bg-white rounded-xl border border-gray-100 hover:border-rose-100 transition-colors group">
                <span className="text-sm font-semibold">{cat.name}</span>
                <button onClick={() => handleDeleteClick(cat.id)} className="p-2 text-gray-300 hover:text-rose-600 transition-colors opacity-0 group-hover:opacity-100">
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        </section>

        <section>
          <div className="flex items-center space-x-2 mb-4">
            <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
            <h3 className="font-bold text-gray-700">Income Categories</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {categories.filter(c => c.type === CategoryType.INCOME).map(cat => (
              <div key={cat.id} className="flex items-center justify-between p-4 bg-white rounded-xl border border-gray-100 hover:border-emerald-100 transition-colors group">
                <span className="text-sm font-semibold">{cat.name}</span>
                <button onClick={() => handleDeleteClick(cat.id)} className="p-2 text-gray-300 hover:text-rose-600 transition-colors opacity-0 group-hover:opacity-100">
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Delete Confirmation Modal */}
      {categoryToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/60 backdrop-blur-md animate-in fade-in duration-300">
          <div className="bg-white w-full max-w-sm rounded-[32px] p-8 shadow-2xl">
            <div className="text-center mb-6">
              <div className="w-14 h-14 bg-rose-50 text-rose-600 rounded-full flex items-center justify-center mx-auto mb-4"><Trash2 size={24} /></div>
              <h2 className="text-xl font-black text-gray-900">Delete Category?</h2>
              <p className="text-gray-500 mt-2 text-sm">Transactions linked to this category will become uncategorized.</p>
            </div>
            <div className="flex gap-3">
              <button onClick={() => setCategoryToDelete(null)} className="flex-1 px-4 py-3 text-sm font-black text-gray-500 hover:bg-gray-50 rounded-xl">Cancel</button>
              <button onClick={confirmDelete} className="flex-1 px-4 py-3 text-sm font-black text-white bg-rose-600 hover:bg-rose-700 rounded-xl shadow-lg shadow-rose-100">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Categories;
