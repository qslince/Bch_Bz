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
    time: str



class TaxiOrder(TaxiOrderBase):
    id: int

    class Config:
        orm_mode = True

class Berth(BaseModel):
    docs_id: int
    name: str
    address: str
    river: str
    latitude: str
    longitude: str
