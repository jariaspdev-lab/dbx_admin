from pydantic.v1 import BaseModel
from pydantic.v1 import Field


class WarehousesInfo(BaseModel):

    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    state: str | None = None
    cluster_size: str | None = None
    warehouse_type: str | None = None
    min_num_clusters: int | None = None
    max_num_clusters: int | None = None
    num_clusters: int | None = None
    auto_stop_mins: int | None = None
    enable_serverless_compute: bool | None = None
    creator_name: str | None = None
    jdbc_url: str | None = None
