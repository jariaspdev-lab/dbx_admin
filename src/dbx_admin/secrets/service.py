from databricks.sdk import WorkspaceClient

from .models import (
    SecretCreate,
    SecretInfo,
    SecretValidation,
)


class SecretService:
    """Servicio para administrar secretos de Databricks."""

    def __init__(self, client: WorkspaceClient):
        self.client = client

    def list(self, scope: str) -> list[SecretInfo]:
        """Listar los secretos existentes en un scope."""

        secrets = self.client.secrets.list_secrets(scope=scope)

        return [
            SecretInfo(
                key=secret.key,
                last_updated_timestamp=secret.last_updated_timestamp,
            )
            for secret in secrets
        ]

    def create(self, secret: SecretCreate) -> None:
        """Crear o actualizar un secreto."""

        self.client.secrets.put_secret(
            scope=secret.scope,
            key=secret.key,
            string_value=secret.value,
        )

    def exists(self, scope: str, key: str) -> bool:
        """Validar si un secreto existe."""

        secrets = self.list(scope)

        return any(secret.key == key for secret in secrets)

    def validate(
        self,
        scope: str,
        key: str,
    ) -> SecretValidation:

        exists = self.exists(
            scope=scope,
            key=key,
        )

        return SecretValidation(
            scope=scope,
            key=key,
            exists=exists,
        )

    def get(self, scope: str, key: str) -> str:
        """Obtener el valor de un secreto."""

        response = self.client.secrets.get_secret(
            scope=scope,
            key=key,
        )

        return response.value