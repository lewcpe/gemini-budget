import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, ForeignKey, DateTime, Text, JSON, Float, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from .database import Base

def gen_uuid():
    return str(uuid.uuid4())

# Linker table for Transaction <-> Document
transaction_document = Table(
    "transaction_document",
    Base.metadata,
    Column("transaction_id", String, ForeignKey("transaction.id"), primary_key=True),
    Column("document_id", String, ForeignKey("document.id"), primary_key=True),
    Column("attached_at", DateTime, default=lambda: datetime.now(timezone.utc)),
)

class User(Base):
    __tablename__ = "user"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    accounts: Mapped[List["Account"]] = relationship(back_populates="user")
    categories: Mapped[List["Category"]] = relationship(back_populates="user")
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="user")
    documents: Mapped[List["Document"]] = relationship(back_populates="user")
    proposals: Mapped[List["ProposedChange"]] = relationship(back_populates="user")

class Account(Base):
    __tablename__ = "account"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user.id"))
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)  # ASSET, LIABILITY
    sub_type: Mapped[Optional[str]] = mapped_column(String)  # CASH, CREDIT_CARD, etc.
    current_balance: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String, default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user: Mapped["User"] = relationship(back_populates="accounts")
    transactions: Mapped[List["Transaction"]] = relationship(
        back_populates="account", 
        foreign_keys="[Transaction.account_id]"
    )

class Category(Base):
    __tablename__ = "category"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user.id"))
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)  # INCOME, EXPENSE
    parent_category_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("category.id"))
    
    user: Mapped["User"] = relationship(back_populates="categories")
    children: Mapped[List["Category"]] = relationship("Category", back_populates="parent")
    parent: Mapped[Optional["Category"]] = relationship("Category", back_populates="children", remote_side=[id])
    transactions: Mapped[List["Transaction"]] = relationship(back_populates="category")

class Transaction(Base):
    __tablename__ = "transaction"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user.id"))
    account_id: Mapped[str] = mapped_column(String, ForeignKey("account.id"))
    target_account_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("account.id"))
    category_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("category.id"))
    
    amount: Mapped[float] = mapped_column(Float)
    type: Mapped[str] = mapped_column(String)  # INCOME, EXPENSE, TRANSFER
    transaction_date: Mapped[datetime] = mapped_column(DateTime)
    note: Mapped[Optional[str]] = mapped_column(Text)
    merchant: Mapped[Optional[str]] = mapped_column(String)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    user: Mapped["User"] = relationship(back_populates="transactions")
    account: Mapped["Account"] = relationship(foreign_keys=[account_id], back_populates="transactions")
    target_account: Mapped[Optional["Account"]] = relationship(foreign_keys=[target_account_id])
    category: Mapped[Optional["Category"]] = relationship(back_populates="transactions")
    
    documents: Mapped[List["Document"]] = relationship(
        secondary=transaction_document, back_populates="transactions"
    )

class Document(Base):
    __tablename__ = "document"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user.id"))
    original_filename: Mapped[str] = mapped_column(String)
    file_path: Mapped[str] = mapped_column(String)
    mime_type: Mapped[str] = mapped_column(String)
    user_note: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="UPLOADED") # UPLOADED, PARSING, PROCESSED, ERROR
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user: Mapped["User"] = relationship(back_populates="documents")
    proposals: Mapped[List["ProposedChange"]] = relationship(back_populates="document")
    transactions: Mapped[List["Transaction"]] = relationship(
        secondary=transaction_document, back_populates="documents"
    )

class ProposedChange(Base):
    __tablename__ = "proposed_change"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("user.id"))
    document_id: Mapped[str] = mapped_column(String, ForeignKey("document.id"))
    target_transaction_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("transaction.id"))
    
    change_type: Mapped[str] = mapped_column(String)  # CREATE_NEW, UPDATE_EXISTING
    status: Mapped[str] = mapped_column(String, default="PENDING")  # PENDING, APPROVED, REJECTED
    
    proposed_data: Mapped[dict] = mapped_column(SQLiteJSON)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    user: Mapped["User"] = relationship(back_populates="proposals")
    document: Mapped["Document"] = relationship(back_populates="proposals")
    target_transaction: Mapped[Optional["Transaction"]] = relationship()
