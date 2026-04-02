from sqlalchemy import Column, String, Float, DateTime, Enum, ForeignKey, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

Base = declarative_base()

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    SALESMAN = "salesman"
    CUSTOMER = "customer"

class TransactionType(str, enum.Enum):
    CASH = "cash"
    LOAN = "loan"
    CREDIT = "credit"

# ============= USER MODEL =============
class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)  
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.CUSTOMER)
    store_id = Column(String(36), ForeignKey("stores.id"))  
    created_at = Column(DateTime, default=datetime.utcnow)
    
    store = relationship("Store", back_populates="users")
    sales = relationship("Sale", back_populates="salesman")
    
    def __repr__(self):
        return f"<User: {self.name} ({self.role})>"

# ============= STORE MODEL =============
class Store(Base):
    __tablename__ = "stores"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    admin_id = Column(String(36), ForeignKey("users.id"))  
    total_balance = Column(Float, default=0.0) 
    created_at = Column(DateTime, default=datetime.utcnow)
    
    admin = relationship("User", foreign_keys=[admin_id])
    users = relationship("User", back_populates="store", foreign_keys="User.store_id")
    products = relationship("Product", back_populates="store", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="store", cascade="all, delete-orphan")
    sales = relationship("Sale", back_populates="store", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Store: {self.name}>"

# ============= PRODUCT MODEL =============
class Product(Base):
    __tablename__ = "products"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)  
    price = Column(Float, nullable=False)
    quantity_in_stock = Column(Integer, default=0)
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    store = relationship("Store", back_populates="products")
    sale_items = relationship("SaleItem", back_populates="product")
    
    def __repr__(self):
        return f"<Product: {self.name} (Stock: {self.quantity_in_stock})>"

# ============= CUSTOMER MODEL =============
class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, index=True)  
    phone = Column(String(20))
    email = Column(String(255))
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False)
    total_balance = Column(Float, default=0.0)  
    created_at = Column(DateTime, default=datetime.utcnow)
    
    store = relationship("Store", back_populates="customers")
    sales = relationship("Sale", back_populates="customer")
    
    def __repr__(self):
        return f"<Customer: {self.name} (Balance: {self.total_balance})>"

# ============= SALE MODEL (Transaction) =============
class Sale(Base):
    __tablename__ = "sales"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=False)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    salesman_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    
    transaction_type = Column(Enum(TransactionType), nullable=False) 
    total_amount = Column(Float, nullable=False)
    quantity_items = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    store = relationship("Store", back_populates="sales")
    customer = relationship("Customer", back_populates="sales")
    salesman = relationship("User", back_populates="sales")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Sale: {self.total_amount} ({self.transaction_type})>"

# ============= SALE ITEM MODEL =============
class SaleItem(Base):
    __tablename__ = "sale_items"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sale_id = Column(String(36), ForeignKey("sales.id"), nullable=False)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    
    sale = relationship("Sale", back_populates="items")
    product = relationship("Product", back_populates="sale_items")
    
    def __repr__(self):
        return f"<SaleItem: {self.quantity}x {self.price_per_unit}>"