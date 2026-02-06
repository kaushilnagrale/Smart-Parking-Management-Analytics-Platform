"""Smart Parking Management Platform — FastAPI Application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import get_settings
from app.core.database import init_db, close_db
from app.api import api_router, websocket_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    logger.info(f"Starting {settings.APP_NAME} ({settings.APP_ENV})")
    await init_db()

    # Run seeder in development
    if settings.APP_ENV == "development":
        try:
            from app.utils.seed import seed_database
            await seed_database()
        except Exception as e:
            logger.warning(f"Seeder skipped: {e}")

    yield

    logger.info("Shutting down...")
    await close_db()


app = FastAPI(
    title="Smart Parking Management Platform",
    description=(
        "Full-stack intelligent parking management system integrating "
        "computer vision, real-time APIs, and cloud analytics."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router)
app.include_router(websocket_router)


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
