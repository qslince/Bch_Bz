from sqlalchemy import Column, Integer, String, DateTime, func, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

class TaxiOrder(Base):
    __tablename__ = "taxi_orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False) 
    user = relationship("User")
    start_location = Column(String)
    end_location = Column(String)
    time = Column(String) 

class Berth(Base):
    __tablename__ = "berths"
    id = Column(Integer, primary_key=True, index=True)
    docs_id = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    river = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)



class KmzFile(Base):
    __tablename__ = "kmz_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)
    upload_time = Column(DateTime, default=func.now())