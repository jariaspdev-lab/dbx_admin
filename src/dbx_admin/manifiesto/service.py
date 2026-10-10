import re
from pathlib import Path

import yaml
from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import NotFound

from dbx_admin.grants.service import GrantService
from dbx_admin.tables.models import TableColumn, TableCreate
from dbx_admin.tables.service import TableService
from dbx_admin.volumes.models import VolumeCreate
from dbx_admin.volumes.service import VolumeService

from .models import (
    ApplyResult,
    Manifest,
    GrantObjectType,
    GrantSpec,
    ResourceKind,
    ResourceResult,
    ResourceStatus,
    TableSpec,
    VolumeSpec,
)

_VAR_PATTERN = re.compile(r"\$\{var\.([A-Za-z0-9_]+)\}")


class ManifestService:
    """Aplica un manifiesto creando esquemas, volúmenes, tablas y grants.

    Las tablas se crean con SQL vía `TableService.create_with_sql`, por lo que
    se requiere un SQL Warehouse (`warehouse_id`) si el manifiesto las incluye.
    Los grants se aplican con `GrantService`.
    """

    def __init__(self, client: WorkspaceClient, warehouse_id: str | None = None):
        self.client = client
        self.volume_service = VolumeService(client)
        self.table_service = TableService(client, warehouse_id=warehouse_id)
        self.grant_service = GrantService(client)

    # ------------------------------------------------------------------
    # Carga del manifiesto
    # ------------------------------------------------------------------
    @staticmethod
    def load(path: str | Path, variables: dict[str, str] | None = None) -> Manifest:
        """Leer el YAML, sustituir ${var.x} y validarlo."""

        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"No existe el manifiesto: {path}")

        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        resolved = ManifestService._resolve_variables(raw, variables or {})
        return Manifest.model_validate(resolved)

    @staticmethod
    def _resolve_variables(value, variables: dict[str, str]):
        if isinstance(value, dict):
            return {
                k: ManifestService._resolve_variables(v, variables)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [ManifestService._resolve_variables(v, variables) for v in value]
        if isinstance(value, str):

            def replace(match: re.Match) -> str:
                name = match.group(1)
                if name not in variables:
                    raise ValueError(
                        f"Variable sin valor: ${{var.{name}}}. "
                        f"Debe proporcionarla en `variables`."
                    )
                return variables[name]

            return _VAR_PATTERN.sub(replace, value)
        return value

    # ------------------------------------------------------------------
    # Aplicación
    # ------------------------------------------------------------------
    def apply(self, manifest: Manifest, dry_run: bool = False) -> ApplyResult:
        """Crear los recursos en orden: esquemas, volúmenes y tablas.

        Es idempotente: los recursos existentes se omiten. Un error en un
        recurso no detiene el resto; se reporta en el resultado.
        Los volúmenes y tablas sin `schema` se crean en `target.schema`.
        """

        catalog = manifest.target.catalog
        default_schema = manifest.target.schema_name
        infra = manifest.infrastructure
        result = ApplyResult()

        # Esquemas: el destino por defecto, los declarados y los referenciados.
        schemas: dict[str, str | None] = {}
        if default_schema:
            schemas[default_schema] = None
        for spec in [*infra.volumes, *infra.tables]:
            if spec.schema_name:
                schemas.setdefault(spec.schema_name, None)
        for spec in infra.schemas:
            schemas[spec.name] = spec.comment

        for name, comment in schemas.items():
            result.resources.append(
                self._run(
                    ResourceKind.SCHEMA,
                    f"{catalog}.{name}",
                    dry_run,
                    lambda n=name, c=comment: self._create_schema(catalog, n, c),
                )
            )

        for vol in infra.volumes:
            schema = vol.schema_name or default_schema
            result.resources.append(
                self._run(
                    ResourceKind.VOLUME,
                    f"{catalog}.{schema}.{vol.name}",
                    dry_run,
                    lambda v=vol, s=schema: self._create_volume(catalog, s, v),
                )
            )

        for table in infra.tables:
            schema = table.schema_name or default_schema
            result.resources.append(
                self._run(
                    ResourceKind.TABLE,
                    f"{catalog}.{schema}.{table.name}",
                    dry_run,
                    lambda t=table, s=schema: self._create_table(catalog, s, t),
                )
            )

        for grant in infra.grants:
            privileges = ", ".join(grant.privileges)
            try:
                target = self._grant_target(manifest, grant)
            except ValueError as exc:
                result.resources.append(
                    ResourceResult(
                        kind=ResourceKind.GRANT,
                        full_name=(
                            f"{privileges} ON {grant.object} TO {grant.principal}"
                        ),
                        status=ResourceStatus.FAILED,
                        detail=str(exc),
                    )
                )
                continue

            result.resources.append(
                self._run(
                    ResourceKind.GRANT,
                    f"{privileges} ON {target} TO {grant.principal}",
                    dry_run,
                    lambda g=grant, t=target: self._apply_grant(g, t),
                )
            )

        return result

    def _apply_grant(self, grant: GrantSpec, target: str) -> bool:
        self.grant_service.grant(
            securable_type=grant.object_type.value,
            full_name=target,
            principal=grant.principal,
            privileges=grant.privileges,
        )
        return True

    @classmethod
    def _grant_target(cls, manifest: Manifest, grant: GrantSpec) -> str:
        """Resolver el nombre completo (catalog.schema[.objeto]) de un grant."""

        catalog = manifest.target.catalog
        default_schema = manifest.target.schema_name
        infra = manifest.infrastructure

        if grant.object_type == GrantObjectType.SCHEMA:
            return f"{catalog}.{grant.object}"

        specs = infra.tables if grant.object_type == GrantObjectType.TABLE else infra.volumes
        schemas = (
            {grant.schema_name}
            if grant.schema_name
            else {
                s.schema_name or default_schema
                for s in specs
                if s.name == grant.object
            }
        )
        schemas.discard(None)

        if not schemas:
            raise ValueError(
                f"No se encontró {grant.object_type.value.lower()} "
                f"'{grant.object}' en el manifiesto; indique 'schema'."
            )
        if len(schemas) > 1:
            raise ValueError(
                f"'{grant.object}' existe en varios schemas "
                f"({', '.join(sorted(schemas))}); indique 'schema'."
            )
        return f"{catalog}.{schemas.pop()}.{grant.object}"

    @staticmethod
    def _run(kind, full_name, dry_run, action) -> ResourceResult:
        if dry_run:
            return ResourceResult(
                kind=kind, full_name=full_name, status=ResourceStatus.PLANNED
            )
        try:
            created = action()
            status = ResourceStatus.CREATED if created else ResourceStatus.EXISTS
            return ResourceResult(kind=kind, full_name=full_name, status=status)
        except Exception as exc:
            return ResourceResult(
                kind=kind,
                full_name=full_name,
                status=ResourceStatus.FAILED,
                detail=str(exc),
            )

    # ------------------------------------------------------------------
    # Recursos (retornan True si crearon, False si ya existían)
    # ------------------------------------------------------------------
    def _create_schema(self, catalog: str, name: str, comment: str | None) -> bool:
        try:
            self.client.schemas.get(full_name=f"{catalog}.{name}")
            return False
        except NotFound:
            pass

        self.client.schemas.create(
            name=name,
            catalog_name=catalog,
            comment=comment,
        )
        return True

    def _create_volume(self, catalog: str, schema: str, spec: VolumeSpec) -> bool:
        try:
            self.client.volumes.read(name=f"{catalog}.{schema}.{spec.name}")
            return False
        except NotFound:
            pass

        self.volume_service.create(
            VolumeCreate(
                catalog_name=catalog,
                schema_name=schema,
                name=spec.name,
                volume_type=spec.type,
                storage_location=spec.storage_location,
                comment=spec.comment,
            )
        )
        return True

    def _create_table(self, catalog: str, schema: str, spec: TableSpec) -> bool:
        try:
            self.client.tables.get(full_name=f"{catalog}.{schema}.{spec.name}")
            return False
        except NotFound:
            pass

        self.table_service.create_with_sql(
            TableCreate(
                catalog_name=catalog,
                schema_name=schema,
                name=spec.name,
                columns=[
                    TableColumn(
                        name=c.name,
                        type=c.type,
                        nullable=c.nullable,
                        comment=c.comment,
                    )
                    for c in spec.columns
                ],
                properties=spec.properties,
                comment=spec.comment,
            )
        )
        return True
