"""FastAPI application factory.

Lifespan owns DB setup/teardown; exception handlers map domain errors to
HTTP responses (services and repositories never reference HTTP).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.agent.verifier import get_verifier
from app.api.admin import router as admin_router
from app.api.health import router as health_router
from app.config import db, settings
from app.errors import AgentError, DomainError, EmptyQueryError, IngestError
from app.retrieval import get_retriever


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    db.migrate(settings.sqlite_path)
    engine = db.make_engine(settings.async_database_url)
    factory = db.make_session_factory(engine)
    db.set_session_factory(factory)
    retriever = get_retriever(settings.retrieval_strategy)
    async with factory() as session:
        await retriever.build(session)
    app.state.retriever = retriever
    app.state.verifier = get_verifier(settings.verifier_strategy)
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


@app.exception_handler(DomainError)
async def _domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


app.include_router(health_router)
app.include_router(admin_router)
