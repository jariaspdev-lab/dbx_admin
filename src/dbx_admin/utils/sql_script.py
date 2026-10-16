import urllib.request
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState


def read_sql_script(url: str, client: WorkspaceClient | None = None) -> str:
    """Leer un script SQL desde una URL http(s), un Volume o una ruta local.

    Las rutas /Volumes/... se leen con la API de Files cuando existe cliente
    y no están montadas localmente (por ejemplo, fuera de Databricks).
    """

    if url.lower().startswith(("http://", "https://")):
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.read().decode("utf-8-sig")

    path = Path(url)
    if path.is_file():
        return path.read_text(encoding="utf-8-sig")

    if client is not None and url.startswith("/Volumes/"):
        response = client.files.download(url)
        return response.contents.read().decode("utf-8-sig")

    raise FileNotFoundError(f"No existe el archivo SQL: {url}")


def split_statements(script: str) -> list[str]:
    """Separar un script en sentencias por ';' ignorando comillas y comentarios."""

    statements: list[str] = []
    current: list[str] = []
    quote: str | None = None
    i, n = 0, len(script)

    while i < n:
        ch = script[i]
        if quote:
            current.append(ch)
            if ch == "\\" and i + 1 < n:
                current.append(script[i + 1])
                i += 1
            elif ch == quote:
                quote = None
        elif ch in ("'", '"', "`"):
            quote = ch
            current.append(ch)
        elif script.startswith("--", i):
            end = script.find("\n", i)
            i = n if end == -1 else end - 1
        elif script.startswith("/*", i):
            end = script.find("*/", i + 2)
            i = n if end == -1 else end + 1
        elif ch == ";":
            statements.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
        i += 1

    statements.append("".join(current).strip())
    return [s for s in statements if s]


def run_sql_script(
    client: WorkspaceClient,
    warehouse_id: str | None,
    url: str,
    catalog: str | None = None,
) -> list[str]:
    """Ejecutar las sentencias de un script SQL en un SQL Warehouse.

    Retorna las sentencias ejecutadas. Lanza RuntimeError ante cualquier fallo.
    """

    try:
        if not warehouse_id:
            raise ValueError("Se requiere un warehouse_id para ejecutar scripts SQL.")

        statements = split_statements(read_sql_script(url, client))
        if not statements:
            raise ValueError("El script SQL no contiene sentencias.")

        for statement in statements:
            response = client.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=statement,
                catalog=catalog,
                wait_timeout="50s",
            )
            status = response.status
            if not status or status.state != StatementState.SUCCEEDED:
                message = status.error.message if status and status.error else (
                    f"estado {status.state if status else 'desconocido'}"
                )
                raise RuntimeError(f"{message}\nSentencia: {statement}")

        return statements

    except Exception as exc:
        raise RuntimeError(
            f"No fue posible ejecutar el script SQL {url}: {exc}"
        ) from exc
