from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

class AccountType(str, Enum):
    ASSET = "ASSET"
    LIABILITY = "LIABILITY"

class CategoryType(str, Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"

class TransactionType(str, Enum):
    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"

class DocumentStatus(str, Enum):
    UPLOADED = "UPLOADED"
    PARSING = "PARSING"
    PROCESSED = "PROCESSED"
    ERROR = "ERROR"

class ProposalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class ProposalChangeType(str, Enum):
    CREATE_NEW = "CREATE_NEW"
    UPDATE_EXISTING = "UPDATE_EXISTING"
    CREATE_ACCOUNT_AND_TRANSACTION = "CREATE_ACCOUNT_AND_TRANSACTION"

# --- User ---
class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Account ---
class AccountBase(BaseModel):
    name: str
    type: AccountType
    sub_type: Optional[str] = None
    currency: str = "USD"
    description: Optional[str] = None

class AccountCreate(AccountBase):
    current_balance: float = 0.0

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[AccountType] = None
    sub_type: Optional[str] = None
    current_balance: Optional[float] = None
    currency: Optional[str] = None
    description: Optional[str] = None

class Account(AccountBase):
    id: str
    user_id: str
    current_balance: float
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Category ---
class CategoryBase(BaseModel):
    name: str
    type: CategoryType
    parent_category_id: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: str
    user_id: str
    model_config = ConfigDict(from_attributes=True)

# --- Transaction ---
class TransactionBase(BaseModel):
    account_id: str
    target_account_id: Optional[str] = None
    category_id: Optional[str] = None
    amount: float
    type: TransactionType
    transaction_date: datetime
    note: Optional[str] = None
    merchant: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    account_id: Optional[str] = None
    target_account_id: Optional[str] = None
    category_id: Optional[str] = None
    amount: Optional[float] = None
    type: Optional[TransactionType] = None
    transaction_date: Optional[datetime] = None
    note: Optional[str] = None
    merchant: Optional[str] = None

class Transaction(TransactionBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Document ---
class DocumentBase(BaseModel):
    original_filename: str
    user_note: Optional[str] = None

class Document(DocumentBase):
    id: str
    user_id: str
    file_path: str
    mime_type: str
    status: DocumentStatus
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# --- Proposed Change ---
class ProposedChangeBase(BaseModel):
    document_id: str
    target_transaction_id: Optional[str] = None
    change_type: ProposalChangeType
    proposed_data: Dict[str, Any]
    confidence_score: Optional[float] = None

class ProposedChange(ProposedChangeBase):
    id: str
    user_id: str
    status: ProposalStatus
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ProposedChangeConfirm(BaseModel):
    status: ProposalStatus # APPROVED or REJECTED
    edited_data: Optional[Dict[str, Any]] = None

# --- Report ---
class ReportDataPoint(BaseModel):
    date: str
    assets: float
    liabilities: float
    net_worth: float

class WealthReport(BaseModel):
    data_points: List[ReportDataPoint]
