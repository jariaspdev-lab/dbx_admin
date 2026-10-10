from pydantic.v1 import BaseModel
from databricks.sdk.service import catalog
from pydantic.v1 import Field

class TableColumn(BaseModel):
    name: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    nullable: bool = True
    comment: str | None = None


class TableCreate(BaseModel):
    catalog_name: str = Field(..., min_length=1)
    schema_name: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)

    table_type = catalog.TableType.EXTERNAL
    data_source_format = catalog.DataSourceFormat.DELTA
    storage_location: str | None = None

    columns: list[TableColumn] = Field(default_factory=list)
    properties: dict[str, str] = Field(default_factory=dict)

    comment: str | None = None
    full_name: str | None = None

class TableInfo(BaseModel):
    name: str
    catalog_name: str
    schema_name: str
    full_name: str
    table_type: str
    comment: str | None = None
    table_id: str | None = None
    metastore_id: str | None = None
    created_at: int | None = None  # epoch en milisegundos
    created_by: str | None = None
    updated_at: int | None = None  # epoch en milisegundos
    updated_by: str | None = None