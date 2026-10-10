# Explicación paso a paso: `manifiesto/service.py`

> **Actualización:** las tablas vuelven a crearse por SQL en un SQL Warehouse,
> pero la lógica ahora vive en `TableService.create_with_sql` (tables/service.py):
> `build_create_sql`, `_quote`, `_literal` y la ejecución del `statement`.
> `_create_table` solo verifica existencia y delega en ese método.
> Las secciones 10 a 13 describen ese código, que se movió de archivo; `ManifestService`
> sigue recibiendo `warehouse_id` y se lo pasa a `TableService`.
> Los grants usan `GrantService.grant` (Grants API).

Este documento recorre el código como una **prueba de escritorio**: se toma un
manifiesto de ejemplo, se ejecuta mentalmente cada método y se anotan los
valores de las variables en cada paso.

---

## 0. Panorama general

`ManifestService` hace dos cosas:

1. **`load()`**: lee el YAML → reemplaza `${var.x}` → valida con Pydantic → devuelve un `Manifest`.
2. **`apply()`**: recorre el `Manifest` y crea, en este orden:
   **esquemas → volúmenes → tablas → grants**.

```
manifest.yml ──load()──► Manifest ──apply()──► ApplyResult (lista de ResourceResult)
                                      │
                                      ├─ _create_schema()  → client.schemas
                                      ├─ _create_volume()  → VolumeService
                                      ├─ _create_table()   → SQL (warehouse)
                                      └─ _apply_grant()    → SQL (warehouse)
```

Regla clave: **cada recurso se ejecuta dentro de `_run()`**, que atrapa los
errores. Un recurso que falla **no detiene** a los demás.

---

## 1. Datos de ejemplo para la prueba de escritorio

Manifiesto (resumido, con `schema` agregado a los volúmenes porque `target.schema` no existe):

```yaml
target:
  catalog: cat_test            # sin "schema"

infrastructure:
  schemas:
    - { name: sq_config, comment: "Objetos de configuración y control" }
    - { name: sq_bronze, comment: "Capa Bronze" }
    - { name: sq_silver, comment: "Capa Silver" }

  volumes:
    - { name: carga,  schema: sq_config, type: MANAGED }
    - { name: salida, schema: sq_config, type: MANAGED }

  tables:
    - name: tabla_01
      schema: sq_silver
      comment: Tabla principal
      columns:
        - { name: id,     type: BIGINT,    nullable: false }
        - { name: nombre, type: STRING,    nullable: false }
        - { name: fecha,  type: TIMESTAMP, nullable: false }
      properties: { delta.enableChangeDataFeed: "true" }

  grants:
    - object_type: TABLE
      object: tabla_01
      principal: grupo_datos
      privileges: [SELECT, MODIFY]
```

Ejecución supuesta:

```python
svc = ManifestService(WorkspaceClient(), warehouse_id="wh-123")
m   = svc.load("resources/manifest.yml", {})
res = svc.apply(m, dry_run=False)
```

> Si no se agrega `schema` a los volúmenes, `load()` falla en la validación
> (ver paso 3.4).

---

## 2. Constantes e imports

| Elemento | Qué hace |
|---|---|
| `_VAR_PATTERN = r"\$\{var\.([A-Za-z0-9_]+)\}"` | Detecta `${var.nombre}` y captura `nombre` en el grupo 1. |
| `_IDENTIFIER_PATTERN = r"^[A-Za-z0-9_]+$"` | Solo letras, números y `_`. Se usa para validar nombres antes de armar SQL. |
| `NotFound` | Excepción del SDK cuando un recurso no existe. Se usa para decidir "crear o no". |
| `StatementState` | Enum con los estados de una sentencia SQL (`SUCCEEDED`, `FAILED`...). |

---

## 3. `__init__` y `load()`

### 3.1 `__init__(client, warehouse_id)`

| Atributo | Valor en el ejemplo |
|---|---|
| `self.client` | el `WorkspaceClient` |
| `self.warehouse_id` | `"wh-123"` |
| `self.volume_service` | `VolumeService(client)` |

