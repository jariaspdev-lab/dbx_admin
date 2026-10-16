from datetime import datetime
from pathlib import Path

import typer


from databricks.sdk import WorkspaceClient
from databricks.sdk.service import catalog
from dbx_admin.secrets.models import SecretCreate
from dbx_admin.secrets.service import SecretService
from dbx_admin.decode.service import DecodeService
from dbx_admin.decode.models import DecodeRequest
from dbx_admin.context.service import ContextService
from dbx_admin.apps.service import AppService
from dbx_admin.tables.models import TableCreate
from dbx_admin.volumes.service import VolumeService
from dbx_admin.volumes.models import VolumeCreate, VolumeType
from dbx_admin.grants.service import GrantService
from dbx_admin.tables.service import TableService
from dbx_admin.schemas.service import SchemaService
from dbx_admin.schemas.models import SchemaCreate
from dbx_admin.manifiesto.service import ManifestService
from dbx_admin.manifiesto.url_service import ManifestUrlService
from dbx_admin.warehouses.service import WarehousesService

app = typer.Typer(
    name="dbx-admin",
    help="Herramientas de administración para Databricks.",
)

secrets_app = typer.Typer(
    name="secrets",
    help="Administración de secretos de Databricks.",
)

decode_app = typer.Typer(
    name="decode",
    help="Decodificación de valores.",
)

context_app = typer.Typer(
    name="context",
    help="Inspeccionar el contexto actual de Databricks.",
)

app_app = typer.Typer(
    name="app",
    help="Administración de Databricks Apps.",
)

volume_app = typer.Typer(
    name="volume",
    help="Administración de volúmenes de Unity Catalog.",
)

warehouses_app = typer.Typer(
    name="warehouses",
    help="Administración de warehouses de Unity Catalog.",
)

table_app = typer.Typer(
    name="table",
    help="Administración de tablas de Unity Catalog.",
)

schema_app = typer.Typer(
    name="schema",
    help="Administración de schemas de Unity Catalog.",
)

grants_app = typer.Typer(
    name="grants",
    help="Administrar privilegios de Unity Catalog."
)

manifest_app = typer.Typer(
    name="manifest",
    help="Aprovisionar recursos desde un manifiesto YAML.",
)

app.add_typer(
    manifest_app,
    name="manifest",
)

manifest_url_app = typer.Typer(
    name="manifest-url",
    help="Aprovisionar recursos desde un manifiesto YAML con scripts SQL (url).",
)

app.add_typer(
    manifest_url_app,
    name="manifest-url",
)

grants_schema_app = typer.Typer(
    name="schema",
    help="Administrar grants sobre schemas."
)

app.add_typer(
    secrets_app,
    name="secrets",
)
app.add_typer(
    decode_app,
    name="decode",
)
app.add_typer(
    context_app,
    name="context",
)
app.add_typer(
    app_app,
    name="app",
)

app.add_typer(
    volume_app,
    name="volume",
)

app.add_typer(
    table_app,
    name="table",
)

app.add_typer(
    schema_app,
    name="schema",
)

app.add_typer(
    warehouses_app,
    name="warehouses",
)

app.add_typer(
    grants_app,
    name="grants",
)

grants_app.add_typer(
    grants_schema_app,
    name="schema",
)


def fmt_ts(value) -> str:
    """Formatear timestamps (epoch en ms) a texto legible."""

    if value in (None, ""):
        return "-"
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000).strftime("%Y-%m-%d %H:%M:%S")
    return str(value)


def print_sections(sections: dict) -> None:
    """Imprimir secciones con título.

    Cada sección es una lista de tuplas (etiqueta, valor) alineadas,
    o una lista de valores simples que se imprimen como viñetas.
    """

    labels = [
        len(item[0])
        for rows in sections.values()
        for item in rows
        if isinstance(item, tuple)
    ]
    width = max(labels, default=0)

    for title, rows in sections.items():
        typer.secho(f"\n{title}", bold=True, fg=typer.colors.CYAN)
        typer.echo("-" * (width + 30))

        if not rows:
            typer.echo("-")
            continue

        for item in rows:
            if isinstance(item, tuple):
                label, value = item
                value = "-" if value in (None, "") else value
                typer.echo(f"{label:<{width}} : {value}")
            else:
                typer.echo(f"  - {item}")
    typer.echo()


