from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import engine, Base
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup: Create tables
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"⚠️ Could not create tables: {e}")
    yield
    # Shutdown: cleanup if needed
    print("🛑 Application shutting down")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Intelligent Job Application Automation System",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "debug": settings.debug
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "docs": "/docs",
        "health": "/health"
    }


# Import and include routers
from app.api import companies, jobs, applications, applications_bot, settings

app.include_router(companies.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(applications_bot.router)
app.include_router(settings.router)