### 3.2 `load(path, variables)` — paso a paso

| # | Línea | Valor / resultado |
|---|---|---|
| 1 | `path = Path(path)` | `Path("resources/manifest.yml")` |
| 2 | `if not path.is_file()` | Si no existe → `FileNotFoundError("No existe el manifiesto: ...")` |
| 3 | `yaml.safe_load(...) or {}` | `raw` = diccionario de Python con todo el YAML. El `or {}` evita `None` si el archivo está vacío. |
| 4 | `_resolve_variables(raw, variables or {})` | Recorre el diccionario y reemplaza `${var.x}` (ver 3.3). |
| 5 | `Manifest.model_validate(resolved)` | Pydantic construye y valida el objeto (ver 3.4). |

### 3.3 `_resolve_variables(value, variables)` — recursiva

Se comporta según el tipo de `value`:

| Tipo | Acción |
|---|---|
| `dict` | Devuelve un nuevo dict con la función aplicada a cada **valor**. |
| `list` | Devuelve una nueva lista aplicándola a cada elemento. |
| `str` | Aplica `_VAR_PATTERN.sub(replace, value)`. |
| otro (`bool`, `int`, `None`) | Lo devuelve igual. |

**Mini prueba** con `variables = {"catalog": "dev"}`:

| Entrada | Proceso | Salida |
|---|---|---|
| `"cat_test"` | No coincide con el patrón | `"cat_test"` |
| `"${var.catalog}"` | `match.group(1)="catalog"` → está en `variables` | `"dev"` |
| `"x_${var.catalog}_y"` | Reemplaza solo la parte coincidente | `"x_dev_y"` |
| `"${var.schema}"` | `"schema"` no está en `variables` | `ValueError("Variable sin valor: ${var.schema}...")` |
| `False` (`nullable`) | No es dict/list/str | `False` |

En el manifiesto actual **no hay variables**, así que el resultado es idéntico a `raw`.

### 3.4 Validación en `Manifest` (models.py)

Pydantic revisa tipos y además:

- Claves desconocidas → error (`extra="forbid"`).
- `_validate_schemas`: si `target.schema` **no** existe, cada volumen y tabla
  debe tener `schema`.

| Caso | Resultado |
|---|---|
| Volúmenes con `schema: sq_config` | ✅ válido |
| Volúmenes `carga` y `salida` sin `schema` y sin `target.schema` | ❌ `ValueError: Sin target.schema, cada recurso debe indicar 'schema': volumen 'carga', volumen 'salida'` |

---

## 4. `apply(manifest, dry_run)` — el flujo principal

### 4.1 Variables iniciales

| Variable | Valor |
|---|---|
| `catalog` | `"cat_test"` |
| `default_schema` | `None` (no hay `target.schema`) |
| `infra` | `manifest.infrastructure` |
| `result` | `ApplyResult()` con `resources = []` |

### 4.2 Construcción del diccionario `schemas`

Objetivo: tener **una sola entrada por esquema** (evitar crearlo dos veces) y
conservar el comentario si fue declarado.

| Paso | Código | Estado de `schemas` |
|---|---|---|
| a | `schemas = {}` | `{}` |
| b | `if default_schema:` → `None` es falso, se omite | `{}` |
| c | Recorre volúmenes y tablas con `schema` y hace `setdefault(schema, None)` | |
| c.1 | volumen `carga` → `sq_config` | `{"sq_config": None}` |
| c.2 | volumen `salida` → `sq_config` (ya existe, `setdefault` no cambia) | `{"sq_config": None}` |
| c.3 | tabla `tabla_01` → `sq_silver` | `{"sq_config": None, "sq_silver": None}` |
| d | Recorre `infra.schemas` y **sobrescribe** con el comentario | |
| d.1 | `sq_config` | `{"sq_config": "Objetos de configuración y control", "sq_silver": None}` |
| d.2 | `sq_bronze` (nuevo) | `{..., "sq_bronze": "Capa Bronze"}` |
| d.3 | `sq_silver` | `{..., "sq_silver": "Capa Silver"}` |