def print_table(headers: list[str], rows: list[tuple]) -> None:
    """Imprimir filas en columnas alineadas con encabezado y total."""

    cells = [
        ["-" if v in (None, "") else str(getattr(v, "value", v)) for v in row]
        for row in rows
    ]
    widths = [
        max(len(h), *(len(r[i]) for r in cells))
        for i, h in enumerate(headers)
    ]

    typer.secho(
        "  ".join(h.ljust(w) for h, w in zip(headers, widths)),
        bold=True,
    )
    typer.echo("  ".join("-" * w for w in widths))
    for row in cells:
        typer.echo("  ".join(c.ljust(w) for c, w in zip(row, widths)))
    typer.echo(f"\nTotal: {len(cells)}\n")


def get_client() -> WorkspaceClient:
    """Crear cliente de Databricks."""

    return WorkspaceClient()


def get_secret_service() -> SecretService:
    """Crear servicio de secretos."""

    client = get_client()

    return SecretService(client)


@secrets_app.command("list")
def list_secrets(
    scope: str = typer.Option(
        ...,
        "--scope",
        "-s",
        help="Nombre del Secret Scope.",
    ),
):
    """Listar secretos de un Secret Scope."""

    service = get_secret_service()

    secrets = service.list(scope)

    if not secrets:
        typer.echo("No se encontraron secretos.")
        return

    typer.secho(f"\nSecret Scope: {scope}", bold=True, fg=typer.colors.CYAN)
    print_table(["#", "Secreto"], [(i, s.key) for i, s in enumerate(secrets, 1)])


@secrets_app.command("create")
def create_secret(
    scope: str = typer.Option(
        ...,
        "--scope",
        "-s",
        help="Nombre del Secret Scope.",
    ),
    key: str = typer.Option(
        ...,
        "--key",
        "-k",
        help="Nombre del secreto.",
    ),
    value: str = typer.Option(
        ...,
        "--value",
        "-v",
        help="Valor del secreto.",
        hide_input=True,
    ),
):
    """Crear o actualizar un secreto."""

    secret = SecretCreate(
        scope=scope,
        key=key,
        value=value,
    )

    service = get_secret_service()

    service.create(secret)

    typer.echo(
        f"✓ Secret '{key}' creado/actualizado "
        f"en scope '{scope}'."
    )


@secrets_app.command("validate")
def validate_secret(
    scope: str = typer.Option(
        ...,
        "--scope",
        "-s",
        help="Nombre del Secret Scope.",
    ),
    key: str = typer.Option(
        ...,
        "--key",
        "-k",
        help="Nombre del secreto.",
    ),
):
    """Validar que un secreto exista."""

    service = get_secret_service()

    result = service.validate(
        scope=scope,
        key=key,
    )

    if result.exists:
        typer.echo(
            f"✓ Secret '{key}' existe "
            f"en '{scope}'."
        )
    else:
        typer.echo(
            f"✗ Secret '{key}' NO existe "
            f"en '{scope}'."
        )

        raise typer.Exit(code=1)

@secrets_app.command("get")
def get_secret(
    scope: str = typer.Option(
        ...,
        "--scope",
        "-s",
        help="Nombre del Secret Scope.",
    ),
    key: str = typer.Option(
        ...,
        "--key",
        "-k",
        help="Nombre del secreto.",
    ),
):
    """Obtener el valor de un secreto."""

    service = get_secret_service()

    value = service.get(
        scope=scope,
        key=key,
    )

    typer.echo(value)    

