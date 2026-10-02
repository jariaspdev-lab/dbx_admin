from pydantic import BaseModel, Field


class UserContext(BaseModel):
    """Información de la identidad actualmente autenticada."""

    id: str | None = None
    username: str | None = None
    external_id: str | None = None
    display_name: str | None = None
    active: bool | None = None

    groups: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    entitlements: list[str] = Field(default_factory=list)