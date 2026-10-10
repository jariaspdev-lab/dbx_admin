from databricks.sdk import WorkspaceClient

from .models import AppInfo

class AppService:
    """Servicio para consultar Databricks Apps."""

    def __init__(self, client: WorkspaceClient):
        self.client = client

    def get_app(self, name: str ) -> AppInfo:
        """Obtener información de una App."""
    
        app = self.client.apps.get(name=name)

        print(f"APP:{type(app)}")
        print(app)

        msg_status = app.app_status.message
        msg_sql_warehouse = next(
            (
                resource.sql_warehouse
                for resource in app.resources
                if resource.sql_warehouse is not None
            ),
            None,
        )
        msg_service_principal_id = str(app.service_principal_id)

        return AppInfo(
            name=app.name,
            description=app.description or "",            
            app_status=msg_status,
            creator=app.creator,
            updater=app.updater or "",
            created_at=app.create_time or "",
            updated_at=app.update_time or "",
            url=app.url,
            sql_warehouse=msg_sql_warehouse,
            service_principal_client_id=app.service_principal_client_id,
            service_principal_id=msg_service_principal_id,
            service_principal_name=app.service_principal_name,
        )