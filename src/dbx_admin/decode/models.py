from pydantic import BaseModel, Field


class DecodeRequest(BaseModel):
    """Data required to decode a value."""

    value: str = Field(..., min_length=1)
    encoding: str = "base64"


class DecodeResponse(BaseModel):
    """Result of decoding a value."""

    value: str
    encoding: str