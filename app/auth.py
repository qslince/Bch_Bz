from app import crud, models, schemas
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends, status


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def register_user(db: Session, username: str, password: str):
    hashed_password = pwd_context.hash(password)
    return crud.create_user(db, username=username, hashed_password=hashed_password)

def login_user(db: Session, username: str, password: str):
    db_user = db.query(models.User).filter(models.User.username == username).first()
    if db_user and pwd_context.verify(password, db_user.hashed_password):
        return {"message": "Login successful"}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