@decode_app.command("base64")
def decode_value(
    value: str = typer.Option(
        ...,
        "--value",
        "-v",
        help="Valor Base64 a decodificar.",
    ),
):
    """Valor Base64 a decodificar."""

    service = DecodeService()

    request = DecodeRequest(
        value=value,
        encoding="base64",
    )

    response = service.decode(request)

    typer.echo(response.value)


@context_app.command("show")
def show(
    user_id: str | None = typer.Option(
        None,
        "--user-id",
        "-u",
        help="ID del usuario a consultar. "
             "Si no se indica, se consulta el usuario actual.",
    ),
):
    """Mostrar la identidad y contexto actual."""

    client = get_client()
    service = ContextService(client)

    response = service.get_user(user_id=user_id)
    print_sections({
        "Usuario": [
            ("Usuario", response.username),
            ("Nombre", response.display_name),
            ("Activo", response.active),
            ("ID externo", response.external_id),
            ("ID", response.id),
        ],
        "Grupos": list(response.groups or []),
        "Roles": list(response.roles or []),
        "Entitlements": list(response.entitlements or []),
    })

@app_app.command("show")
def get_app(
    name_app: str = typer.Option(
        ...,
        "--name",
        "-n",
        help="Nombre de la App.",
    ),
):
    """Obtener información de una App."""

    client = get_client()
    service = AppService(client)

    response = service.get_app(name=name_app)
    print_sections({
        "Información general": [
            ("Nombre", response.name),
            ("Descripción", response.description),
            ("Estado", response.status),
            ("Estado de la app", response.app_status),
            ("URL", response.url),
            ("SQL Warehouse", response.sql_warehouse),
        ],
        "Service Principal": [
            ("Client ID", response.service_principal_client_id),
            ("ID", response.service_principal_id),
            ("Nombre", response.service_principal_name),
        ],
        "Auditoría": [
            ("Creado en", fmt_ts(response.created_at)),
            ("Creado por", response.creator),
            ("Actualizado en", fmt_ts(response.updated_at)),
            ("Actualizado por", response.updater),
        ],
    })

@volume_app.command("list")
def list_volumes(
    catalog: str = typer.Option(
        ...,
        "--catalog",
        "-c",
    ),
    schema: str = typer.Option(
        ...,
        "--schema",
        "-s",
    ),
):
    """Listar todos los volúmenes en un esquema específico."""

    client = get_client()
    service = VolumeService(client)

    volumes = service.list(
        catalog=catalog,
        schema=schema,
    )

    volumes = list(volumes)

    if not volumes:
        typer.echo("No se encontraron volúmenes.")
        return

    typer.secho(f"\nVolúmenes de {catalog}.{schema}", bold=True, fg=typer.colors.CYAN)
    print_table(
        ["Nombre", "Tipo", "Propietario", "Ubicación", "Comentario"],
        [
            (v.name, v.volume_type, v.owner, v.storage_location, v.comment)
            for v in volumes
        ],
    )

@volume_app.command("show")
def show_volume(
    catalog: str = typer.Option(
        ...,
        "--catalog",
        "-c",
    ),
    schema: str = typer.Option(
        ...,
        "--schema",
        "-s",
    ),
    name: str = typer.Option(
        ...,
        "--name",
        "-n",
    ),
):
    """Mostrar información de un volumen."""

    client = get_client()
    service = VolumeService(client)

    volume = service.get(
        catalog=catalog,
        schema=schema,
        name=name,
    )

    print_sections({
        "Información general": [
            ("Nombre", volume.name),
            ("Nombre completo", volume.full_name),
            ("Catalog", volume.catalog_name),
            ("Schema", volume.schema_name),
            ("Tipo de volumen", volume.volume_type),
            ("Comentario", volume.comment),
        ],
        "Almacenamiento": [
            ("Ubicación", volume.storage_location),
            ("Propietario", volume.owner),
        ],
        "Identificadores": [
            ("ID de volumen", volume.volume_id),
        ],
    })

