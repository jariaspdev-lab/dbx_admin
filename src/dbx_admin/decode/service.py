import base64

from .models import DecodeRequest, DecodeResponse


class DecodeService:
    """Service for decoding values."""

    def decode(self, request: DecodeRequest) -> DecodeResponse:
        """Decode a value using the requested encoding."""

        if request.encoding.lower() == "base64":
            decoded = base64.b64decode(
                request.value
            ).decode("utf-8")

            return DecodeResponse(
                value=decoded,
                encoding="base64",
            )

        raise ValueError(
            f"Unsupported encoding: {request.encoding}"
        )