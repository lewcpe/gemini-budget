
export enum AccountType {
  ASSET = 'ASSET',
  LIABILITY = 'LIABILITY'
}

export enum CategoryType {
  INCOME = 'INCOME',
  EXPENSE = 'EXPENSE'
}

export enum TransactionType {
  INCOME = 'INCOME',
  EXPENSE = 'EXPENSE',
  TRANSFER = 'TRANSFER'
}

export enum DocumentStatus {
  UPLOADED = 'UPLOADED',
  PARSING = 'PARSING',
  PROCESSED = 'PROCESSED',
  ERROR = 'ERROR'
}

export enum ProposalChangeType {
  CREATE_NEW = 'CREATE_NEW',
  UPDATE_EXISTING = 'UPDATE_EXISTING',
  CREATE_ACCOUNT = 'CREATE_ACCOUNT'
}

export enum ProposalStatus {
  PENDING = 'PENDING',
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED'
}

export interface Account {
  id: string;
  name: string;
  type: AccountType;
  sub_type: string | null;
  currency: string;
  description: string | null;
  user_id: string;
  current_balance: number;
  created_at: string;
}

export interface Category {
  id: string;
  name: string;
  type: CategoryType;
  parent_category_id: string | null;
  user_id: string;
}

export interface Merchant {
  id: string;
  name: string;
  default_category_id: string | null;
  user_id: string;
}

export interface Transaction {
  id: string;
  account_id: string;
  target_account_id: string | null;
  category_id: string | null;
  amount: number;
  type: TransactionType;
  transaction_date: string;
  note: string | null;
  merchant: string | null;
  user_id: string;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  original_filename: string;
  user_note: string | null;
  file_path: string;
  mime_type: string;
  status: DocumentStatus;
  created_at: string;
}

export interface ProposedChange {
  id: string;
  document_id: string;
  target_transaction_id: string | null;
  change_type: ProposalChangeType;
  proposed_data: any;
  confidence_score: number | null;
  status: ProposalStatus;
  created_at: string;
}

export interface ReportDataPoint {
  date: string;
  assets: number;
  liabilities: number;
  net_worth: number;
}

export interface WealthReport {
  data_points: ReportDataPoint[];
}

export interface Pricing {
  id: string;
  asset_code: string;
  price_in_usd: number;
  last_updated: string;
}
