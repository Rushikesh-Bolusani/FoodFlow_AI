"""FoodFlow AI backend — FastAPI application entry point.

Run from the repo root:
    venv/Scripts/python.exe -m uvicorn backend.main:app --reload
Then open http://127.0.0.1:8000/docs
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import models
from backend.database import engine
from backend.routers import (
    benchmarks,
    feedback,
    forecast,
    impact,
    menu,
    recommendations,
    waste,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_all only adds missing tables; it never alters existing ones.
    models.Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="FoodFlow AI",
    description=(
        "Food waste intelligence for institutional kitchens — waste records, "
        "diner feedback, impact conversion, forecasting and recommendations."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Enable CORS for feedback form & local dashboard calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(waste.router)
app.include_router(impact.router)
app.include_router(benchmarks.router)
app.include_router(forecast.router)
app.include_router(feedback.router)
app.include_router(menu.router)
app.include_router(recommendations.router)


@app.get("/")
def welcome():
    return {
        "message": "FoodFlow AI is running.",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "FoodFlow AI"}
