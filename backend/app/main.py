import logging

from alembic import command
from alembic.config import Config
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.api import auth, profile, scans, listings, removals, admin

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(title="Ghosted", version="1.0.0")


@app.on_event("startup")
def run_migrations():
    try:
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Alembic migrations applied successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(scans.router)
app.include_router(listings.router)
app.include_router(removals.router)
app.include_router(admin.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Return error responses in CONTRACTS.md format: {detail, code}."""
    code = "UNKNOWN"
    if hasattr(exc, "headers") and exc.headers and "code" in exc.headers:
        code = exc.headers["code"]
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": code},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": "INTERNAL_ERROR"},
    )


@app.get("/health")
def health():
    return {"status": "ok"}
