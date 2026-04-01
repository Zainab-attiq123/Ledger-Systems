from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    SALESMAN = "salesman"
    CUSTOMER = "customer"

class TransactionType(str, Enum):
    CASH = "cash"
    LOAN = "loan"
    CREDIT = "credit"

# ============= AUTHENTICATION =============
class LoginRequest(BaseModel):
    email: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    role: UserRole
    
    class Config:
        from_attributes = True

# ============= USER SCHEMAS =============
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.CUSTOMER
    store_id: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: UserRole
    store_id: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============= STORE SCHEMAS =============
class StoreCreate(BaseModel):
    name: str
    admin_email: str
    admin_password: str

class StoreResponse(BaseModel):
    id: str
    name: str
    total_balance: float
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============= PRODUCT SCHEMAS =============
class ProductCreate(BaseModel):
    name: str
    price: float
    quantity_in_stock: int = 0

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    quantity_in_stock: Optional[int] = None

class ProductResponse(BaseModel):
    id: str
    name: str
    price: float
    quantity_in_stock: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============= CUSTOMER SCHEMAS =============
class CustomerCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class CustomerResponse(BaseModel):
    id: str
    name: str
    phone: Optional[str]
    email: Optional[str]
    total_balance: float
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============= SALE ITEM SCHEMAS =============
class SaleItemCreate(BaseModel):
    product_name: str  # Product name se link kara (ID nahi)
    quantity: int
    price_per_unit: float

class SaleItemResponse(BaseModel):
    id: str
    product_name: str
    quantity: int
    price_per_unit: float
    total_price: float
    
    class Config:
        from_attributes = True

# ============= SALE (TRANSACTION) SCHEMAS =============
class SaleCreate(BaseModel):
    customer_name: str  # Customer name se link kara (ID nahi)
    transaction_type: TransactionType  # Cash/Loan/Credit
    items: List[SaleItemCreate]

class SaleResponse(BaseModel):
    id: str
    customer_name: str
    salesman_name: str
    transaction_type: TransactionType
    total_amount: float
    quantity_items: int
    created_at: datetime
    items: List[SaleItemResponse]
    
    class Config:
        from_attributes = True

# ============= STORE BALANCE SCHEMA =============
class StoreBalanceResponse(BaseModel):
    store_id: str
    store_name: str
    total_cash: float
    total_loan: float
    total_credit: float
    net_balance: float
    
    class Config:
        from_attributes = True

# ============= CUSTOMER BALANCE SCHEMA =============
class CustomerBalanceResponse(BaseModel):
    customer_id: str
    customer_name: str
    total_owed: float
    transaction_count: int
    
    class Config:
        from_attributes = True