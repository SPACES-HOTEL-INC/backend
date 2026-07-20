from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import ProgrammingError

from .config import settings
from .database import Base, engine
from .routers import auth, bookings, payments, properties, reviews, rooms, users

app = FastAPI(title="Spaces Backend API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(properties.router)
app.include_router(rooms.router)
app.include_router(bookings.router)
app.include_router(payments.router)
app.include_router(reviews.router)


@app.on_event("startup")
async def startup_event():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except ProgrammingError:
        pass


@app.get("/")
async def root():
    return {"message": "Spaces backend is running"}
