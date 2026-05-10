"""FastAPI application factory.

Lifespan owns DB setup/teardown; exception handlers map domain errors to
HTTP responses (services and repositories never reference HTTP).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.admin import router as admin_router
from app.api.chat import router as chat_router
from app.api.chat_history import router as chat_history_router
from app.api.conversations import router as conversations_router
from app.api.health import router as health_router
from app.config import db, settings
from app.errors import AgentError, DomainError, EmptyQueryError, IngestError
from app.providers import ProviderError
from app.repositories import passages as passages_repo
from app.retrieval import get_retriever
from app.services import ingest as ingest_service

_FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def _require_access_tokens() -> None:
    missing = [
        name
        for name, value in (
            ("CHAT_ACCESS_TOKEN", settings.chat_access_token),
            ("ADMIN_TOKEN", settings.admin_token),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            f"refusing to start: required access token(s) not set: {', '.join(missing)}. "
            "Set them in .env (local dev) or as Space secrets (Hugging Face)."
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _require_access_tokens()
    db.migrate(settings.sqlite_path)
    engine = db.make_engine(settings.async_database_url)
    factory = db.make_session_factory(engine)
    db.set_session_factory(factory)
    retriever = get_retriever(settings.retrieval_strategy)
    if settings.auto_ingest_on_startup:
        async with factory() as session:
            existing = await passages_repo.all_ids(session)
        # Fresh session for ingest — `all_ids` already auto-began a tx on the
        # previous one, and `ingest_corpus` opens its own `session.begin()`.
        if not existing:
            async with factory() as session:
                await ingest_service.ingest_corpus(session, settings.convictions_dir)
    async with factory() as session:
        await retriever.build(session)
    app.state.retriever = retriever
    try:
        yield
    finally:
        db.set_session_factory(None)
        await engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.exception_handler(IngestError)
async def _ingest_error_handler(request: Request, exc: IngestError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(EmptyQueryError)
async def _empty_query_error_handler(request: Request, exc: EmptyQueryError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(AgentError)
async def _agent_error_handler(request: Request, exc: AgentError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


@app.exception_handler(ProviderError)
async def _provider_error_handler(request: Request, exc: ProviderError) -> JSONResponse:
    # 503 (upstream unusable response) is distinct from 500 (our code
    # crashed) so the frontend can render an actionable message instead
    # of a generic Internal Server Error.
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(DomainError)
async def _domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


app.include_router(health_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(chat_history_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")


# Serve the built React frontend at /. Only mounts if the dist/ exists,
# so local backend-only dev (`uv run uvicorn …` without a frontend build)
# still works. Registered after API routers so /api/* never falls through.
if _FRONTEND_DIST.is_dir():
    _ASSETS_DIR = _FRONTEND_DIST / "assets"
    if _ASSETS_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=_ASSETS_DIR), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def _spa_fallback(full_path: str) -> FileResponse:
        # /api/* is owned by the routers above; FastAPI's /docs and
        # /openapi.json are registered before this catch-all and win on match.
        candidate = _FRONTEND_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        index = _FRONTEND_DIST / "index.html"
        if not index.is_file():
            raise HTTPException(status_code=404, detail="frontend not built")
        return FileResponse(index)
