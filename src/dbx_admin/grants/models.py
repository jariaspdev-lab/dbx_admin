from pydantic import BaseModel, Field


class Grant(BaseModel):
    principal: str = Field(..., min_length=1)
    privilege: str = Field(..., min_length=1)
    object_type: str | None = None
    object_name: str | None = None


class GrantRequest(BaseModel):
    principal: str = Field(..., min_length=1)
    privilege: str = Field(..., min_length=1)


class GrantResult(BaseModel):
    principal: str
    privilege: str
    object_type: str
    object_name: str