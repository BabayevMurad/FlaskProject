from fastapi import FastAPI, HTTPException, Depends
from typing import List
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

DATABASE_URL = 'sqlite:///./fastapi_books.db'
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SQLAlchemy MODELS

order_products = Table(
    "order_products",
    Base.metadata,
    Column("order_id", ForeignKey("orders.id"), primary_key=True),
    Column("product_id", ForeignKey("products.id"), primary_key=True)
)


class Categories(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)

    products = relationship("Product", back_populates="category", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    price = Column(Integer, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)

    category = relationship("Categories", back_populates="products")
    orders = relationship("Orders", secondary=order_products, back_populates="products")


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    email = Column(String(128), nullable=False, unique=True)
    password = Column(String(128), nullable=False)

    orders = relationship("Orders", back_populates="client", cascade="all, delete-orphan")


class Orders(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)

    client = relationship("Client", back_populates="orders")
    products = relationship("Product", secondary=order_products, back_populates="orders")


Base.metadata.create_all(bind=engine)

# Pydantic

class ProductOut(BaseModel):
    id: int
    name: str
    price: int

    class Config:
        from_attributes = True


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class CategoryOut(BaseModel):
    id: int
    name: str
    products: List[ProductOut] = []

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    price: int
    category_id: int


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    email: str
    password: str


class ClientOut(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    client_id: int
    product_ids: List[int]


class OrderOut(BaseModel):
    id: int
    client: ClientOut
    products: List[ProductOut]

    class Config:
        from_attributes = True


# FastApi App

app = FastAPI(title='FastApi Ecommerce')


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


#Caregory

@app.get("/api/categories/", response_model=List[CategoryOut])
def get_categories(db: Session = Depends(get_db)):
    return db.query(Categories).all()

@app.get("/api/categories/{category_id}", response_model=CategoryOut)
def get_category_by_id(category_id: int, db: Session = Depends(get_db)):
    db_category = db.query(Categories).filter(Categories.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return db_category

@app.post("/api/categories/", response_model=CategoryOut, status_code=201)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    db_category = Categories(name=category.name)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category

@app.delete("/api/categories/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    db_category = db.query(Categories).filter_by(id=category_id).first()
    db.delete(db_category)
    db.commit()
    db.refresh(db_category)
    return None


#Product

@app.get("/api/products/", response_model=List[ProductOut])
def get_products(db: Session = Depends(get_db)):
    return db.query(Product).all()


@app.get("/api/products/{product_id}", response_model=ProductOut)
def get_products(product_id: int, db: Session = Depends(get_db)):
    db_product=db.query(Product).filter_by(id=product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


@app.post("/api/products/", response_model=ProductOut, status_code=201)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    category = db.query(Categories).filter(Categories.id == product.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@app.delete("/api/products/{product_id}", response_model=ProductOut)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return product


#Client

@app.get("/api/clients/", response_model=List[ClientOut])
def get_clients(db: Session = Depends(get_db)):
    return db.query(Client).all()


@app.get("/api/clients/{client_id}", response_model=ClientOut)
def get_client_by_id(client_id: int, db: Session = Depends(get_db)):
    db_client = db.query(Client).filter(Client.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    return db_client

@app.get("/api/clients/{client_id}/orders", response_model=List[OrderOut])
def get_client_orders(client_id: int, db: Session = Depends(get_db)):
    db_orders = db.query(Orders).filter(Orders.client_id == client_id).all()
    if not db_orders:
        raise HTTPException(status_code=404, detail="No orders found for this client")
    return db_orders

@app.post("/api/clients/", response_model=ClientOut, status_code=201)
def create_client(client: ClientCreate, db: Session = Depends(get_db)):
    db_client = Client(**client.dict())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client


@app.delete("/api/clients/{client_id}", response_model=ClientOut)
def delete_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.delete(client)
    db.commit()
    return client


#Order

@app.get("/api/orders/", response_model=List[OrderOut])
def get_orders(db: Session = Depends(get_db)):
    return db.query(Orders).all()


@app.get("/api/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Orders).filter(Orders.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.post("/api/orders/", response_model=OrderOut, status_code=201)
def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    db_client = db.query(Client).filter(Client.id == order.client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")

    db_products = db.query(Product).filter(Product.id.in_(order.product_ids)).all()
    if len(db_products) != len(order.product_ids):
        raise HTTPException(status_code=404, detail="One or more products not found")

    db_order = Orders(client=db_client, products=db_products)
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    return db_order

@app.delete("/api/orders/{order_id}", response_model=OrderOut)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Orders).filter(Orders.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
    return order
