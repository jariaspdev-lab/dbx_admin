from xmlrpc import client

from databricks.sdk import WorkspaceClient
from databricks.sdk.service import catalog
from .models import VolumeCreate, VolumeInfo


class VolumeService:
    """Servicio para administrar volúmenes de Unity Catalog."""

    def __init__(self, client: WorkspaceClient):
        self.client = client

    def create(self, volume: VolumeCreate) -> VolumeInfo:
        """Crear un volumen de Unity Catalog."""

        try:
            self.client.tables.create
            response = self.client.volumes.create(
                name=volume.name,
                catalog_name=volume.catalog_name,
                schema_name=volume.schema_name,
                volume_type=catalog.VolumeType(volume.volume_type),
                storage_location=volume.storage_location,
                comment=volume.comment,
            )

            return self._to_model(response)

        except Exception as exc:
            raise RuntimeError(
                f"No fue posible crear el volumen "
                f"{volume.catalog_name}.{volume.schema_name}.{volume.name}: {exc}"
            ) from exc

    def list(
        self,
        catalog: str,
        schema: str,
    ) -> list[VolumeInfo]:
        """Listar todos los volúmenes en un esquema específico."""

        responselist = list(self.client.volumes.list(
            schema_name=schema,
            catalog_name=catalog,
        ))

        return [self._to_model(volume) for volume in responselist]
    

    def get(
        self,
        catalog: str,
        schema: str,
        name: str,
    ) -> VolumeInfo:
        """Consultar un volumen por nombre completo."""

        full_name = f"{catalog}.{schema}.{name}"

        responselist = list(self.client.volumes.list(
            schema_name=schema,
            catalog_name=catalog,
        ))

        print(f"volume list:{type(responselist)}")

        for volume in responselist:
            print("\n")
            print(volume.name)
            print(vars(volume))

        response = self.client.volumes.read(
            name=full_name,
        )

        print(f"volume:{type(response)}")
        print(response)

        return self._to_model(response)

    @staticmethod
    def _to_model(response) -> VolumeInfo:
        """Convertir respuesta del SDK al modelo de dominio."""

        return VolumeInfo(
            name=response.name,
            catalog_name=response.catalog_name,
            schema_name=response.schema_name,
            full_name=response.full_name,
            volume_type=response.volume_type,
            storage_location=response.storage_location,
            owner=response.owner,
            comment=response.comment,
            volume_id=response.volume_id,
            metastore_id=response.metastore_id,
            created_at=response.created_at,
            created_by=response.created_by,
            updated_at=response.updated_at,
            updated_by=response.updated_by,
        )