from databricks.sdk import WorkspaceClient

class WarehouseService:
    def __init__(self, client: WorkspaceClient):
        self.client = client

    def get_list_warehouses(self):
        response = self.client.warehouses.list()
        return response