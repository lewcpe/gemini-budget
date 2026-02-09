
import {
  Account, Category, Transaction, Document,
  ProposedChange, WealthReport, AccountType, CategoryType,
  TransactionType, ProposalStatus, Merchant, Pricing
} from './types';

const STORAGE_KEYS = {
  API_URL: 'gemini_budget_api_url',
  USER_EMAIL: 'gemini_budget_user_email'
};

const DEFAULT_API_URL = 'http://localhost:8000';

export const getApiSettings = () => {
  return {
    apiUrl: localStorage.getItem(STORAGE_KEYS.API_URL) || DEFAULT_API_URL,
    userEmail: localStorage.getItem(STORAGE_KEYS.USER_EMAIL) || 'user@example.com'
  };
};

export const setApiSettings = (apiUrl: string, userEmail: string) => {
  localStorage.setItem(STORAGE_KEYS.API_URL, apiUrl);
  localStorage.setItem(STORAGE_KEYS.USER_EMAIL, userEmail);
};

const fetcher = async (path: string, options: RequestInit = {}) => {
  const { apiUrl, userEmail } = getApiSettings();
  const baseUrl = apiUrl.endsWith('/') ? apiUrl.slice(0, -1) : apiUrl;
  const url = `${baseUrl}${path}`;

  const headers = new Headers(options.headers || {});
  headers.set('X-Forwarded-Email', userEmail);

  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const fetchOptions: RequestInit = {
    ...options,
    headers,
    mode: 'cors',
    credentials: 'omit',
  };

  try {
    const response = await fetch(url, fetchOptions);

    if (response.status === 204) return null;

    if (!response.ok) {
      let errorDetail = `Error ${response.status}: ${response.statusText}`;
      try {
        const errorData = await response.json();
        errorDetail = errorData.detail || errorDetail;
      } catch (e) {
      }
      throw new Error(errorDetail);
    }

    const text = await response.text();
    return text ? JSON.parse(text) : null;

  } catch (error: any) {
    console.error(`API Error [${path}]:`, error);
    if (error.message === 'Failed to fetch') {
      throw new Error(`Unable to connect to server at ${baseUrl}. Is the backend running?`);
    }
    throw error;
  }
};

export const apiService = {
  // System
  checkStatus: (): Promise<{ status: string }> => fetcher('/'),

  // Accounts
  getAccounts: (): Promise<Account[]> => fetcher('/accounts/'),
  createAccount: (data: Partial<Account>): Promise<Account> => fetcher('/accounts/', {
    method: 'POST',
    body: JSON.stringify(data)
  }),
  updateAccount: (id: string, data: Partial<Account>): Promise<Account> => fetcher(`/accounts/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data)
  }),
  deleteAccount: (id: string): Promise<void> => fetcher(`/accounts/${id}`, { method: 'DELETE' }),

  // Categories
  getCategories: (): Promise<Category[]> => fetcher('/categories/'),
  createCategory: (data: Partial<Category>): Promise<Category> => fetcher('/categories/', {
    method: 'POST',
    body: JSON.stringify(data)
  }),
  deleteCategory: (id: string): Promise<void> => fetcher(`/categories/${id}`, { method: 'DELETE' }),

  // Merchants
  getMerchants: (params?: { q?: string; skip?: number; limit?: number }): Promise<Merchant[]> => {
    const query = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) query.append(key, value.toString());
      });
    }
    const qs = query.toString();
    return fetcher(`/merchants/?${qs}`);
  },
  createMerchant: (data: Partial<Merchant>): Promise<Merchant> => fetcher('/merchants/', {
    method: 'POST',
    body: JSON.stringify(data)
  }),
  updateMerchant: (id: string, data: Partial<Merchant>): Promise<Merchant> => fetcher(`/merchants/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data)
  }),
  deleteMerchant: (id: string): Promise<void> => fetcher(`/merchants/${id}`, { method: 'DELETE' }),

  // Transactions
  getTransactions: (params?: { q?: string; skip?: number; limit?: number; account_id?: string }): Promise<Transaction[]> => {
    const query = new URLSearchParams();
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) query.append(key, value.toString());
      });
    }
    const qs = query.toString();
    return fetcher(`/transactions/?${qs}`);
  },
  createTransaction: (data: Partial<Transaction>): Promise<Transaction> => fetcher('/transactions/', {
    method: 'POST',
    body: JSON.stringify(data)
  }),
  updateTransaction: (id: string, data: Partial<Transaction>): Promise<Transaction> => fetcher(`/transactions/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data)
  }),
  deleteTransaction: (id: string): Promise<void> => fetcher(`/transactions/${id}`, { method: 'DELETE' }),

  // Documents
  getDocuments: (): Promise<Document[]> => fetcher('/documents/'),
  uploadDocument: (file: File): Promise<Document> => {
    const formData = new FormData();
    formData.append('file', file);
    return fetcher('/documents/upload', {
      method: 'POST',
      body: formData
    });
  },

  // Proposals
  getProposals: (): Promise<ProposedChange[]> => fetcher('/proposals/'),
  confirmProposal: (id: string, status: ProposalStatus, data?: any): Promise<ProposedChange> => {
    const payload: any = { status };
    if (data) payload.edited_data = data;
    return fetcher(`/proposals/${id}/confirm`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },

  // Reports
  getWealthChart: (interval: string = 'month'): Promise<WealthReport> => fetcher(`/wealth/chart?interval=${interval}`),

  // Pricing
  getPricing: (): Promise<Pricing[]> => fetcher('/pricing/'),
  refreshPrice: (assetCode: string): Promise<void> => fetcher(`/pricing/${assetCode}/refresh`, { method: 'POST' }),
};
