from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from database import engine, SessionLocal
from models import Base, User
from routers import ai, diagnosis

app = FastAPI(title="RAGstar API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.id == 1).first():
            db.add(User(id=1, email="test@test.com", name="test", role="operator"))
            db.commit()
    finally:
        db.close()


app.include_router(ai.router)
app.include_router(diagnosis.router)


@app.get("/health")
def health():
    return {"status": "ok"}
