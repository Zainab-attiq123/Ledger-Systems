from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    SALESMAN = "salesman"

class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    admin_id = Column(Integer, ForeignKey("users.id"))  # admin user

    admin = relationship("User", foreign_keys=[admin_id], back_populates="store_admin")
    users = relationship("User", back_populates="store", foreign_keys="User.store_id")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True)
    password_hash = Column(String)
    role = Column(Enum(UserRole))
    store_id = Column(Integer, ForeignKey("stores.id"))

    store = relationship("Store", foreign_keys=[store_id], back_populates="users")
    store_admin = relationship("Store", foreign_keys="[Store.admin_id]", back_populates="admin")