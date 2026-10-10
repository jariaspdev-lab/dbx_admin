import re
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from dbx_admin.volumes.models import VolumeType


class ManifestModel(BaseModel):
    """Base de los modelos del manifiesto: rechaza claves desconocidas."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ProjectSpec(ManifestModel):
    name: str = Field(..., min_length=1)
    owner: str | None = None
    description: str | None = None


class TargetSpec(ManifestModel):
    catalog: str = Field(..., min_length=1)
    # Schema por defecto de volúmenes, tablas y grants; opcional.
    schema_name: str | None = Field(default=None, alias="schema")


class SchemaSpec(ManifestModel):
    name: str = Field(..., min_length=1)
    comment: str | None = None


class VolumeSpec(ManifestModel):
    name: str = Field(..., min_length=1)
    comment: str | None = None
    type: VolumeType = VolumeType.MANAGED
    storage_location: str | None = None
    # Si se omite, se usa target.schema.
    schema_name: str | None = Field(default=None, alias="schema")


class ColumnSpec(ManifestModel):
    name: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    nullable: bool = True
    comment: str | None = None


class TableSpec(ManifestModel):
    name: str = Field(..., min_length=1)
    comment: str | None = None
    columns: list[ColumnSpec] = Field(..., min_length=1)
    properties: dict[str, str] = Field(default_factory=dict)
    # Si se omite, se usa target.schema.
    schema_name: str | None = Field(default=None, alias="schema")


class GrantObjectType(str, Enum):
    SCHEMA = "SCHEMA"
    TABLE = "TABLE"
    VOLUME = "VOLUME"


class GrantSpec(ManifestModel):
    object_type: GrantObjectType
    # Nombre del objeto. Para TABLE/VOLUME se ubica por nombre en el manifiesto.
    object: str = Field(..., min_length=1)
    principal: str = Field(..., min_length=1)
    privileges: list[str] = Field(..., min_length=1)
    # Si se omite, se deduce de la tabla/volumen declarado o de target.schema.
    schema_name: str | None = Field(default=None, alias="schema")

    @field_validator("privileges")
    @classmethod
    def _validate_privileges(cls, value: list[str]) -> list[str]:
        normalized = [p.strip().upper().replace(" ", "_") for p in value]
        for privilege in normalized:
            if not re.fullmatch(r"[A-Z_]+", privilege):
                raise ValueError(f"Privilegio no válido: {privilege!r}")
        return normalized


class InfrastructureSpec(ManifestModel):
    schemas: list[SchemaSpec] = Field(default_factory=list)
    volumes: list[VolumeSpec] = Field(default_factory=list)
    tables: list[TableSpec] = Field(default_factory=list)
    grants: list[GrantSpec] = Field(default_factory=list)


class Manifest(ManifestModel):
    version: str
    project: ProjectSpec
    target: TargetSpec
    infrastructure: InfrastructureSpec = Field(default_factory=InfrastructureSpec)

    @model_validator(mode="after")
    def _validate_schemas(self) -> "Manifest":
        if self.target.schema_name:
            return self

        missing = [
            f"{kind} '{spec.name}'"
            for kind, specs in (
                ("volumen", self.infrastructure.volumes),
                ("tabla", self.infrastructure.tables),
            )
            for spec in specs
            if not spec.schema_name
        ]
        if missing:
            raise ValueError(
                "Sin target.schema, cada recurso debe indicar 'schema': "
                + ", ".join(missing)
            )
        return self


class ResourceKind(str, Enum):
    SCHEMA = "schema"
    VOLUME = "volume"
    TABLE = "table"
    GRANT = "grant"


class ResourceStatus(str, Enum):
    CREATED = "created"
    EXISTS = "exists"
    PLANNED = "planned"
    FAILED = "failed"


class ResourceResult(BaseModel):
    """Resultado de aplicar un recurso del manifiesto."""

    kind: ResourceKind
    full_name: str
    status: ResourceStatus
    detail: str | None = None


class ApplyResult(BaseModel):
    """Resultado agregado de aplicar un manifiesto."""

    resources: list[ResourceResult] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(r.status == ResourceStatus.FAILED for r in self.resources)
