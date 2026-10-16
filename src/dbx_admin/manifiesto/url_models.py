from pydantic import Field

from .models import (
    ApplyResult,
    GrantSpec,
    ManifestModel,
    ProjectSpec,
    ResourceKind,
    ResourceResult,
    ResourceStatus,
    TargetSpec,
)


class UrlSpec(ManifestModel):
    """Recurso definido por un script SQL (ruta local, /Volumes o URL http)."""

    url: str = Field(..., min_length=1)


class UrlInfrastructureSpec(ManifestModel):
    schemas: list[UrlSpec] = Field(default_factory=list)
    volumes: list[UrlSpec] = Field(default_factory=list)
    tables: list[UrlSpec] = Field(default_factory=list)
    grants: list[GrantSpec] = Field(default_factory=list)


class UrlManifest(ManifestModel):
    version: str
    project: ProjectSpec
    target: TargetSpec
    infrastructure: UrlInfrastructureSpec = Field(
        default_factory=UrlInfrastructureSpec
    )


__all__ = [
    "ApplyResult",
    "ResourceKind",
    "ResourceResult",
    "ResourceStatus",
    "UrlInfrastructureSpec",
    "UrlManifest",
    "UrlSpec",
]
