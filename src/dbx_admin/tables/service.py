import json
import re

from databricks.sdk import WorkspaceClient
from databricks.sdk.service import catalog
from databricks.sdk.service.sql import StatementState
from dbx_admin.utils.sql_script import run_sql_script
from .models import TableColumn, TableCreate, TableInfo

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")

# Equivalencias de tipos SQL -> (ColumnTypeName del SDK, nombre de tipo en JSON de Spark)
_TYPE_MAP = {
    "BIGINT": ("LONG", "long"),
    "LONG": ("LONG", "long"),
    "INT": ("INT", "integer"),
    "INTEGER": ("INT", "integer"),
    "SMALLINT": ("SHORT", "short"),
    "SHORT": ("SHORT", "short"),
    "TINYINT": ("BYTE", "byte"),
    "BYTE": ("BYTE", "byte"),
    "STRING": ("STRING", "string"),
    "BOOLEAN": ("BOOLEAN", "boolean"),
    "DOUBLE": ("DOUBLE", "double"),
    "FLOAT": ("FLOAT", "float"),
    "DATE": ("DATE", "date"),
    "TIMESTAMP": ("TIMESTAMP", "timestamp"),
    "TIMESTAMP_NTZ": ("TIMESTAMP_NTZ", "timestamp_ntz"),
    "BINARY": ("BINARY", "binary"),
}


class TableService:
    """Servicio para administrar tablas de Unity Catalog."""

    def __init__(self, client: WorkspaceClient, warehouse_id: str | None = None):
        self.client = client
        self.warehouse_id = warehouse_id

    def create(self, table: TableCreate) -> TableInfo:
        """Crear una tabla externa de Unity Catalog.

        La API del SDK solo soporta tablas externas, por lo que
        `storage_location` es obligatorio. El comentario no es soportado
        por esta API y no se aplica.
        """

        try:
            if not table.storage_location:
                raise ValueError("storage_location es obligatorio.")

            response = self.client.tables.create(
                name=table.name,
                catalog_name=table.catalog_name,
                schema_name=table.schema_name,
                table_type=table.table_type,
                data_source_format=table.data_source_format,
                storage_location=table.storage_location,
                columns=[
                    self._to_column_info(column, position)
                    for position, column in enumerate(table.columns)
                ] or None,
                properties=table.properties or None,
            )

            return self._to_model(response)

        except Exception as exc:
            raise RuntimeError(
                f"No fue posible crear la tabla "
                f"{table.catalog_name}.{table.schema_name}.{table.name}: {exc}"
            ) from exc  

    @staticmethod
    def _quote(identifier: str) -> str:
        if not _IDENTIFIER_PATTERN.match(identifier):
            raise ValueError(f"Identificador no válido: {identifier!r}")
        return f"`{identifier}`"

    @staticmethod
    def _literal(value: str) -> str:
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"

    @classmethod
    def build_create_sql(cls, table: TableCreate) -> str:
        """Construir el CREATE TABLE IF NOT EXISTS de una tabla."""

        if not table.columns:
            raise ValueError("La tabla requiere al menos una columna.")

        columns = []
        for col in table.columns:
            line = f"  {cls._quote(col.name)} {col.type}"
            if not col.nullable:
                line += " NOT NULL"
            if col.comment:
                line += f" COMMENT {cls._literal(col.comment)}"
            columns.append(line)

        full_name = ".".join(
            cls._quote(part)
            for part in (table.catalog_name, table.schema_name, table.name)
        )
        statement = (
            f"CREATE TABLE IF NOT EXISTS {full_name} (\n"
            + ",\n".join(columns)
            + "\n)"
        )
        if table.comment:
            statement += f"\nCOMMENT {cls._literal(table.comment)}"
        if table.properties:
            props = ", ".join(
                f"{cls._literal(k)} = {cls._literal(v)}"
                for k, v in table.properties.items()
            )
            statement += f"\nTBLPROPERTIES ({props})"
        return statement

    def create_with_sql(self, table: TableCreate) -> TableInfo:
        """Crear una tabla (managed) con SQL en un SQL Warehouse.

        Soporta columnas, comentario y propiedades. Requiere `warehouse_id`.
        """

        full_name = f"{table.catalog_name}.{table.schema_name}.{table.name}"

        try:
            if not self.warehouse_id:
                raise ValueError("Se requiere un warehouse_id para crear tablas con SQL.")

            response = self.client.statement_execution.execute_statement(
                warehouse_id=self.warehouse_id,
                statement=self.build_create_sql(table),
                wait_timeout="50s",
            )
            status = response.status
            if not status or status.state != StatementState.SUCCEEDED:
                message = status.error.message if status and status.error else (
                    f"estado {status.state if status else 'desconocido'}"
                )
                raise RuntimeError(message)

            return self._to_model(self.client.tables.get(full_name=full_name))

        except Exception as exc:
            raise RuntimeError(
                f"No fue posible crear la tabla {full_name} con SQL: {exc}"
            ) from exc

    def create_from_sql_file(self, url: str, catalog: str | None = None) -> list[str]:
        """Ejecutar las sentencias de un archivo SQL en un SQL Warehouse.

        Retorna las sentencias ejecutadas. Requiere `warehouse_id`.
        """

        return run_sql_script(self.client, self.warehouse_id, url, catalog)

    @staticmethod
    def _to_column_info(column: TableColumn, position: int) -> catalog.ColumnInfo:
        """Convertir una columna del modelo a ColumnInfo del SDK."""

        sql_type = column.type.strip().upper()
        mapped = _TYPE_MAP.get(sql_type)

        if mapped:
            type_name, json_type = mapped
        elif sql_type.startswith("DECIMAL"):
            type_name = "DECIMAL"
            json_type = sql_type.lower()
        else:
            raise ValueError(
                f"Tipo de columna no soportado: {column.type!r} "
                f"(columna {column.name!r})."
            )

        type_json = json.dumps(
            {
                "name": column.name,
                "type": json_type,
                "nullable": column.nullable,
                "metadata": {},
            }
        )

        return catalog.ColumnInfo(
            name=column.name,
            type_text=column.type.strip().lower(),
            type_name=catalog.ColumnTypeName(type_name),
            type_json=type_json,
            position=position,
            nullable=column.nullable,
            comment=column.comment,
        )

    def get(self, catalog: str, schema: str, name: str) -> TableInfo:
        """Consultar una tabla por nombre completo."""

        full_name = f"{catalog}.{schema}.{name}"

        response = self.client.tables.get(
            full_name=full_name,
        )
      
        return self._to_model(response)

    
    @staticmethod
    def _to_model(response: catalog.TableInfo) -> TableInfo:
        """Convertir la respuesta del SDK de Databricks al modelo interno."""
        table_type = response.table_type
        return TableInfo(
            name=response.name,
            catalog_name=response.catalog_name,
            schema_name=response.schema_name,
            full_name=response.full_name,
            table_type=table_type.value if table_type else None,
            comment=response.comment,
            table_id=response.table_id,
            metastore_id=response.metastore_id,
            created_at=response.created_at,
            created_by=response.created_by,
            updated_at=response.updated_at,
            updated_by=response.updated_by,
        )
