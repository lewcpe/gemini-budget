
import React, { useEffect, useState, useRef, useCallback } from 'react';
import {
  FileUp,
  Inbox,
  Check,
  X,
  Edit3,
  FileText,
  Loader2,
  BrainCircuit,
  AlertCircle,
  RefreshCw,
  Clock,
  ChevronRight,
  Sparkles,
  Search,
  Landmark,
  ArrowRight,
  Wallet,
  ChevronDown,
  Tag,
  Tags,
  MoreHorizontal,
  Receipt
} from 'lucide-react';
import { apiService } from '../apiService';
import { ProposedChange, ProposalStatus, ProposalChangeType, Document, DocumentStatus, AccountType, TransactionType, Account, Category } from '../types';
import { format } from 'date-fns';

interface ProposalCardProps {
  proposal: ProposedChange;
  document?: Document;
  accounts: Account[];
  categories: Category[];
  onConfirm: (id: string, data: any) => void;
  onReject: (id: string) => void;
}

const ProposalCard: React.FC<ProposalCardProps> = ({
  proposal,
  document,
  accounts,
  categories,
  onConfirm,
  onReject
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editedData, setEditedData] = useState(JSON.parse(JSON.stringify(proposal.proposed_data)));

  // Normalize transactions to an array
  const getTransactions = () => {
    if (editedData.transactions && Array.isArray(editedData.transactions)) {
      return editedData.transactions;
    }
    // Handle flat structure or wrapped single transaction
    const { _new_account, transactions, ...rest } = editedData;
    // If rest contains transaction fields, treat as one transaction
    if (Object.keys(rest).length > 0) return [rest];
    return [];
  };

  const transactions = getTransactions();
  const isCreateAccount = proposal.change_type === ProposalChangeType.CREATE_ACCOUNT;
  const newAccount = editedData._new_account;

  const handleUpdateTransaction = (index: number, field: string, value: any) => {
    const newData = { ...editedData };

    if (newData.transactions && Array.isArray(newData.transactions)) {
      // Deep clone array to ensure React detects change
      const newTransactions = [...newData.transactions];
      newTransactions[index] = { ...newTransactions[index], [field]: value };
      newData.transactions = newTransactions;
    } else {
      // Flat structure update
      newData[field] = value;
    }
    setEditedData(newData);
  };

  const handleUpdateAccountField = (field: string, value: any) => {
    if (!isCreateAccount) return;
    const newData = { ...editedData };
    newData._new_account = { ...newData._new_account, [field]: value };
    setEditedData(newData);
  };

  const handleConfirmAction = () => {
    // Sanitize data: Ensure amounts are numbers
    const sanitizedData = JSON.parse(JSON.stringify(editedData));

    if (sanitizedData.transactions && Array.isArray(sanitizedData.transactions)) {
      sanitizedData.transactions = sanitizedData.transactions.map((t: any) => ({
        ...t,
        amount: Number(t.amount)
      }));
    } else {
      if (sanitizedData.amount !== undefined) {
        sanitizedData.amount = Number(sanitizedData.amount);
      }
    }
    onConfirm(proposal.id, sanitizedData);
  };

  const confidenceColor = (score: number | null) => {
    if (score === null || score === undefined) return 'bg-gray-100 text-gray-500 border-gray-200';
    if (score > 0.8) return 'bg-emerald-50 text-emerald-600 border-emerald-100';
    if (score > 0.5) return 'bg-amber-50 text-amber-600 border-amber-100';
    return 'bg-rose-50 text-rose-600 border-rose-100';
  };

  return (
    <div className="bg-white rounded-[32px] border border-gray-100 shadow-sm overflow-hidden mb-8 group hover:shadow-md transition-all duration-300">
      {/* Header */}
      <div className="p-5 border-b border-gray-50 bg-gradient-to-r from-blue-50/10 to-transparent flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 bg-blue-600 text-white rounded-2xl shadow-sm">
            {isCreateAccount ? <Landmark size={18} /> : <Sparkles size={18} />}
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h4 className="font-bold text-gray-900">
                {isCreateAccount ? 'New Account & History' : 'Transaction Suggestion'}
              </h4>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${confidenceColor(proposal.confidence_score)}`}>
                {proposal.confidence_score !== null ? `${Math.round(proposal.confidence_score * 100)}% Match` : 'AI Review'}
              </span>
            </div>
            <div className="flex items-center space-x-2 text-xs text-gray-500">
              <FileText size={12} />
              <span className="font-medium truncate max-w-[150px]">{document?.original_filename || 'Receipt Scan'}</span>
              <span>•</span>
              <Clock size={12} />
              <span>{format(new Date(proposal.created_at), 'MMM d, HH:mm')}</span>
            </div>
          </div>
        </div>
        <button
          onClick={() => setIsEditing(!isEditing)}
          className={`p-2.5 rounded-xl transition-all ${isEditing ? 'bg-blue-600 text-white shadow-lg shadow-blue-100' : 'text-gray-400 hover:text-blue-600 hover:bg-blue-50'}`}
        >
          <Edit3 size={18} />
        </button>
      </div>

      <div className="p-6 space-y-8">
        {/* Account Details Section (Only for CREATE_ACCOUNT) */}
        {isCreateAccount && newAccount && (
          <div className="bg-gray-50 p-6 rounded-[24px] border border-gray-100">
            <div className="flex items-center space-x-2 mb-4">
              <Wallet size={16} className="text-blue-600" />
              <h5 className="text-xs font-black text-gray-900 uppercase tracking-widest">Proposed Account</h5>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-[10px] uppercase font-bold text-gray-400">Account Name</label>
                {isEditing ? (
                  <input
                    className="w-full text-sm font-bold p-3 bg-white rounded-xl border border-gray-200 text-gray-900 focus:border-blue-500 outline-none shadow-sm"
                    value={newAccount.name || ''}
                    onChange={e => handleUpdateAccountField('name', e.target.value)}
                    placeholder="Account Name"
                  />
                ) : (
                  <p className="text-sm font-black text-gray-900">{newAccount.name}</p>
                )}
              </div>
              <div className="space-y-2">
                <label className="text-[10px] uppercase font-bold text-gray-400">Account Type</label>
                {isEditing ? (
                  <div className="relative">
                    <select
                      className="appearance-none w-full text-sm font-bold p-3 bg-white rounded-xl border border-gray-200 text-gray-900 focus:border-blue-500 outline-none shadow-sm cursor-pointer"
                      value={newAccount.type}
                      onChange={e => handleUpdateAccountField('type', e.target.value)}
                    >
                      <option value={AccountType.ASSET}>ASSET</option>
                      <option value={AccountType.LIABILITY}>LIABILITY</option>
                    </select>
                    <ChevronDown size={14} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                  </div>
                ) : (
                  <span className="inline-block text-[10px] font-black px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-gray-600 uppercase tracking-wider">
                    {newAccount.type}
                  </span>
                )}
              </div>
              <div className="md:col-span-2 space-y-2">
                <label className="text-[10px] uppercase font-bold text-gray-400">Description</label>
                {isEditing ? (
                  <input
                    className="w-full text-sm font-medium p-3 bg-white rounded-xl border border-gray-200 text-gray-900 focus:border-blue-500 outline-none shadow-sm"
                    value={newAccount.description || ''}
                    onChange={e => handleUpdateAccountField('description', e.target.value)}
                  />
                ) : (
                  <p className="text-sm text-gray-500 font-medium">{newAccount.description || 'No description'}</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Transactions List */}
        <div>
          <div className="flex items-center justify-between mb-4 px-1">
            <h5 className="text-xs font-black text-gray-900 uppercase tracking-widest flex items-center">
              <Receipt size={14} className="mr-2 text-blue-600" />
              {transactions.length} Transactions Found
            </h5>
            {/* If singular transaction, allow selecting account for it */}
            {!isCreateAccount && isEditing && (
              <div className="relative min-w-[200px]">
                <select
                  className="appearance-none w-full text-[10px] font-bold p-2 bg-white rounded-lg outline-none cursor-pointer pr-6 border border-gray-200 text-gray-900 focus:border-blue-500"
                  value={transactions[0]?.account_id || ''}
                  onChange={e => handleUpdateTransaction(0, 'account_id', e.target.value)}
                >
                  <option value="">Select Account...</option>
                  {accounts.map(acc => (
                    <option key={acc.id} value={acc.id}>{acc.name}</option>
                  ))}
                </select>
                <ChevronDown size={12} className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
              </div>
            )}
            {!isCreateAccount && !isEditing && (
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                {accounts.find(a => a.id === transactions[0]?.account_id)?.name || 'Unassigned Account'}
              </span>
            )}
          </div>

          <div className="overflow-x-auto rounded-[24px] border border-gray-100 shadow-sm">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-gray-50 text-[10px] uppercase tracking-wider font-black text-gray-400 border-b border-gray-100">
                  <th className="p-3 min-w-[120px]">Date</th>
                  <th className="p-3 min-w-[180px]">Merchant</th>
                  <th className="p-3 min-w-[160px]">Category</th>
                  <th className="p-3 min-w-[120px] text-right">Amount</th>
                  <th className="p-3 min-w-[120px]">Type</th>
                  <th className="p-3 min-w-[200px]">Note</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 bg-white">
                {transactions.map((tx: any, idx: number) => (
                  <tr key={idx} className="group hover:bg-blue-50/30 transition-colors">
                    <td className="p-3 align-top">
                      {isEditing ? (
                        <input
                          type="date"
                          className="w-full text-xs font-bold p-2.5 bg-white border border-gray-200 rounded-lg text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none shadow-sm transition-all"
                          value={tx.transaction_date ? tx.transaction_date.split('T')[0] : ''}
                          onChange={e => handleUpdateTransaction(idx, 'transaction_date', e.target.value)}
                        />
                      ) : (
                        <span className="text-xs font-bold text-gray-600 whitespace-nowrap block py-2">
                          {tx.transaction_date ? format(new Date(tx.transaction_date), 'MMM d, yyyy') : '-'}
                        </span>
                      )}
                    </td>
                    <td className="p-3 align-top">
                      {isEditing ? (
                        <input
                          className="w-full text-xs font-bold p-2.5 bg-white border border-gray-200 rounded-lg text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none shadow-sm transition-all placeholder-gray-300"
                          value={tx.merchant || ''}
                          onChange={e => handleUpdateTransaction(idx, 'merchant', e.target.value)}
                          placeholder="Merchant Name"
                        />
                      ) : (
                        <div className="flex flex-col py-2">
                          <span className="text-sm font-bold text-gray-900 truncate max-w-[180px]" title={tx.merchant}>{tx.merchant || 'Unknown'}</span>
                        </div>
                      )}
                    </td>
                    <td className="p-3 align-top">
                      {isEditing ? (
                        <div className="relative">
                          <select
                            className="appearance-none w-full text-xs font-bold p-2.5 bg-white border border-gray-200 rounded-lg text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none shadow-sm cursor-pointer pr-8 transition-all"
                            value={tx.category_id || ''}
                            onChange={e => handleUpdateTransaction(idx, 'category_id', e.target.value)}
                          >
                            <option value="">Uncategorized</option>
                            {categories.map(cat => (
                              <option key={cat.id} value={cat.id}>{cat.name}</option>
                            ))}
                          </select>
                          <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                        </div>
                      ) : (
                        <div className="flex items-center space-x-1.5 py-2">
                          <Tag size={12} className="text-gray-400 shrink-0" />
                          <span className="text-xs font-medium text-gray-600 truncate max-w-[140px]">
                            {categories.find(c => c.id === tx.category_id)?.name || 'Uncategorized'}
                          </span>
                        </div>
                      )}
                    </td>
                    <td className="p-3 align-top text-right">
                      {isEditing ? (
                        <input
                          type="number"
                          step="0.01"
                          className="w-full text-xs font-bold p-2.5 bg-white border border-gray-200 rounded-lg text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none shadow-sm text-right transition-all"
                          value={tx.amount !== undefined ? tx.amount : ''}
                          onChange={e => handleUpdateTransaction(idx, 'amount', e.target.value)}
                        />
                      ) : (
                        <span className={`text-sm font-black block py-2 ${tx.type === 'INCOME' ? 'text-emerald-600' : 'text-gray-900'}`}>
                          {tx.type === 'INCOME' ? '+' : ''}${Math.abs(tx.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </span>
                      )}
                    </td>
                    <td className="p-3 align-top">
                      {isEditing ? (
                        <div className="relative">
                          <select
                            className="appearance-none w-full text-[10px] font-black p-2.5 bg-white border border-gray-200 rounded-lg text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none shadow-sm cursor-pointer uppercase pr-6 transition-all"
                            value={tx.type}
                            onChange={e => handleUpdateTransaction(idx, 'type', e.target.value)}
                          >
                            <option value={TransactionType.EXPENSE}>EXPENSE</option>
                            <option value={TransactionType.INCOME}>INCOME</option>
                            <option value={TransactionType.TRANSFER}>TRANSFER</option>
                          </select>
                          <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
                        </div>
                      ) : (
                        <span className={`text-[10px] font-black px-2 py-1 rounded-md uppercase tracking-wide inline-block mt-1.5 ${tx.type === TransactionType.INCOME ? 'bg-emerald-50 text-emerald-600' :
                          tx.type === TransactionType.EXPENSE ? 'bg-rose-50 text-rose-600' : 'bg-blue-50 text-blue-600'
                          }`}>
                          {tx.type}
                        </span>
                      )}
                    </td>
                    <td className="p-3 align-top">
                      {isEditing ? (
                        <input
                          className="w-full text-xs p-2.5 bg-white border border-gray-200 rounded-lg text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none shadow-sm transition-all placeholder-gray-300"
                          value={tx.note || tx.description || ''}
                          onChange={e => handleUpdateTransaction(idx, 'note', e.target.value)}
                          placeholder="Notes..."
                        />
                      ) : (
                        <p className="text-xs text-gray-400 italic truncate max-w-[200px] py-2" title={tx.note || tx.description}>
                          {tx.note || tx.description || '-'}
                        </p>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Actions */}
        <div className="pt-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <p className="text-[10px] text-gray-400 font-bold max-w-sm leading-relaxed uppercase tracking-tight">
            Verify {isCreateAccount ? 'account details and transaction history' : 'transaction details'} before merging into your ledger.
          </p>
          <div className="flex items-center space-x-3">
            <button
              onClick={() => onReject(proposal.id)}
              className="flex-1 sm:flex-none px-6 py-3 text-sm font-black text-gray-500 hover:text-rose-600 hover:bg-rose-50 rounded-2xl transition-all"
            >
              Discard
            </button>
            <button
              onClick={handleConfirmAction}
              className="flex-1 sm:flex-none px-10 py-3 text-sm font-black text-white bg-blue-600 hover:bg-blue-700 rounded-2xl shadow-xl shadow-blue-100 transition-all transform active:scale-95 flex items-center justify-center"
            >
              <Check size={18} className="mr-2" />
              {isCreateAccount ? 'Create Account & Import' : 'Approve Transaction'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

const Proposals: React.FC = () => {
  const [proposals, setProposals] = useState<ProposedChange[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isProcessing = documents.some(doc =>
    doc.status === DocumentStatus.PARSING || doc.status === DocumentStatus.UPLOADED
  );

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [props, docs, accs, cats] = await Promise.all([
        apiService.getProposals(),
        apiService.getDocuments(),
        apiService.getAccounts(),
        apiService.getCategories()
      ]);
      setProposals(props.filter(p => p.status === ProposalStatus.PENDING));
      setDocuments(docs);
      setAccounts(accs);
      setCategories(cats);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Auto-refresh when documents are processing
  useEffect(() => {
    if (isProcessing) {
      const interval = setInterval(() => {
        fetchData();
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [isProcessing, fetchData]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    setUploading(true);
    try {
      await apiService.uploadDocument(e.target.files[0]);
      // No need for manual setTimeout here as the useEffect above handles polling
      fetchData();
    } catch (err) {
      alert("Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleConfirm = async (id: string, data: any) => {
    try {
      await apiService.confirmProposal(id, ProposalStatus.APPROVED, data);
      setProposals(prev => prev.filter(p => p.id !== id));
    } catch (err: any) {
      alert(err.message || "Failed to confirm");
    }
  };

  const handleReject = async (id: string) => {
    try {
      await apiService.confirmProposal(id, ProposalStatus.REJECTED);
      setProposals(prev => prev.filter(p => p.id !== id));
    } catch (err: any) {
      alert(err.message || "Failed to reject");
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-6">
        <div>
          <h1 className="text-3xl font-black text-gray-900 tracking-tight">AI Inbox</h1>
          <p className="text-gray-500 font-medium">Review and approve suggestions extracted from your documents.</p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={fetchData}
            className="p-3 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-2xl transition-all"
          >
            <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="flex items-center justify-center space-x-2 bg-gray-900 text-white px-6 py-3 rounded-2xl font-black shadow-xl shadow-gray-200 hover:bg-black transition-all transform active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {uploading ? <Loader2 size={20} className="animate-spin" /> : <FileUp size={20} />}
            <span>{uploading ? 'Analyzing...' : 'Upload Receipt'}</span>
          </button>
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            accept="image/*,application/pdf"
            onChange={handleFileUpload}
          />
        </div>
      </header>

      {/* Stats / Queue Info */}
      <div className="flex gap-4 overflow-x-auto pb-2">
        <div className="bg-blue-600 text-white p-5 rounded-[28px] min-w-[200px] shadow-lg shadow-blue-200">
          <div className="flex items-center justify-between mb-4">
            <Inbox size={24} />
            <span className="text-xs font-bold bg-white/20 px-2 py-1 rounded-lg">PENDING</span>
          </div>
          <p className="text-3xl font-black">{proposals.length}</p>
          <p className="text-xs text-blue-100 font-bold uppercase tracking-wider mt-1">Actions Required</p>
        </div>

        <div className="bg-white text-gray-900 p-5 rounded-[28px] border border-gray-100 min-w-[200px] shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <FileText size={24} className="text-gray-400" />
            <span className="text-xs font-bold bg-gray-100 text-gray-500 px-2 py-1 rounded-lg">DOCUMENTS</span>
          </div>
          <p className="text-3xl font-black">{documents.length}</p>
          <p className="text-xs text-gray-400 font-bold uppercase tracking-wider mt-1">Processed Files</p>
        </div>
      </div>

      <div className="space-y-6">
        {loading && proposals.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 space-y-4">
            <Loader2 size={40} className="text-blue-600 animate-spin" />
            <p className="text-gray-400 font-bold uppercase tracking-widest text-xs">Fetching AI suggestions...</p>
          </div>
        ) : proposals.length > 0 ? (
          proposals.map(proposal => (
            <ProposalCard
              key={proposal.id}
              proposal={proposal}
              document={documents.find(d => d.id === proposal.document_id)}
              accounts={accounts}
              categories={categories}
              onConfirm={handleConfirm}
              onReject={handleReject}
            />
          ))
        ) : (
          <div className="py-20 text-center bg-white border-2 border-dashed border-gray-100 rounded-[40px] flex flex-col items-center justify-center">
            {isProcessing ? (
              <>
                <div className="w-20 h-20 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mb-6 animate-pulse">
                  <BrainCircuit size={40} className="animate-bounce" />
                </div>
                <h3 className="text-xl font-black text-gray-900">Processing Documents...</h3>
                <p className="text-gray-400 mt-2 max-w-xs mx-auto">Gemini is currently extracting transitions from your uploads. This usually takes 10-20 seconds.</p>
              </>
            ) : (
              <>
                <div className="w-20 h-20 bg-emerald-50 text-emerald-600 rounded-full flex items-center justify-center mb-6">
                  <Check size={40} />
                </div>
                <h3 className="text-xl font-black text-gray-900">All caught up!</h3>
                <p className="text-gray-400 mt-2 max-w-xs mx-auto">No pending proposals. Upload more receipts to trigger the AI agent.</p>
                <button onClick={() => fileInputRef.current?.click()} className="mt-8 px-8 py-3 bg-gray-900 text-white rounded-2xl font-bold shadow-lg">Upload File</button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Proposals;