@volume_app.command("create")
def create_volume(
    catalog: str = typer.Option(
        ...,
        "--catalog",
        "-c",
        help="Nombre del catalog.",
    ),
    schema: str = typer.Option(
        ...,
        "--schema",
        "-s",
        help="Nombre del schema.",
    ),
    name: str = typer.Option(
        ...,
        "--name",
        "-n",
        help="Nombre del volumen.",
    ),
    volume_type: VolumeType = typer.Option(
        VolumeType.MANAGED,
        "--type",
        "-t",
        help="Tipo de volumen: MANAGED o EXTERNAL.",
    ),
    storage_location: str | None = typer.Option(
        None,
        "--storage-location",
        help="Ubicación del volumen externo.",
    ),
    comment: str | None = typer.Option(
        None,
        "--comment",
        help="Descripción del volumen.",
    ),
):
    """Crear un volumen de Unity Catalog."""

    client = get_client()

    service = VolumeService(client)

    request = VolumeCreate(
        catalog_name=catalog,
        schema_name=schema,
        name=name,
        volume_type=volume_type,
        storage_location=storage_location,
        comment=comment,
    )

    volume = service.create(request)

    typer.echo(
        f"Volume creado: {volume.full_name}"
    )


@volume_app.command("create-sql")
def create_volume_sql(
    url_script_sql: str = typer.Option(
        ...,
        "--url-script-sql",
        "-u",
        help="Ruta o URL (http/https) del archivo .sql con la creación del volumen.",
    ),
    warehouse_id: str | None = typer.Option(
        None,
        "--warehouse-id",
        "-w",
        envvar="DATABRICKS_WAREHOUSE_ID",
        help="SQL Warehouse donde se ejecuta el script.",
    ),
):
    """Crear volúmenes ejecutando un script SQL."""

    service = VolumeService(get_client(), warehouse_id=warehouse_id)

    try:
        statements = service.create_from_sql_file(url_script_sql)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)

    typer.echo(f"Script ejecutado: {len(statements)} sentencia(s).")


@grants_schema_app.command("list")
def list_schema_grants(
    catalog: str = typer.Option(
        ...,
        "--catalog",
        "-c",
        help="Nombre del catalog.",
    ),
    schema: str = typer.Option(
        ...,
        "--schema",
        "-s",
        help="Nombre del schema.",
    ),
    effective: bool = typer.Option(
        False,
        "--effective",
        help="Mostrar privilegios efectivos, incluyendo privilegios heredados.",
    ),
    principal: str | None = typer.Option(
        None,
        "--principal",
        "-p",
        help="Filtrar por principal.",
    ),
):
    """Listar todos los grants de un esquema específico."""

    client = get_client()
    service = GrantService(client)

    if effective:
        grants = service.list_effective_schema_grants(
            catalog_name=catalog,
            schema_name=schema,
            principal=principal,
        )
    else:
        grants = service.list_schema_grants(
            catalog_name=catalog,
            schema_name=schema,
            principal=principal,
        )

    if not grants:
        typer.echo("No se encontraron grants.")
        return

    typer.secho(f"\nGrants de {catalog}.{schema}", bold=True, fg=typer.colors.CYAN)
    print_table(
        ["Principal", "Privilegio", "Tipo de objeto", "Objeto"],
        [
            (g.principal, g.privilege, g.object_type, g.object_name)
            for g in grants
        ],
    )

