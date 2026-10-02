from databricks.sdk import WorkspaceClient

from .models import UserContext


class ContextService:
    """Servicio para inspeccionar el contexto actual de Databricks."""

    def __init__(self, client: WorkspaceClient):
        self.client = client

    def get_user(self, user_id: str | None = None) -> UserContext:
        """Obtener información de la identidad autenticada."""
        if user_id:
            user = self.client.users.get(id=user_id)
        else:
            user = self.client.current_user.me()

        return UserContext(
            id=user.id,
            external_id=user.external_id,
            username=user.user_name,
            display_name=user.display_name,
            active=user.active,
            groups=[
                group.display
                for group in (user.groups or [])
            ],
            roles=[
                role.display
                for role in (user.roles or [])
            ],
            entitlements=[
                entitlement.value
                for entitlement in (user.entitlements or [])
            ],
        )