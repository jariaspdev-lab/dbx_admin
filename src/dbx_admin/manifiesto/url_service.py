from pathlib import Path

import yaml
from databricks.sdk import WorkspaceClient

from dbx_admin.grants.service import GrantService
from dbx_admin.utils.sql_script import run_sql_script

from .models import (
    ApplyResult,
    GrantObjectType,
    GrantSpec,
    ResourceKind,
    ResourceResult,
    ResourceStatus,
)
from .service import ManifestService
from .url_models import UrlManifest


class ManifestUrlService:
    """Aplica un manifiesto cuyos recursos se definen con scripts SQL.

    Orden: schemas, volúmenes, tablas (cada `url` se ejecuta en el SQL
    Warehouse con `target.catalog` como catalog por defecto) y luego grants.
    Los scripts deben ser idempotentes (CREATE ... IF NOT EXISTS).
    """

    def __init__(self, client: WorkspaceClient, warehouse_id: str | None = None):
        self.client = client
        self.warehouse_id = warehouse_id
        self.grant_service = GrantService(client)

    @staticmethod
    def load(path: str | Path, variables: dict[str, str] | None = None) -> UrlManifest:
        """Leer el YAML, sustituir ${var.x} y validarlo."""

        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"No existe el manifiesto: {path}")

        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        resolved = ManifestService._resolve_variables(raw, variables or {})
        return UrlManifest.model_validate(resolved)

    def apply(self, manifest: UrlManifest, dry_run: bool = False) -> ApplyResult:
        catalog = manifest.target.catalog
        infra = manifest.infrastructure
        result = ApplyResult()

        for kind, specs in (
            (ResourceKind.SCHEMA, infra.schemas),
            (ResourceKind.VOLUME, infra.volumes),
            (ResourceKind.TABLE, infra.tables),
        ):
            for spec in specs:
                result.resources.append(
                    ManifestService._run(
                        kind,
                        spec.url,
                        dry_run,
                        lambda u=spec.url: self._run_script(catalog, u),
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
                ManifestService._run(
                    ResourceKind.GRANT,
                    f"{privileges} ON {target} TO {grant.principal}",
                    dry_run,
                    lambda g=grant, t=target: self._apply_grant(g, t),
                )
            )

        return result

    def _run_script(self, catalog: str, url: str) -> bool:
        run_sql_script(self.client, self.warehouse_id, url, catalog)
        return True

    def _apply_grant(self, grant: GrantSpec, target: str) -> bool:
        self.grant_service.grant(
            securable_type=grant.object_type.value,
            full_name=target,
            principal=grant.principal,
            privileges=grant.privileges,
        )
        return True

    @staticmethod
    def _grant_target(manifest: UrlManifest, grant: GrantSpec) -> str:
        """Resolver el nombre completo de un grant.

        `object` puede ser `objeto`, `schema.objeto` o `catalog.schema.objeto`;
        si es simple se usa `schema` del grant o `target.schema`.
        """

        catalog = manifest.target.catalog
        parts = grant.object.split(".")

        if grant.object_type == GrantObjectType.SCHEMA:
            return grant.object if len(parts) == 2 else f"{catalog}.{grant.object}"

        if len(parts) == 3:
            return grant.object
        if len(parts) == 2:
            return f"{catalog}.{grant.object}"

        schema = grant.schema_name or manifest.target.schema_name
        if not schema:
            raise ValueError(
                f"Indique 'schema' o use 'schema.{grant.object}' para el grant."
            )
        return f"{catalog}.{schema}.{grant.object}"
