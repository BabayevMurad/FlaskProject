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

class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)

class CategoryOut(BaseModel):
    id: int
    name: str
    products: List[Product]

class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    price: int
    category_id: int


class ProductOut(BaseModel):
    id: int
    name: str
    price: int

    class Config:
        from_attributes = True


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


# FASTAPI APP

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()




@app.post("/api/categories/", response_model=CategoryCreate, status_code=201)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    db_category = Categories(name=category.name)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


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



@app.post("/api/clients/", response_model=ClientOut, status_code=201)
def create_client(client: ClientCreate, db: Session = Depends(get_db)):
    db_client = Client(**client.dict())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client


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


@app.get("/api/categories/", response_model=dict, status_code=200)
def get_categories(db: Session = Depends(get_db)):
    db_categories = db.query(Categories).all()
    return db_categories

@app.get("/api/categories/{category_id}", response_model=dict, status_code=200)
def get_categories_by_id(category_id: int, db: Session = Depends(get_db)):
    db_category = db.query(Categories).filter(Categories.id == category_id).first()
    if not db_category:
        raise HTTPException(status_code=404, detail="Category not found")
    return db_category

@app.get("/api/products/", response_model=dict, status_code=200)
def get_products(db: Session = Depends(get_db)):
    db_products = db.query(Product).all()
    return db_products

@app.get("/api/products/{product_id}", response_model=dict, status_code=200)
def get_products_by_id(product_id: int, db: Session = Depends(get_db)):
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product

@app.get("/api/clients/", response_model=dict, status_code=200)
def get_clients(db: Session = Depends(get_db)):
    db_clients = db.query(Client).all()
    return db_clients

@app.get("/api/clients/{client_id}", response_model=dict, status_code=200)
def get_clients_by_id(client_id: int, db: Session = Depends(get_db)):
    db_client = db.query(Client).filter(Client.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")
    return db_client

@app.get('api/clients/{client_id}/orders', response_model=dict, status_code=200)
def get_clients_by_id(client_id: int, db: Session = Depends(get_db)):
    db_orders = db.query(Orders).filter(Orders.client_id == client_id).all()
    if not db_orders:
        raise HTTPException(status_code=404, detail="Client not found")
    return db_orders


@app.get("/api/orders/", response_model=dict, status_code=200)
def get_orders(db: Session = Depends(get_db)):
    db_orders = db.query(Orders).all()
    return db_orders

@app.get("/api/orders/{order_id}", response_model=OrderOut, status_code=200)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Orders).filter(Orders.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.delete("/api/orders/{order_id}", response_model=OrderOut, status_code=204)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Orders).filter(Orders.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
    db.refresh(order)
    return order

@app.delete("/api/products/{product_id}", response_model=ProductOut, status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    db.refresh(product)
    return product

@app.delete("/api/clients/{client_id}", response_model=ClientOut, status_code=204)
def delete_client(client_id: int, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    db.delete(client)
    db.commit()
    db.refresh(client)
    return client

@app.delete("/api/orders/{order_id}", response_model=ProductOut, status_code=204)
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(Orders).filter(Orders.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    db.delete(order)
    db.commit()
    db.refresh(order)
    return order
