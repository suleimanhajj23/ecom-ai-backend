from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    plan = Column(String, default="basic")  # basic, pro, premium
    monthly_generates = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Generation(Base):
    __tablename__ = "generations"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, nullable=False)
    voice = Column(String, default="default")
    include = Column(String)  # comma-separated string of channels
    output = Column(JSON)     # JSON field to store generation output
    created_at = Column(DateTime(timezone=True), server_default=func.now())
