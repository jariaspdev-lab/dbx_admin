![Status](https://img.shields.io/badge/status-EXPERIMENTAL-9C27B0?style=for-the-badge)
![Version](https://img.shields.io/badge/version-0.1.0-1565C0?style=for-the-badge)
![Python](https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Databricks](https://img.shields.io/badge/platform-Databricks-EF3E42?style=for-the-badge&logo=databricks&logoColor=white)
![Sandbox](https://img.shields.io/badge/environment-SANDBOX-607D8B?style=for-the-badge)

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
│       ├── secrets/
│       │   ├── service.py
│       │   └── models.py
│       │
│       ├── decode/
│           ├── service.py
│           └── models.py
│
├── tests/
│
├── examples/
│
└── scripts/
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
