"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1 import router as api_v1_router
from app.auth.oauth import oauth_router
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    yield
    # Shutdown


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        description="""
DongneFit Backend API

## Features
- **User Management**: OAuth authentication (Google, Kakao)
- **Neighborhoods**: Location-based neighborhood information
- **Reports**: Real estate content and reports
- **Discussions**: Community forum
- **Notifications**: User notification system

## Authentication
Use `/api/auth/google` or `/api/auth/kakao` to login via OAuth.
Session-based authentication is used for subsequent requests.
        """,
        version="1.0.0",
        debug=settings.debug,
        lifespan=lifespan,
        openapi_tags=[
            {"name": "auth", "description": "Authentication endpoints"},
            {"name": "users", "description": "User management"},
            {"name": "neighborhoods", "description": "Neighborhood information"},
            {"name": "reports", "description": "Real estate reports and content"},
            {"name": "discussions", "description": "Community discussions"},
            {"name": "products", "description": "Product management"},
            {"name": "orders", "description": "Order management"},
            {"name": "coupons", "description": "Coupon management"},
            {"name": "notifications", "description": "User notifications"},
            {"name": "talk", "description": "Tool-calling agent API"},
        ],
    )

    # Session middleware (must be added before CORS)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        max_age=settings.session_expire_days * 24 * 60 * 60,
        same_site="lax",
        https_only=not settings.debug,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.frontend_client_app_url,
            settings.frontend_admin_app_url,
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(oauth_router, prefix="/api")
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/", tags=["health"])
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
    }
