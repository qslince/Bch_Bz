from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import models, crud, auth, database
from app.database import SessionLocal, engine
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.auth import hash_password, verify_password
import pandas as pd
from jose import JWTError, jwt
from tempfile import SpooledTemporaryFile
from datetime import datetime
from starlette.middleware.sessions import SessionMiddleware

models.Base.metadata.create_all(bind=engine)



SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.add_middleware(SessionMiddleware, secret_key="your_secret_key")

def parse_orders(db: Session):
    orders = db.query(models.TaxiOrder).all()

    parsed_orders = []
    for order in orders:
        parsed_order = {
            "id": order.id,
            "start_location": order.start_location,
            "end_location": order.end_location,
            "time": order.time,
            "user_id": order.user_id
        }
        parsed_orders.append(parsed_order)

    return parsed_orders

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.get("/")
async def read_root(request: Request, current_user: models.User = Depends(get_current_user)):
    if current_user is None:
        return templates.TemplateResponse("index.html", {"request": request})
    return templates.TemplateResponse("index.html", {"request": request, "user": current_user.username})

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
async def register_user(request: Request, db: Session = Depends(get_db), username: str = Form(...), password: str = Form(...), confirm_password: str = Form(...)):

    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html", {"request": request, "error": "Passwords do not match"}
        )


    user = db.query(models.User).filter(models.User.username == username).first()
    if user:
        return templates.TemplateResponse(
            "register.html", {"request": request, "error": "Username already exists"}
        )

    hashed_password = hash_password(password)


    new_user = models.User(username=username, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return templates.TemplateResponse("login.html", {"request": request, "success": "Registration successful! Please log in."})



@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_user(request: Request, db: Session = Depends(get_db), username: str = Form(...), password: str = Form(...)):

    
    db_user = db.query(models.User).filter(models.User.username == username).first()
    if not db_user or not verify_password(password, db_user.hashed_password):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})
    request.session["user_id"] = db_user.id
    request.session["username"] = db_user.username

    return templates.TemplateResponse("index.html", {"request": request, "user": username})



@app.get("/search_berths")
async def search_berths(query: str, db: Session = Depends(get_db)):
    results = db.query(models.Berth).filter(models.Berth.name.ilike(f"%{query}%")).all()
    berths = [{"id": berth.id, "name": berth.name, "latitude": berth.latitude, "longitude": berth.longitude} for berth in results]
    return JSONResponse(content=berths)



@app.get("/order")
async def order_page(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    berths = db.query(models.Berth).all()

    if current_user is None:
        return templates.TemplateResponse("login.html", {"request": request, "message": "Для заказа речного такси нужно войти в аккаунт!"})
    
    return templates.TemplateResponse("order.html", {"request": request, "berths": berths})



@app.post("/order")
async def create_order(request: Request, start_location_id: int = Form(...), end_location_id: int = Form(...),  db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    current_datetime = datetime.now()
    if not start_location_id or not end_location_id:
        raise HTTPException(status_code=400, detail="Both start and end locations are required")
    
    start_location = db.query(models.Berth).filter(models.Berth.id == start_location_id).first()
    end_location = db.query(models.Berth).filter(models.Berth.id == end_location_id).first()

    new_order = models.TaxiOrder(user_id = current_user.id, start_location=start_location.docs_id, end_location=end_location.docs_id, time=str(current_datetime))
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    return templates.TemplateResponse("order.html", {"request": request, "order": new_order, "message": f"Заказ успешно создан, ожидайтк."})

@app.get("/api/orders")
async def get_orders(db: Session = Depends(get_db)):
    orders = parse_orders(db)
    return {"orders": orders}


@app.get("/admin")
async def admin_panel(request: Request, db: Session = Depends(get_db)):
    orders = db.query(models.TaxiOrder).all()
    return templates.TemplateResponse("admin.html", {"request": request, "orders": orders})

@app.post("/admin/upload")
async def upload_file(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    print(f"!!!!!!!!!!!!!!\n{file.filename}\n!!!!!!!!!!!!!!!!!!!!!!!")
    if file.filename == "berths.xlsx":

        with open(f"uploaded_files/{file.filename}", "wb") as f:
            f.write(file.file.read())
        df = pd.read_excel('uploaded_files/berths.xlsx')


        for _, row in df.iterrows():
            print(row)
            berth = models.Berth(docs_id = row["Docs.id"], name = row["Docs.name"], address = row["Docs.address"], river = row["Docs.river"], latitude = row["Docs.latitude"], longitude = row["Docs.longitude"])
            db.add(berth)
            db.commit()
            db.refresh(berth)
        return templates.TemplateResponse("admin.html", {"request": request, "message": f"File {file.filename} uploaded successfully!"})
    
    try:
        with open(f"uploaded_files/{file.filename}", "wb") as f:
            f.write(file.file.read())

        print("good")
        return templates.TemplateResponse("admin.html", {"request": request, "message": f"File {file.filename} uploaded successfully!"})
    except Exception  as ex:
        print(ex)
        return templates.TemplateResponse("admin.html", {"request": request, "error": f"File {file.filename} uploaded failed!"})



@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)