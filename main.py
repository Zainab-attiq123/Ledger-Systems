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
    StoreCreate, StoreResponse, ProductCreate, ProductResponse, ProductUpdate,
    CustomerCreate, CustomerResponse, CustomerUpdate,
    SaleCreate, SaleResponse, SaleItemCreate,
    StoreBalanceResponse, CustomerBalanceResponse
)

DATABASE_URL = "sqlite:///./grocery_store.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Grocery Store Management System",
    description="Admin, Salesman, Customer ke saath transactions",
    version="1.0.0"
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid token")
    
    try:
        token = auth_header.split(" ")[1]
    except IndexError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format")
    
    payload = verify_token(token)
    
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    return user

def check_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only!")
    return user

def check_salesman_or_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in [UserRole.SALESMAN, UserRole.ADMIN]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Salesman/Admin only!")
    return user

@app.get("/", tags=["Root"])
def read_root():
    return {
        "message": "Welcome to Grocery Store Management System",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.post("/stores/create", response_model=dict, tags=["Store Setup"])
def create_store(store_data: StoreCreate, db: Session = Depends(get_db)):
    existing_admin = db.query(User).filter(
        User.email == store_data.admin_email,
        User.role == UserRole.ADMIN
    ).first()
    
    if existing_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admin with this email already exists")
    
    try:
        admin_user = User(
            name="Admin",
            email=store_data.admin_email,
            password_hash=hash_password(store_data.admin_password),
            role=UserRole.ADMIN
        )
        db.add(admin_user)
        db.flush()
        
        store = Store(
            name=store_data.name,
            admin_id=admin_user.id
        )
        db.add(store)
        admin_user.store_id = store.id
        
        db.commit()
        
        return {
            "message": "Store created successfully",
            "store_id": store.id,
            "admin_email": store_data.admin_email,
            "store_name": store.name
        }
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

@app.post("/login", response_model=LoginResponse, tags=["Authentication"])
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    
    access_token = create_access_token(
        data={"sub": user.id, "role": user.role.value},
        expires_delta=timedelta(hours=24)
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role
    )

@app.post("/users", response_model=UserResponse, tags=["Users"])
def create_user(
    user_data: UserCreate,
    current_user: User = Depends(check_admin),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
    
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

@app.get("/users", response_model=List[UserResponse], tags=["Users"])
def get_all_users(current_user: User = Depends(check_admin), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.store_id == current_user.store_id).all()
    return users

@app.post("/products", response_model=ProductResponse, tags=["Products"])
def create_product(
    product_data: ProductCreate,
    current_user: User = Depends(check_salesman_or_admin),
    db: Session = Depends(get_db)
):
    product = Product(
        name=product_data.name,
        price=product_data.price,
        quantity_in_stock=product_data.quantity_in_stock,
        store_id=current_user.store_id
    )
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    return product

@app.get("/products", response_model=List[ProductResponse], tags=["Products"])
def get_products(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.store_id == current_user.store_id).all()
    return products

@app.get("/products/search/{product_name}", response_model=ProductResponse, tags=["Products"])
def search_product(
    product_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(
        Product.store_id == current_user.store_id,
        Product.name.ilike(f"%{product_name}%")
    ).first()
    
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    return product

@app.put("/products/{product_id}", response_model=ProductResponse, tags=["Products"])
def update_product(
    product_id: str,
    product_data: ProductUpdate,
    current_user: User = Depends(check_salesman_or_admin),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.store_id == current_user.store_id
    ).first()
    
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    
    if product_data.name:
        product.name = product_data.name
    if product_data.price:
        product.price = product_data.price
    if product_data.quantity_in_stock is not None:
        product.quantity_in_stock = product_data.quantity_in_stock
    
    db.commit()
    db.refresh(product)
    
    return product

@app.post("/customers", response_model=CustomerResponse, tags=["Customers"])
def create_customer(
    customer_data: CustomerCreate,
    current_user: User = Depends(check_salesman_or_admin),
    db: Session = Depends(get_db)
):
    customer = Customer(
        name=customer_data.name,
        phone=customer_data.phone,
        email=customer_data.email,
        store_id=current_user.store_id
    )
    
    db.add(customer)
    db.commit()
    db.refresh(customer)
    
    return customer

@app.get("/customers", response_model=List[CustomerResponse], tags=["Customers"])
def get_customers(current_user: User = Depends(check_salesman_or_admin), db: Session = Depends(get_db)):
    customers = db.query(Customer).filter(Customer.store_id == current_user.store_id).all()
    return customers

@app.get("/customers/search/{customer_name}", response_model=CustomerResponse, tags=["Customers"])
def search_customer(
    customer_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(
        Customer.store_id == current_user.store_id,
        Customer.name.ilike(f"%{customer_name}%")
    ).first()
    
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
    return customer

@app.post("/sales", response_model=dict, tags=["Sales & Transactions"])
def create_sale(
    sale_data: SaleCreate,
    current_user: User = Depends(check_salesman_or_admin),
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(
        Customer.store_id == current_user.store_id,
        Customer.name.ilike(sale_data.customer_name)
    ).first()
    
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
    total_amount = 0
    total_items = 0
    sale_items = []
    
    for item_data in sale_data.items:
        product = db.query(Product).filter(
            Product.store_id == current_user.store_id,
            Product.name.ilike(item_data.product_name)
        ).first()
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product '{item_data.product_name}' not found"
            )
        
        if product.quantity_in_stock < item_data.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for {product.name}. Available: {product.quantity_in_stock}"
            )
        
        item_total = item_data.quantity * item_data.price_per_unit
        total_amount += item_total
        total_items += item_data.quantity
        
        sale_items.append({
            "product": product,
            "quantity": item_data.quantity,
            "price_per_unit": item_data.price_per_unit,
            "total_price": item_total
        })
    
    sale = Sale(
        store_id=current_user.store_id,
        customer_id=customer.id,
        salesman_id=current_user.id,
        transaction_type=sale_data.transaction_type,
        total_amount=total_amount,
        quantity_items=total_items
    )
    
    db.add(sale)
    db.flush()
    
    for item in sale_items:
        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=item["product"].id,
            quantity=item["quantity"],
            price_per_unit=item["price_per_unit"],
            total_price=item["total_price"]
        )
        
        item["product"].quantity_in_stock -= item["quantity"]
        db.add(sale_item)
    
    if sale_data.transaction_type in [TransactionType.LOAN, TransactionType.CREDIT]:
        customer.total_balance += total_amount
    
    store = db.query(Store).filter(Store.id == current_user.store_id).first()
    
    if sale_data.transaction_type == TransactionType.CASH:
        store.total_balance += total_amount
    
    db.commit()
    db.refresh(sale)
    
    return {
        "message": "Sale created successfully",
        "sale_id": sale.id,
        "customer": customer.name,
        "salesman": current_user.name,
        "transaction_type": sale.transaction_type.value,
        "total_amount": total_amount,
        "items_count": total_items
    }

@app.get("/sales", tags=["Sales & Transactions"])
def get_sales(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sales = db.query(Sale).filter(Sale.store_id == current_user.store_id).all()
    
    result = []
    for sale in sales:
        sale_items = []
        for item in sale.items:
            sale_items.append({
                "id": item.id,
                "product_name": item.product.name,
                "quantity": item.quantity,
                "price_per_unit": item.price_per_unit,
                "total_price": item.total_price
            })
        
        result.append({
            "id": sale.id,
            "customer_name": sale.customer.name,
            "salesman_name": sale.salesman.name,
            "transaction_type": sale.transaction_type.value,
            "total_amount": sale.total_amount,
            "quantity_items": sale.quantity_items,
            "created_at": sale.created_at.isoformat(),
            "items": sale_items
        })
    
    return result

@app.get("/store/balance", response_model=StoreBalanceResponse, tags=["Balance"])
def get_store_balance(current_user: User = Depends(check_admin), db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == current_user.store_id).first()
    
    if not store:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    
    sales = db.query(Sale).filter(Sale.store_id == current_user.store_id).all()
    
    total_cash = sum([s.total_amount for s in sales if s.transaction_type == TransactionType.CASH])
    total_loan = sum([s.total_amount for s in sales if s.transaction_type == TransactionType.LOAN])
    total_credit = sum([s.total_amount for s in sales if s.transaction_type == TransactionType.CREDIT])
    
    net_balance = total_cash + total_loan + total_credit
    
    return StoreBalanceResponse(
        store_id=store.id,
        store_name=store.name,
        total_cash=total_cash,
        total_loan=total_loan,
        total_credit=total_credit,
        net_balance=net_balance
    )

@app.get("/customers/{customer_id}/balance", response_model=CustomerBalanceResponse, tags=["Balance"])
def get_customer_balance(
    customer_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    customer = db.query(Customer).filter(
        Customer.id == customer_id,
        Customer.store_id == current_user.store_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    
    transactions = db.query(Sale).filter(Sale.customer_id == customer_id).all()
    
    return CustomerBalanceResponse(
        customer_id=customer.id,
        customer_name=customer.name,
        total_owed=customer.total_balance,
        transaction_count=len(transactions)
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)