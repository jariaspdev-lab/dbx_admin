from pydantic import BaseModel


class AppInfo(BaseModel):
    """Información administrativa de una Databricks App."""

    name: str
    description: str | None = None
    status: str | None = None
    app_status: str | None = None
    creator: str | None = None
    created_at: str | None = None
    updated_at: str | None = None

    sql_warehouse: str | None = None
    url: str | None = None
    service_principal_client_id: str | None = None
    service_principal_id: str | None = None
    service_principal_name: str | None = None