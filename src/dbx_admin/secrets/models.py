from pydantic import BaseModel, Field


class SecretCreate(BaseModel):
    """Datos necesarios para crear o actualizar un secreto."""

    scope: str = Field(..., min_length=1)
    key: str = Field(..., min_length=1)
    value: str = Field(..., min_length=1)


class SecretInfo(BaseModel):
    """Información pública de un secreto."""

    key: str
    last_updated_timestamp: int | None = None


class SecretValidation(BaseModel):
    """Resultado de la validación de un secreto."""

    scope: str
    key: str
    exists: bool