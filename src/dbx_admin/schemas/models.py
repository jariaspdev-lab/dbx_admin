from pydantic.v1 import BaseModel, Field


class SchemaCreate(BaseModel):
    catalog_name: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    comment: str | None = None
    properties: dict[str, str] = Field(default_factory=dict)
    storage_root: str | None = None


class SchemaInfo(BaseModel):
    name: str
    catalog_name: str
    full_name: str
    comment: str | None = None
    schema_id: str | None = None
    metastore_id: str | None = None
    created_at: int | None = None  # epoch en milisegundos
    created_by: str | None = None
    updated_at: int | None = None  # epoch en milisegundos
    updated_by: str | None = None