Resultado final:

```python
schemas = {
  "sq_config": "Objetos de configuración y control",
  "sq_silver": "Capa Silver",
  "sq_bronze": "Capa Bronze",
}
```

> El paso **c** va antes que el **d** a propósito: `setdefault` no pisa nada y
> el paso **d** sí, así el comentario declarado siempre gana.

### 4.3 Creación de esquemas

Para cada `(name, comment)` se llama a `_run(...)` con
`lambda n=name, c=comment: self._create_schema(catalog, n, c)`.

> **Por qué `n=name, c=comment`:** una lambda en un bucle captura la *variable*,
> no su valor. Sin los valores por defecto, todas verían el último `name` del
> bucle. Con `n=name` se "congela" el valor de esa vuelta.

### 4.4 Creación de volúmenes

| Vuelta | `vol.name` | `schema = vol.schema_name or default_schema` | `full_name` |
|---|---|---|---|
| 1 | `carga` | `"sq_config"` | `cat_test.sq_config.carga` |
| 2 | `salida` | `"sq_config"` | `cat_test.sq_config.salida` |

### 4.5 Creación de tablas

| Vuelta | `table.name` | `schema` | `full_name` |
|---|---|---|---|
| 1 | `tabla_01` | `"sq_silver"` | `cat_test.sq_silver.tabla_01` |

### 4.6 Grants

Un bucle por grant; todos sus privilegios se otorgan en **una sola** llamada.

| Grant | `privileges` | Acción |
|---|---|---|
| `tabla_01` / `grupo_datos` | `SELECT, MODIFY` | resolver destino → `_run(...)` |

Dentro de cada vuelta:

1. `target = self._grant_target(manifest, grant)` (ver sección 6).
2. Si lanza `ValueError`, se agrega un `ResourceResult` con `FAILED` y se hace
   `continue` (siguiente grant). **No** se llama a `_run`.
3. Si todo bien, la etiqueta es
   `"SELECT, MODIFY ON cat_test.sq_silver.tabla_01 TO grupo_datos"` y se llama a `_run`.

Finalmente `return result`.

---

## 5. `_run(kind, full_name, dry_run, action)`

Es el "envoltorio" común. Recibe una función `action` y decide qué hacer.

```
dry_run?  ──sí──► ResourceResult(PLANNED)          (no ejecuta nada)
   │
   no
   ▼
try: created = action()
        True  → CREATED
        False → EXISTS
except Exception → FAILED (detail = mensaje del error)
```

**Pruebas:**

| `dry_run` | `action()` | Resultado |
|---|---|---|
| `True` | (no se llama) | `PLANNED` |
| `False` | devuelve `True` | `CREATED` |
| `False` | devuelve `False` | `EXISTS` |
| `False` | lanza `RuntimeError("boom")` | `FAILED`, `detail="boom"` |

---

## 6. `_grant_target(manifest, grant)` — resolver el objeto del grant

Convierte `grant.object = "tabla_01"` en `"cat_test.sq_silver.tabla_01"`.

**Caso A — `object_type == SCHEMA`:** devuelve `catalog.object`
(ej. `cat_test.sq_bronze`).

**Caso B — TABLE o VOLUME:**

| Paso | Código | Valor en el ejemplo |
|---|---|---|
| 1 | `specs = infra.tables` (porque es TABLE) | lista con `tabla_01` |
| 2 | Si el grant trae `schema`, `schemas = {ese schema}` | (no trae) |
| 3 | Si no, buscar en `specs` los que se llamen igual y tomar `s.schema_name or default_schema` | `{"sq_silver"}` |
| 4 | `schemas.discard(None)` | quita `None` por si algún recurso no tenía schema | 
| 5 | Si `schemas` vacío → `ValueError("No se encontró tabla 'x' ...")` | no aplica |
| 6 | Si hay más de uno → `ValueError("'x' existe en varios schemas (...)")` | no aplica |
| 7 | `return f"{catalog}.{schemas.pop()}.{object}"` | `"cat_test.sq_silver.tabla_01"` |

**Casos de error:**

