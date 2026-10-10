from enum import Enum

from pydantic import BaseModel, Field


class VolumeType(str, Enum):
    """Tipos de volumen soportados por Unity Catalog."""

    MANAGED = "MANAGED"
    EXTERNAL = "EXTERNAL"


class VolumeCreate(BaseModel):
    """Datos necesarios para crear un volumen."""

    catalog_name: str = Field(..., min_length=1)
    schema_name: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)

    volume_type: VolumeType = VolumeType.MANAGED

    storage_location: str | None = None
    comment: str | None = None
    owner: str | None = None

class VolumeInfo(BaseModel):
    """Información de un volumen de Unity Catalog."""

    name: str
    catalog_name: str
    schema_name: str
    full_name: str | None = None

    volume_type: str | None = None
    storage_location: str | None = None

    owner: str | None = None
    comment: str | None = None

    volume_id: str | None = None
    metastore_id: str | None = None

    created_at: int | None = None
    created_by: str | None = None

    updated_at: int | None = None
    updated_by: str | None = None    