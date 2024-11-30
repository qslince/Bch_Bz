from pydantic import BaseModel
from typing import Optional


class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int

    class Config:
        orm_mode = True


class TaxiOrderBase(BaseModel):
    start_location: str
    end_location: str
    user_id: int

class TaxiOrderCreate(TaxiOrderBase):
    pass

class TaxiOrder(TaxiOrderBase):
    id: int
    status: str  # "pending", "completed", etc.

    class Config:
        orm_mode = True
