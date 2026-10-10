from pydantic.v1 import BaseModel
from databricks.sdk.service import catalog
from pydantic.v1 import Field

class WarehouseInfo(BaseModel):

    name: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1)
    capacity: int = Field(..., ge=0)
    nullable: bool = True
    comment: str | None = None
    