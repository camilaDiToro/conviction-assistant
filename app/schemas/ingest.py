from pydantic import BaseModel, ConfigDict


class IngestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    documents: int
    passages: int
    orphans_deleted: int
    db_path: str