@table_app.command("show")
def show_table(
    catalog: str = typer.Option(
        ...,
        "--catalog",
        "-c",
        help="Nombre del catalog.",
    ),
    schema: str = typer.Option(
        ...,
        "--schema",
        "-s",
        help="Nombre del schema.",
    ),
    name: str = typer.Option(
        ...,
        "--name",
        "-n",
        help="Nombre de la tabla.",
    ),
):
    """Mostrar información de una tabla específica."""

    client = get_client()
    service = TableService(client)

    table = service.get(
        catalog=catalog,
        schema=schema,
        name=name,
    )

    print_sections({
        "Información general": [
            ("Nombre", table.name),
            ("Nombre completo", table.full_name),
            ("Catalog", table.catalog_name),
            ("Schema", table.schema_name),
            ("Tipo de tabla", table.table_type),
            ("Comentario", table.comment),
        ],
        "Identificadores": [
            ("ID de tabla", table.table_id),
            ("ID de metastore", table.metastore_id),
        ],
        "Auditoría": [
            ("Creado en", fmt_ts(table.created_at)),
            ("Creado por", table.created_by),
            ("Actualizado en", fmt_ts(table.updated_at)),
            ("Actualizado por", table.updated_by),
        ],
    })

@table_app.command("create")   
def create_table(
    catalog: str = typer.Option(
        ...,
        "--catalog",
        "-c",
        help="Nombre del catalog.",
    ),
    schema: str = typer.Option(
        ...,
        "--schema",
        "-s",
        help="Nombre del schema.",
    ),
    name: str = typer.Option(
        ...,
        "--name",
        "-n",
        help="Nombre de la tabla.",
    ),
    table_type: catalog.TableType = typer.Option(
        catalog.TableType.MANAGED,
        "--table-type",
        "-t",
        help="Tipo de la tabla: MANAGED o EXTERNAL.",
    ),
    comment: str | None = typer.Option(
        None,
        "--comment",
        "-m",
        help="Comentario de la tabla.",
    ),
):
    """Crear una nueva tabla en Unity Catalog."""

    client = get_client()
    service = TableService(client)

    table = service.create(
        TableCreate(
            catalog_name=catalog,
            schema_name=schema,
            name=name,
            table_type=table_type,
            comment=comment,
        )
    )

    typer.echo(f"Tabla creada: {table.full_name}")


@schema_app.command("create")
def create_schema(
    catalog: str = typer.Option(
        ...,
        "--catalog",
        "-c",
        help="Nombre del catalog.",
    ),
    name: str = typer.Option(
        ...,
        "--name",
        "-n",
        help="Nombre del schema.",
    ),
    comment: str | None = typer.Option(
        None,
        "--comment",
        "-m",
        help="Comentario del schema.",
    ),
):
    """Crear un nuevo schema en Unity Catalog."""

    service = SchemaService(get_client())

    try:
        schema = service.create(
            SchemaCreate(catalog_name=catalog, name=name, comment=comment)
        )
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)

    typer.echo(f"Schema creado: {schema.full_name}")


@schema_app.command("create-sql")
def create_schema_sql(
    url_script_sql: str = typer.Option(
        ...,
        "--url-script-sql",
        "-u",
        help="Ruta o URL (http/https) del archivo .sql con la creación del schema.",
    ),
    warehouse_id: str | None = typer.Option(
        None,
        "--warehouse-id",
        "-w",
        envvar="DATABRICKS_WAREHOUSE_ID",
        help="SQL Warehouse donde se ejecuta el script.",
    ),
):
    """Crear schemas ejecutando un script SQL."""

    service = SchemaService(get_client(), warehouse_id=warehouse_id)

    try:
        statements = service.create_from_sql_file(url_script_sql)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)

    typer.echo(f"Script ejecutado: {len(statements)} sentencia(s).")


@table_app.command("create-sql")
def create_table_sql(
    url_script_sql: str = typer.Option(
        ...,
        "--url-script-sql",
        "-u",
        help="Ruta o URL (http/https) del archivo .sql con la creación de la tabla.",
    ),
    warehouse_id: str | None = typer.Option(
        None,
        "--warehouse-id",
        "-w",
        envvar="DATABRICKS_WAREHOUSE_ID",
        help="SQL Warehouse donde se ejecuta el script.",
    ),
):
    """Crear tablas ejecutando un script SQL."""

    service = TableService(get_client(), warehouse_id=warehouse_id)

    try:
        statements = service.create_from_sql_file(url_script_sql)
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)

    typer.echo(f"Script ejecutado: {len(statements)} sentencia(s).")


