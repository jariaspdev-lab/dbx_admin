from databricks.sdk import WorkspaceClient
from databricks.sdk.service import catalog

from dbx_admin.utils.sql_script import run_sql_script
from .models import SchemaCreate, SchemaInfo


class SchemaService:
    """Servicio para administrar schemas de Unity Catalog."""

    def __init__(self, client: WorkspaceClient, warehouse_id: str | None = None):
        self.client = client
        self.warehouse_id = warehouse_id

    def create(self, schema: SchemaCreate) -> SchemaInfo:
        """Crear un schema en un catalog de Unity Catalog."""

        try:
            response = self.client.schemas.create(
                name=schema.name,
                catalog_name=schema.catalog_name,
                comment=schema.comment,
                properties=schema.properties or None,
                storage_root=schema.storage_root,
            )
            return self._to_model(response)

        except Exception as exc:
            raise RuntimeError(
                f"No fue posible crear el schema "
                f"{schema.catalog_name}.{schema.name}: {exc}"
            ) from exc

    def create_from_sql_file(self, url: str, catalog: str | None = None) -> list[str]:
        """Ejecutar las sentencias de un archivo SQL en un SQL Warehouse.

        Retorna las sentencias ejecutadas. Requiere `warehouse_id`.
        """

        return run_sql_script(self.client, self.warehouse_id, url, catalog)

    @staticmethod
    def _to_model(response: catalog.SchemaInfo) -> SchemaInfo:
        """Convertir la respuesta del SDK de Databricks al modelo interno."""

        return SchemaInfo(
            name=response.name,
            catalog_name=response.catalog_name,
            full_name=response.full_name,
            comment=response.comment,
            schema_id=response.schema_id,
            metastore_id=response.metastore_id,
            created_at=response.created_at,
            created_by=response.created_by,
            updated_at=response.updated_at,
            updated_by=response.updated_by,
        )
