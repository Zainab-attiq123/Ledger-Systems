from fastapi import FastAPI, Depends, HTTPException, status
from starlette.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from datetime import timedelta
from typing import List

from models import Base, User, Store, Product, Customer, Sale, SaleItem, UserRole, TransactionType
from security import hash_password, verify_password, create_access_token, verify_token
from schemas import (
    LoginRequest, LoginResponse, UserCreate, UserResponse,
    StoreCreate, ProductCreate, ProductResponse, ProductUpdate,
    CustomerCreate, CustomerResponse,
    SaleCreate
)

DATABASE_URL = "sqlite:///./grocery_store.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Grocery Store Management System")


# ================= DB =================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ================= AUTH =================
def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = auth_header.split(" ")[1]
    payload = verify_token(token)

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def check_admin(user: User = Depends(get_current_user)):
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin only")
    return user


def check_salesman_or_admin(user: User = Depends(get_current_user)):
    if user.role not in [UserRole.ADMIN, UserRole.SALESMAN]:
        raise HTTPException(status_code=403, detail="Not allowed")
    return user


# ================= ROOT =================
@app.get("/")
def root():
    return {"message": "API Running 🚀"}


# ================= STORE CREATE (FIXED) =================
@app.post("/stores/create")
def create_store(store_data: StoreCreate, db: Session = Depends(get_db)):

    existing = db.query(User).filter(User.email == store_data.admin_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")

    try:
        # 👉 Admin create
        admin_user = User(
            name="Admin",
            email=store_data.admin_email,
            password_hash=hash_password(store_data.admin_password),
            role=UserRole.ADMIN
        )

        db.add(admin_user)
        db.flush()  # ✅ admin_user.id mil gaya

        # 👉 Store create
        store = Store(
            name=store_data.name,
            admin_id=admin_user.id
        )

        db.add(store)
        db.flush()  # ✅ store.id mil gaya

        # 👉 Link admin with store
        admin_user.store_id = store.id

        db.commit()

        return {
            "message": "Store created successfully",
            "store_id": store.id,
            "admin_email": admin_user.email
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ================= LOGIN =================
@app.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(hours=24)
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role
    }


# ================= USER =================
@app.post("/users", response_model=UserResponse)
def create_user(
    user_data: UserCreate,
    current_user: User = Depends(check_admin),
    db: Session = Depends(get_db)
):
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=user_data.role,
        store_id=current_user.store_id
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


# ================= PRODUCT =================
@app.post("/products", response_model=ProductResponse)
def create_product(
    data: ProductCreate,
    user: User = Depends(check_salesman_or_admin),
    db: Session = Depends(get_db)
):
    product = Product(
        name=data.name,
        price=data.price,
        quantity_in_stock=data.quantity_in_stock,
        store_id=user.store_id
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product


# ================= CUSTOMER =================
@app.post("/customers", response_model=CustomerResponse)
def create_customer(
    data: CustomerCreate,
    user: User = Depends(check_salesman_or_admin),
    db: Session = Depends(get_db)
):
    customer = Customer(
        name=data.name,
        phone=data.phone,
        email=data.email,
        store_id=user.store_id
    )

    db.add(customer)
    db.commit()
    db.refresh(customer)

    return customer


# ================= SALES =================
@app.post("/sales")
def create_sale(
    data: SaleCreate,
    user: User = Depends(check_salesman_or_admin),
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(Customer.name == data.customer_name).first()

    if not customer:
        raise HTTPException(404, "Customer not found")

    total = 0

    for item in data.items:
        product = db.query(Product).filter(Product.name == item.product_name).first()

        if not product:
            raise HTTPException(404, f"{item.product_name} not found")

        if product.quantity_in_stock < item.quantity:
            raise HTTPException(400, "Stock not enough")

        total += item.quantity * item.price_per_unit
        product.quantity_in_stock -= item.quantity

    sale = Sale(
        store_id=user.store_id,
        customer_id=customer.id,
        salesman_id=user.id,
        transaction_type=data.transaction_type,
        total_amount=total
    )

    db.add(sale)
    db.commit()

    return {"message": "Sale done", "total": total}