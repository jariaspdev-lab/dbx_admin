
## Arquitectura

``` text
dbx-admin/
│
├── pyproject.toml
├── README.md
├── .gitignore
│
├── src/
│   └── dbx_admin/
│       │
│       ├── __init__.py
│       ├── cli.py
│       │
│       ├── config/
│       │   ├── settings.py
│       │   └── environments.py
│       │
│       ├── clients/
│       │   └── databricks.py
│       │
│       ├── secrets/
│       │   ├── service.py
│       │   └── models.py
│       │
│       ├── jobs/
│       │   └── service.py
│       │
│       ├── catalog/
│       │   └── service.py
│       │
│       ├── volumes/
│       │   └── service.py
│       │
│       ├── apps/
│       │   └── service.py
│       │
│       └── permissions/
│           └── service.py
│
├── tests/
│   ├── test_secrets.py
│   └── test_config.py
│
├── examples/
│   └── secrets.yaml
│
└── scripts/
    └── dev.ps1
```

## Ejecucion

### 1 Instalacion aplicacion

```powershell
pip install -e .
```

### 2 Utilizar aplicacion

```powershell
dbx-admin --help
```

obtendras algo como:

```powershell
Usage: dbx-admin [OPTIONS] COMMAND [ARGS]...

Herramientas de administración para Databricks.

Commands:
  secrets
```

### 3 Utilizar aplicacion con secrets

```powershell
dbx-admin secrets --help
```

obtendras algo como:

```powershell
Commands:
  create
  list
  validate
```

### 4 Ejemplos

#### * Listar

```powershell
dbx-admin secrets list --scope secrets-scope-01
```

#### * Crear

```powershell
dbx-admin secrets create --scope mi-scope --key oracle-user --value "usuario_oracle"
```

#### * Validar

```powershell
dbx-admin secrets validate --scope secrets-scope-01 --key oracle-password
```

#### * Consultar

```powershell
dbx-admin secrets get --scope secrets-scope-01 --key oracle-password
```

Una mejora que haría desde el principio

Hay una cosa que cambiaría respecto a la estructura inicial: aprovecharía tu archivo:

```text
clients/
└── databricks.py
```

para que cli.py no tenga que conocer cómo se autentica Databricks.

Quedaría:

```text
cli.py
   │
   ▼
SecretService
   │
   ▼
DatabricksClient
   │
   ▼
Databricks SDK
```

Así posteriormente puedes hacer:

```powershell
dbx-admin --profile dev secrets list --scope ...
```

o:

```powershell
dbx-admin --profile prod secrets list --scope ...
```
