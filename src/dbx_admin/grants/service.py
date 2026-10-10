from databricks.sdk import WorkspaceClient
from databricks.sdk.service import catalog
from .models import Grant, GrantRequest, GrantResult


class GrantService:

    def __init__(self, client: WorkspaceClient):
        self.client = client

    def list_effective_schema_grants(
        self,
        catalog_name: str,
        schema_name: str,
        principal: str | None = None,
    ) -> list[Grant]:
        try:

          full_name = f"{catalog_name}.{schema_name}"

          response = self.client.grants.get_effective(
              securable_type="schema",
              full_name=full_name,
              principal=principal,
          )

          result = []

          for assignment in response.privilege_assignments or []:

              for privilege in assignment.privileges or []:
                  if not privilege:
                      privilege_value = "None"
                  else:
                      if not privilege.privilege:
                          privilege_value = "None"
                      else:
                          privilege_value = privilege.privilege.value
                  result.append(
                      Grant(
                          principal=assignment.principal,
                          privilege=privilege_value,
                          object_type="SCHEMA",
                          object_name=full_name,
                      )
                  )
          return result
        except Exception as exc:
            raise RuntimeError(
                f"No fue posible listar los grants efectivos del esquema "
                f"{catalog_name}.{schema_name}: {exc}"
            ) from exc

    def list_schema_grants(
        self,
        catalog_name: str,
        schema_name: str,
        principal: str | None = None,
    ) -> list[Grant]:

        full_name = f"{catalog_name}.{schema_name}"

        response = self.client.grants.get(
            securable_type="schema",
            full_name=full_name,
            principal=principal,
        )

        result = []

        for assignment in response.privilege_assignments or []:

            for privilege in assignment.privileges or []:
                result.append(
                    Grant(
                        principal=assignment.principal,
                        privilege=privilege,
                        object_type="SCHEMA",
                        object_name=full_name,
                    )
                )

        return result

    def grant_schema(
        self,
        catalog: str,
        schema: str,
        request: GrantRequest,
    ) -> GrantResult:

        sql = f"""
            GRANT {request.privilege}
            ON SCHEMA `{catalog}`.`{schema}`
            TO `{request.principal}`
        """

        self._execute(sql)

        return GrantResult(
            principal=request.principal,
            privilege=request.privilege,
            object_type="SCHEMA",
            object_name=f"{catalog}.{schema}",
        )

    def grant(
        self,
        securable_type: str,
        full_name: str,
        principal: str,
        privileges: list[str],
    ) -> GrantResult:
        """Otorgar privilegios sobre un objeto usando la Grants API."""

        try:
            self.client.grants.update(
                securable_type=securable_type,
                full_name=full_name,
                changes=[
                    catalog.PermissionsChange(
                        principal=principal,
                        add=[catalog.Privilege(p) for p in privileges],
                    )
                ],
            )
        except Exception as exc:
            raise RuntimeError(
                f"No fue posible otorgar {', '.join(privileges)} sobre "
                f"{securable_type} {full_name} a {principal}: {exc}"
            ) from exc

        return GrantResult(
            principal=principal,
            privilege=", ".join(privileges),
            object_type=securable_type,
            object_name=full_name,
        )

    def _execute(self, sql: str):
        response = self.client.statement_execution.execute_statement(
            warehouse_id=self._get_warehouse_id(),
            statement=sql,
        )

        return response.result.data_array if response.result else []

    def _get_warehouse_id(self) -> str:
        raise NotImplementedError(
            "Configurar SQL Warehouse para ejecutar sentencias SQL."
        )