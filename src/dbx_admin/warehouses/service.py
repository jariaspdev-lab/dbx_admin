from databricks.sdk import WorkspaceClient
from .models import WarehousesInfo


def _enum_value(value):
    return getattr(value, "value", value)


class WarehousesService:
    def __init__(self, client: WorkspaceClient):
        self.client = client

    @staticmethod
    def _to_info(wh) -> WarehousesInfo:
        return WarehousesInfo(
            id=wh.id,
            name=wh.name,
            state=_enum_value(wh.state),
            cluster_size=wh.cluster_size,
            warehouse_type=_enum_value(wh.warehouse_type),
            min_num_clusters=wh.min_num_clusters,
            max_num_clusters=wh.max_num_clusters,
            num_clusters=wh.num_clusters,
            auto_stop_mins=wh.auto_stop_mins,
            enable_serverless_compute=wh.enable_serverless_compute,
            creator_name=wh.creator_name,
            jdbc_url=wh.jdbc_url,
        )

    def get_list_warehouses(self) -> list[WarehousesInfo]:
        return [self._to_info(wh) for wh in self.client.warehouses.list()]

    def get(self, warehouse_id: str) -> WarehousesInfo:
        return self._to_info(self.client.warehouses.get(warehouse_id))

    def start(self, warehouse_id: str, wait: bool = False) -> WarehousesInfo:
        waiter = self.client.warehouses.start(warehouse_id)
        if wait:
            waiter.result()
        return self.get(warehouse_id)

    def stop(self, warehouse_id: str, wait: bool = False) -> WarehousesInfo:
        waiter = self.client.warehouses.stop(warehouse_id)
        if wait:
            waiter.result()
        return self.get(warehouse_id)