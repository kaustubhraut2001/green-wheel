"""
FastAPI application factory.

The application is created via a factory function (not module-level),
which makes it straightforward to create test instances with overridden
dependencies and settings.
"""
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router
from app.core.config import settings
from app.events.lifespan import lifespan
from app.middleware.exception_handler import ExceptionMiddleware, validation_exception_handler
from app.middleware.rate_limit import RateLimitMiddleware


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.DEBUG else None,   # Disable Swagger in prod
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ── Middleware (order matters — outermost runs first) ─────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # IMPORTANT: add_middleware is a stack — last added = outermost = runs first.
    # Correct order: ExceptionMiddleware (outermost) → RateLimitMiddleware → route
    # ExceptionMiddleware must wrap everything so it catches errors from all layers.
    app.add_middleware(ExceptionMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # ── Exception Handlers ────────────────────────────────────
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # ── Routers ───────────────────────────────────────────────
    app.include_router(api_router)

    # ── Static Files (profile images) ─────────────────────────
    import os
    os.makedirs(settings.UPLOAD_DIR + "/profile_images", exist_ok=True)
    app.mount("/static", StaticFiles(directory=settings.UPLOAD_DIR), name="static")

    return app


app = create_application()
