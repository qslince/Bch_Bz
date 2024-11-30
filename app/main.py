from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import models, crud, auth, database
from app.database import SessionLocal, engine
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, Request
from sqlalchemy.orm import Session

models.Base.metadata.create_all(bind=engine)


app = FastAPI()

templates = Jinja2Templates(directory="templates")

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
async def register_user(request: Request, db: Session = Depends(get_db), username: str = Form(...), password: str = Form(...), confirm_password: str = Form(...)):
    try:
        if password != confirm_password:
            return templates.TemplateResponse(
                "register.html", {"request": request, "error": "Passwords do not match"}
            )


        user = db.query(models.User).filter(models.User.username == username).first()
        if user:
            return templates.TemplateResponse(
                "register.html", {"request": request, "error": "Username already exists"}
            )


        new_user = models.User(username=username, hashed_password=password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return templates.TemplateResponse("login.html", {"request": request, "success": "Registration successful! Please log in."})
    except Exception as e:
        print(e)



@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login_user(request: Request, db: Session = Depends(get_db), username: str = Form(...), password: str = Form(...)):
    try:
        db_user = db.query(models.User).filter(models.User.username == username).first()
        if not db_user or db_user.hashed_password != password:
            return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid username or password"})
        
  
        return templates.TemplateResponse("index.html", {"request": request, "username": username})
    except Exception as e:
        print(e)



@app.get("/order")
async def order_page(request: Request):
    return templates.TemplateResponse("order.html", {"request": request})


@app.post("/order")
async def create_order(request: Request, start_location: str = Form(...), end_location: str = Form(...), db: Session = Depends(get_db)):
    if not start_location or not end_location:
        raise HTTPException(status_code=400, detail="Both start and end locations are required")
    
    new_order = models.TaxiOrder(start_location=start_location, end_location=end_location, status="pending")
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    return templates.TemplateResponse("order_success.html", {"request": request, "order": new_order})


@app.get("/admin")
async def admin_panel(request: Request, db: Session = Depends(get_db)):
    orders = db.query(models.TaxiOrder).all()
    return templates.TemplateResponse("admin.html", {"request": request, "orders": orders})

@app.post("/admin/upload")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        with open(f"static/{file.filename}", "wb") as f:
            f.write(file.file.read())

        db.add(models.KmzFile(filename=file.filename))
        db.commit()

        return {"message": f"File {file.filename} uploaded successfully!"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="File upload failed")



