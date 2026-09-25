import typer

from databricks.sdk import WorkspaceClient

from dbx_admin.secrets.models import SecretCreate
from dbx_admin.secrets.service import SecretService
from dbx_admin.decode.service import DecodeService
from dbx_admin.decode.models import DecodeRequest


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

app.add_typer(
    secrets_app,
    name="secrets",
)
app.add_typer(
    decode_app,
    name="decode",
)


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

    typer.echo(f"Secret Scope: {scope}")
    typer.echo("-" * 50)

    for secret in secrets:
        typer.echo(secret.key)


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


if __name__ == "__main__":
    app()