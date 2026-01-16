"""
FluentAI - AI-Powered Language Learning Platform
Main FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging

from config import settings
from database import init_database

# Import routers
from routers import auth, assessment, lessons, speaking, vocabulary, review, progress, user_settings, planner, admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info("Applying Dashboard XP Fix - Server Reloaded")
    logger.info("Achievement Service Integrated - Server Reloaded")
    init_database()
    yield
    # Shutdown
    logger.info("Shutting down FluentAI")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered Adaptive Language Learning Platform",
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(assessment.router, prefix="/api/assessment", tags=["Assessment"])
app.include_router(lessons.router, prefix="/api/lessons", tags=["Lessons"])
app.include_router(speaking.router, prefix="/api/speaking", tags=["Speaking"])
app.include_router(vocabulary.router, prefix="/api/vocabulary", tags=["Vocabulary"])
app.include_router(review.router, prefix="/api/review", tags=["Review"])
app.include_router(progress.router, prefix="/api/progress", tags=["Progress"])
app.include_router(user_settings.router, prefix="/api/settings", tags=["Settings"])
app.include_router(planner.router, prefix="/api/planner", tags=["Planner"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": settings.APP_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
