import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.cache import close_cache
from app.core.config import settings
from app.core.db import Base, engine
from app.core.rate_limit import limiter
from app.ml.artifacts import get_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Idempotent table creation so a fresh environment boots without a manual step."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_db()
    except SQLAlchemyError as exc:
        logger.error("database unavailable at startup: %s", exc)
    store = get_store()
    logger.info(
        "ForecastIQ ready - %d forecast rows, sources=%s", len(store.forecasts), store.sources
    )
    yield
    await close_cache()


app = FastAPI(
    title=settings.project_name,
    version="1.0.0",
    description="Retail intelligence serving layer for TFT probabilistic demand forecasts.",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Too many requests - please retry shortly."},
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Request validation failed", "errors": exc.errors()},
    )


@app.exception_handler(SQLAlchemyError)
async def database_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("database error on %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database temporarily unavailable"},
    )


@app.get("/health", tags=["system"])
async def health() -> dict:
    store = get_store()
    return {
        "status": "ok",
        "environment": settings.environment,
        "data_source": "synthetic" if store.is_synthetic else "artifacts",
        "artifact_sources": store.sources,
        "series_count": int(store.forecasts[["product_id", "store_nbr"]].drop_duplicates().shape[0]),
    }


app.include_router(api_router, prefix=settings.api_prefix)