| Situación | Resultado |
|---|---|
| `object: tabla_99` (no existe) | `ValueError: No se encontró tabla 'tabla_99' en el manifiesto; indique 'schema'.` |
| `tabla_01` declarada en `sq_silver` y en `sq_bronze` | `ValueError: 'tabla_01' existe en varios schemas (sq_bronze, sq_silver); indique 'schema'.` |

---

## 7. `_apply_grant(grant, target)` y `GrantService.grant(...)`

`_apply_grant` delega en `GrantService.grant` (grants/service.py), que usa la
**Grants API** (sin SQL ni warehouse):

| Paso | Valor |
|---|---|
| `securable_type` | `"TABLE"` (`grant.object_type.value`) |
| `full_name` | `"cat_test.sq_silver.tabla_01"` |
| `changes` | `[PermissionsChange(principal="grupo_datos", add=[Privilege.SELECT, Privilege.MODIFY])]` |

Llamada final:

```python
client.grants.update(securable_type="TABLE", full_name="cat_test.sq_silver.tabla_01", changes=[...])
```

`catalog.Privilege(p)` valida cada privilegio: si no existe en el SDK lanza
`ValueError`, que `GrantService` envuelve en `RuntimeError` y `_run` convierte en `FAILED`.

Retorna `True` siempre → el reporte dice `CREATED`
(`update` con `add` es idempotente y no informa si ya existía).

---

## 8. `_create_schema(catalog, name, comment)`

| Paso | Qué pasa |
|---|---|
| 1 | `client.schemas.get(full_name="cat_test.sq_config")` |
| 2a | Si **existe** → `return False` → `EXISTS` |
| 2b | Si lanza `NotFound` → `pass` y continúa |
| 3 | `client.schemas.create(name, catalog_name, comment)` |
| 4 | `return True` → `CREATED` |

**Dos ejecuciones seguidas (idempotencia):**

| Ejecución | `get()` | Resultado |
|---|---|---|
| 1ª | `NotFound` | crea → `CREATED` |
| 2ª | encuentra el schema | `EXISTS` |

---

## 9. `_create_volume(catalog, schema, spec)`

1. `client.volumes.read(name="cat_test.sq_config.carga")`
   - existe → `False` (`EXISTS`)
   - `NotFound` → continúa.
2. Llama a `VolumeService.create(VolumeCreate(...))` con:

| Campo | Valor |
|---|---|
| `catalog_name` | `cat_test` |
| `schema_name` | `sq_config` |
| `name` | `carga` |
| `volume_type` | `MANAGED` |
| `storage_location` | `None` |
| `comment` | `"Archivos de entrada"` |

3. `return True` → `CREATED`.

---

## 10. `_create_table(catalog, schema, spec)`

| Paso | Qué pasa |
|---|---|
| 1 | Sin `warehouse_id` → `ValueError("Se requiere un warehouse_id para crear tablas.")` |
| 2 | `client.tables.get("cat_test.sq_silver.tabla_01")`: existe → `False`; `NotFound` → sigue |
| 3 | `sql = _build_create_table(...)` |
| 4 | `_execute_sql(sql)` |
| 5 | `return True` |

---

## 11. `_build_create_table` — construcción del SQL

### 11.1 Columnas

Para cada columna se arma `line` así:

| Columna | `line` inicial | `nullable=False` | `comment` | Resultado |
|---|---|---|---|---|
| `id` BIGINT | `` `id` BIGINT `` | + ` NOT NULL` | no | `` `id` BIGINT NOT NULL `` |
| `nombre` STRING | `` `nombre` STRING `` | + ` NOT NULL` | no | `` `nombre` STRING NOT NULL `` |
| `fecha` TIMESTAMP | `` `fecha` TIMESTAMP `` | + ` NOT NULL` | no | `` `fecha` TIMESTAMP NOT NULL `` |

Una columna con `nullable` por defecto (`true`) no lleva `NOT NULL`
(ej. `descripcion STRING` de `tabla_02`).

### 11.2 Cuerpo