@manifest_app.command("apply")
def apply_manifest(
    file: Path = typer.Option(
        Path("resources/manifest.yml"),
        "--file",
        "-f",
        help="Ruta del manifiesto YAML.",
    ),
    var: list[str] = typer.Option(
        [],
        "--var",
        help="Variable del manifiesto en formato nombre=valor. Repetible.",
    ),
    warehouse_id: str | None = typer.Option(
        None,
        "--warehouse-id",
        "-w",
        envvar="DATABRICKS_WAREHOUSE_ID",
        help="SQL Warehouse para crear tablas.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Mostrar lo que se crearía sin ejecutar cambios.",
    ),
):
    """Crear esquemas, volúmenes y tablas definidos en un manifiesto."""

    variables = {}
    for item in var:
        key, sep, value = item.partition("=")
        if not sep or not key:
            raise typer.BadParameter(
                f"Formato inválido '{item}'. Use nombre=valor.",
                param_hint="--var",
            )
        variables[key] = value

    try:
        service = ManifestService(get_client(), warehouse_id=warehouse_id)
        manifest = service.load(file, variables)
        result = service.apply(manifest, dry_run=dry_run)
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.secho(
        f"\nManifiesto: {manifest.project.name}"
        f"{' (dry-run)' if dry_run else ''}",
        bold=True,
        fg=typer.colors.CYAN,
    )
    print_table(
        ["Tipo", "Recurso", "Estado", "Detalle"],
        [
            (r.kind, r.full_name, r.status, r.detail)
            for r in result.resources
        ],
    )

    if result.has_errors:
        raise typer.Exit(code=1)

@manifest_url_app.command("apply")
def apply_manifest_url(
    file: Path = typer.Option(
        Path("resources/manifest-url.yaml"),
        "--file",
        "-f",
        help="Ruta del manifiesto YAML con scripts SQL.",
    ),
    var: list[str] = typer.Option(
        [],
        "--var",
        help="Variable del manifiesto en formato nombre=valor. Repetible.",
    ),
    warehouse_id: str | None = typer.Option(
        None,
        "--warehouse-id",
        "-w",
        envvar="DATABRICKS_WAREHOUSE_ID",
        help="SQL Warehouse donde se ejecutan los scripts.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Mostrar lo que se ejecutaría sin ejecutar cambios.",
    ),
):
    """Ejecutar los scripts SQL y grants definidos en un manifiesto."""

    variables = {}
    for item in var:
        key, sep, value = item.partition("=")
        if not sep or not key:
            raise typer.BadParameter(
                f"Formato inválido '{item}'. Use nombre=valor.",
                param_hint="--var",
            )
        variables[key] = value

    try:
        service = ManifestUrlService(get_client(), warehouse_id=warehouse_id)
        manifest = service.load(file, variables)
        result = service.apply(manifest, dry_run=dry_run)
    except (FileNotFoundError, ValueError) as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    typer.secho(
        f"\nManifiesto: {manifest.project.name}"
        f"{' (dry-run)' if dry_run else ''}",
        bold=True,
        fg=typer.colors.CYAN,
    )
    print_table(
        ["Tipo", "Recurso", "Estado", "Detalle"],
        [
            (r.kind, r.full_name, r.status, r.detail)
            for r in result.resources
        ],
    )

    if result.has_errors:
        raise typer.Exit(code=1)


@warehouses_app.command("list")
def list_warehouses():
    """Listar todos los warehouses de Unity Catalog."""
    client = get_client()
    service = WarehousesService(client)
    warehouses = service.get_list_warehouses()
    print_table(
        ["ID", "Nombre", "Estado"],
        [(w.id, w.name, w.state) for w in warehouses],
    )


if __name__ == "__main__":
    app()