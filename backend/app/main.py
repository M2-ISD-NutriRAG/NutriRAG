"""
NutriRAG - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from shared.snowflake.client import SnowflakeClient

from app.routers import recipes, search, transform, analytics, orchestration


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown events"""
    # Startup
    print("🚀 Starting NutriRAG Backend...")
    yield
    # Shutdown
    print("👋 Shutting down NutriRAG Backend...")


app = FastAPI(
    title="NutriRAG API",
    description="Système intelligent de recherche et transformation de recettes nutritionnelles",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
    ],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(recipes.router, prefix="/api/recipes", tags=["Recipes - Équipe 1"])
app.include_router(search.router, prefix="/api/search", tags=["Search - Équipe 2"])
app.include_router(
    transform.router, prefix="/api/transform", tags=["Transform - Équipe 3"]
)
app.include_router(
    analytics.router, prefix="/api/analytics", tags=["Analytics - Équipe 4"]
)
app.include_router(
    orchestration.router, prefix="/api/orchestrate", tags=["Orchestration - Équipe 5"]
)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "NutriRAG API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": f"{'connected' if SnowflakeClient().is_connected() else 'not connected'}",
        "timestamp": "2025-11-18T00:00:00Z",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