```
"CREATE TABLE IF NOT EXISTS `cat_test`.`sq_silver`.`tabla_01` (\n"
+ ",\n".join(columns)
+ "\n)"
```

### 11.3 Partes opcionales

| Condición | Se agrega |
|---|---|
| `spec.comment` | `\nCOMMENT 'Tabla principal'` |
| `spec.properties` | `\nTBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')` |

### 11.4 SQL final

```sql
CREATE TABLE IF NOT EXISTS `cat_test`.`sq_silver`.`tabla_01` (
  `id` BIGINT NOT NULL,
  `nombre` STRING NOT NULL,
  `fecha` TIMESTAMP NOT NULL
)
COMMENT 'Tabla principal'
TBLPROPERTIES ('delta.enableChangeDataFeed' = 'true')
```

---

## 12. Seguridad SQL: `_quote` y `_literal`

### `_quote(identifier)` — nombres de objetos

| Entrada | Resultado |
|---|---|
| `tabla_01` | `` `tabla_01` `` |
| `mi-tabla` | `ValueError: Identificador no válido: 'mi-tabla'` |
| ``a`; DROP TABLE x`` | `ValueError` (impide inyección SQL) |

### `_literal(value)` — textos (comentarios, propiedades)

Escapa `\` y `'`:

| Entrada | Resultado |
|---|---|
| `Tabla principal` | `'Tabla principal'` |
| `It's` | `'It\'s'` |
| `a\b` | `'a\\b'` |

### `_quote_principal(principal)`

Solo prohíbe el carácter `` ` ``. Permite correos y guiones
(`usuario@empresa.com`, `grupo-datos`), a diferencia de `_quote`.

---

## 13. `_execute_sql(statement)`

1. `execute_statement(warehouse_id, statement, wait_timeout="50s")`
   → espera hasta 50 s a que termine.
2. Toma `status = response.status`.
3. Si `status` es `None` **o** `status.state != SUCCEEDED` → lanza
   `RuntimeError(mensaje)`.

| `status.state` | `status.error` | Resultado |
|---|---|---|
| `SUCCEEDED` | — | termina sin error |
| `FAILED` | `message="PERMISSION_DENIED"` | `RuntimeError("PERMISSION_DENIED")` |
| `PENDING` (superó los 50 s) | `None` | `RuntimeError("estado StatementState.PENDING")` |

Ese `RuntimeError` lo atrapa `_run` y lo convierte en `FAILED`.

---

## 14. Resultado completo de la prueba de escritorio

Primera ejecución (`dry_run=False`, nada existe):

| # | Tipo | Recurso | Estado |
|---|---|---|---|
| 1 | schema | cat_test.sq_config | created |
| 2 | schema | cat_test.sq_silver | created |
| 3 | schema | cat_test.sq_bronze | created |
| 4 | volume | cat_test.sq_config.carga | created |
| 5 | volume | cat_test.sq_config.salida | created |
| 6 | table | cat_test.sq_silver.tabla_01 | created |
| 7 | grant | SELECT ON cat_test.sq_silver.tabla_01 TO grupo_datos | created |
| 8 | grant | MODIFY ON cat_test.sq_silver.tabla_01 TO grupo_datos | created |

Segunda ejecución inmediata: las filas 1–6 pasan a **exists**; los grants
siguen en **created**.

Con `dry_run=True`: todas las filas salen **planned** y no se llama a
Databricks (ni siquiera se valida el `warehouse_id`).

---

## 15. Resumen de decisiones de diseño

| Decisión | Motivo |
|---|---|
| `_run` atrapa todas las excepciones | Un fallo no impide crear el resto. |
| Orden esquemas → volúmenes → tablas → grants | Cada paso depende del anterior. |
| Verificar existencia con `get`/`read` + `NotFound` | Hace el proceso idempotente. |
| Tablas y grants por SQL | El SDK/servicio actual no soporta columnas ni grants sobre tablas/volúmenes. |
| `_quote` con lista blanca de caracteres | Evita inyección SQL en nombres. |
| Lambdas con `n=name` | Capturan el valor de cada vuelta del bucle. |
