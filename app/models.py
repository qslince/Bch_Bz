from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False) #create hash func

class TaxiOrder(Base):
    __tablename__ = "taxi_orders"
    id = Column(Integer, primary_key=True, index=True)
    start_location = Column(String)
    end_location = Column(String)
    user_id = Column(Integer)
    status = Column(String)  # "pending", "completed", etc.

class KmzFile(Base):
    __tablename__ = "kmz_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)
    upload_time = Column(DateTime, default=func.now())