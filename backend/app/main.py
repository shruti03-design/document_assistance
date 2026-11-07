from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (registers tables with Base)
from app.config import settings
from app.db import Base, engine
from app.routers import documents, qa


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables if they don't exist (a migration tool like Alembic can replace this later)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Document Assistant API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(qa.router)


@app.get("/health")
def health():
    return {"status": "ok"}
