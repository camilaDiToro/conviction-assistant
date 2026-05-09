"""Admin endpoints — operations not exposed to end users."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.config.db import get_session
from app.schemas.ingest import IngestResponse
from app.services import ingest as ingest_service

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/ingest", response_model=IngestResponse)
async def trigger_ingest(
    session: AsyncSession = Depends(get_session),
) -> IngestResponse:
    report = await ingest_service.ingest_corpus(session, settings.convictions_dir)
    return IngestResponse(
        documents=report.documents,
        passages=report.passages,
        orphans_deleted=report.orphans_deleted,
        db_path=str(settings.sqlite_path),
    )
