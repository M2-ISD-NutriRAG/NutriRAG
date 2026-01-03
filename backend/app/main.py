"""
NutriRAG - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from shared.snowflake.client import SnowflakeClient

from app.routers import recipes, search, transform, analytics, orchestration

from app.routers import r_test
from app.routers import r_auth

# Global SnowflakeClient instance to avoid reconnection overhead
_snowflake_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown events"""
    global _snowflake_client
    # Startup
    print("🚀 Starting NutriRAG Backend...")
    try:
        _snowflake_client = SnowflakeClient()
        print("✅ Connected to Snowflake")
    except Exception as e:
        print(f"⚠️  Failed to connect to Snowflake: {e}")
        _snowflake_client = None
    yield
    # Shutdown
    print("👋 Shutting down NutriRAG Backend...")
    if _snowflake_client:
        _snowflake_client.close()


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
app.include_router(r_test.router, prefix="/api/general", tags=["General"])
app.include_router(r_auth.router, prefix="/auth", tags=["General"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "healthy", "service": "NutriRAG API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Detailed health check"""
    db_status = "not connected"
    if _snowflake_client:
        connection_info = _snowflake_client.is_connected()
        db_status = "connected" if connection_info.get("ok") else "not connected"

    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": "2025-11-18T00:00:00Z",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
