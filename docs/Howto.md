# Guía Práctica

## Desarrollo Local en Python con `pip install -e .` y Dependencias Dinámicas

Esta guía explica dos conceptos fundamentales para la gestión y creación de paquetes en Python usando las especificaciones modernas de `pyproject.toml`: la **instalación en modo editable** y la **lectura dinámica de dependencias**.

---

### 1. Utilidad de `pip install -e .`

El comando `pip install -e .` (o `pip install --editable .`) sirve para instalar un paquete Python local en **modo editable** (desarrollo).

#### ¿Cómo funciona?

En lugar de copiar los archivos del código fuente a la carpeta global del entorno (`site-packages`), `pip` crea un enlace directo (un puntero o archivo `.pth`) hacia la carpeta de tu código fuente.

#### Principales Beneficios

* **Actualización en Tiempo Real:** Cualquier modificación que realices en el código fuente de tu paquete se reflejará inmediatamente al ejecutar tus scripts o pruebas, sin necesidad de volver a ejecutar `pip install`.
* **Desarrollo Limpio:** Permite probar tu paquete como si fuera una librería externa instalada desde PyPI, validando las importaciones (`import mi_paquete`) correctamente dentro de tu entorno virtual.
* **Integración con Tests:** Facilita la ejecución de suites de prueba (como `pytest`) sobre la estructura real del proyecto instalada.

---

### 2. Uso de `setuptools` con `dynamic = ["dependencies"]`

En el estándar moderno de Python (`PEP 621`), los metadatos de un paquete se configuran dentro de `pyproject.toml`.

Por defecto, se espera que las dependencias estén escritas directamente de forma estática en el campo `dependencies = [...]`. Sin embargo, si deseas mantener un archivo `requirements.txt` existente como fuente principal, debes usar **dependencias dinámicas**.

#### ¿Qué hace `dynamic = ["dependencies"]`?

Informa a las herramientas de empaquetado que las dependencias **no están declaradas estáticamente en el `pyproject.toml`**, sino que deben ser calculadas o leídas de una fuente externa al momento de construir o instalar el paquete.

---

### 3. Configuración Paso a Paso (`pyproject.toml` + `requirements.txt`)

A continuación se muestra un ejemplo completo de cómo conectar `setuptools` con `requirements.txt`:

#### Estrategia de Archivos

```
mi_proyecto/
├── pyproject.toml
├── requirements.txt
└── mi_paquete/
    ├── __init__.py
    └── main.py
```

#### Contenido de `requirements.txt`

```text
requests>=2.28.0
pandas>=2.0.0
```

#### Contenido de `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "mi_paquete"
version = "0.1.0"
description = "Un proyecto de ejemplo con dependencias dinámicas"
readme = "README.md"
requires-python = ">=3.8"

# 1. Indicamos que las dependencias se definirán de forma dinámica
dynamic = ["dependencies"]

## 2. Le decimos a setuptools exactamente qué archivo debe leer
[tool.setuptools.dynamic]
dependencies = {file = ["requirements.txt"]}
```

---

### 4. Flujo de Trabajo Recomendado

1. **Añade las dependencias necesarias** en tu archivo `requirements.txt`.
2. **Activa tu entorno virtual** (`venv`, `conda`, etc.).
3. **Instala tu proyecto en modo editable**:

   ```bash
   pip install -e .
   ```

   *Nota: `pip` leerá el `pyproject.toml`, identificará que la lista de dependencias es dinámica, extraerá los paquetes desde `requirements.txt`, los instalará en el entorno y finalmente enlazará tu proyecto local.*

## Configuracion Git

### Identidad solo para dbx_admin

Git permite tener una identidad diferente por repositorio.

#### 1. Entra a dbx_admin

cd /ruta/donde/esta/dbx_admin

Comprueba:

```powershell
git status
```

#### 2. Configura la identidad personal SOLO para este proyecto

Por ejemplo:

```powershell
git config user.name "Juan Carlos Arevalo"
git config user.email "<tu-correo-personal@gmail.com>"
```

Esto crea la configuración dentro de:

```powershell
dbx_admin/.git/config
```

y no modifica tu identidad corporativa global.

Puedes comprobarlo:

```powershell
git config --local user.name
git config --local user.email
```

Deberías obtener:

```powershell
Juan Carlos Arevalo
<tu-correo-personal@gmail.com>
```

#### 3. Comprueba qué identidad usa Git  

Puedes ejecutar:

```powershell
git config --show-origin --get user.name
git config --show-origin --get user.email
```

Para dbx_admin debería aparecer algo parecido a:

```powershell
file:.git/config    Juan Carlos Arevalo
file:.git/config    <tu-correo-personal@gmail.com>
```

Mientras que en tus otros proyectos corporativos puede seguir apareciendo la configuración global:

```powershell
file:C:/Users/.../.gitconfig    Tu Nombre Corporativo
file:C:/Users/.../.gitconfig    <correo@empresa.com>
```

#### 4. Una recomendación importante

Si después vas a subir dbx_admin a tu Git personal, por ejemplo GitHub, GitLab, etc., hay dos cosas independientes:

Identidad del commit:

```powershell
git config user.name
git config user.email
```

Cuenta utilizada para hacer push:

```text
GitHub/GitLab personal
        ↓
   autenticación
        ↓
     git push
```

Es decir, configurar:

```powershell
git config user.email "<tu-correo-personal@gmail.com>"
``

no cambia automáticamente la cuenta con la que GitHub te autentica.

Para tu escenario yo lo dejaría así:

````texto`
                 Git global
              ┌──────────────┐
              │ Corporativo  │
              │ correo corp. │
              └──────┬───────┘
                     │
          otros proyectos corporativos


                 dbx_admin
              ┌──────────────┐
              │ Git local    │
              │ Personal     │
              │ correo pers. │
              └──────────────┘
                     │
                     ▼
              Git personal
```

Así no tienes que cambiar constantemente tu configuración global y dbx_admin queda aislado con tu identidad personal.

#### 5. Autenticacion

Sí. Aquí hay que separar **dos cosas**: quién aparece como autor de tus commits y **con qué cuenta te autenticas al hacer `push`/`pull`**.

Para `dbx_admin` personal, yo tendría en cuenta esto:

### 1. Identidad del commit

Ya la puedes dejar local al proyecto:

```bash
git config user.name "Juan Carlos Arevalo"
git config user.email "tu-correo-personal@gmail.com"
```

Esto determina quién aparece en:

```bash
git log
```

---

### 2. Autenticación contra tu Git personal

Si vas a usar **GitHub personal**, tienes dos opciones principales:

#### Opción A — SSH ⭐

Es la que te recomiendo si vas a trabajar frecuentemente.

Generas una llave:

```bash
ssh-keygen -t ed25519 -C "tu-correo-personal@gmail.com"
```

Puedes aceptar:

```text
Enter file in which to save the key:
```

con una ruta como:

```text
~/.ssh/id_ed25519_personal
```

Luego tendrás:

```text
id_ed25519_personal
id_ed25519_personal.pub
```

La **privada nunca se comparte**.

La pública (`.pub`) es la que registras en tu cuenta personal de GitHub.

Después el remoto de `dbx_admin` puede ser:

```bash
git remote add origin git@github.com:TU_USUARIO/dbx_admin.git
```

Y:

```bash
git push -u origin main
```

---

### 3. Si también tienes Git corporativo

Aquí es donde conviene tener cuidado.

Puedes tener simultáneamente:

```text
GitHub personal
    SSH → id_ed25519_personal

Azure DevOps corporativo
    SSH/HTTPS → credencial corporativa
```

Y hacer que cada repositorio utilice su correspondiente remoto.

Por ejemplo:

```bash
git remote -v
```

En `dbx_admin`:

```text
origin  git@github.com:TU_USUARIO/dbx_admin.git
```

Mientras que en tu proyecto corporativo podrías tener algo como:

```text
origin  https://...@dev.azure.com/.../...
```

No necesitas cambiar de usuario global cada vez.

---

### 4. Si eliges HTTPS

También puedes hacerlo:

```bash
git remote add origin https://github.com/TU_USUARIO/dbx_admin.git
```

Al hacer:

```bash
git push
```

GitHub ya no utiliza normalmente tu contraseña de GitHub como contraseña de Git; se utiliza autenticación mediante **token/credencial administrada por Git Credential Manager**.

En Windows, Git Credential Manager puede guardar la sesión para que no tengas que autenticarte continuamente.

---

### 5. Lo que yo haría en tu caso

Como tienes una separación clara entre **proyectos corporativos Azure DevOps** y este proyecto **personal**, configuraría:

```text
                    TU PC
                      │
          ┌───────────┴───────────┐
          │                       │
    dbx_admin                 Proyectos DIAN
     PERSONAL                 CORPORATIVOS
          │                       │
          ▼                       ▼
     GitHub personal          Azure DevOps
          │                       │
       SSH key                 Credencial
       personal               corporativa
```

Y en `dbx_admin`:

```bash
git config user.name "Juan Carlos Arevalo"
git config user.email "tu-correo-personal@gmail.com"

git remote add origin git@github.com:TU_USUARIO/dbx_admin.git
```

Así **no mezclas la identidad ni las credenciales corporativas con tu proyecto personal**.

Si me dices si tu Git personal será **GitHub, GitLab o Bitbucket**, te puedo dar los comandos exactos para configurarlo en Windows y dejar funcionando **personal + Azure DevOps corporativo simultáneamente**.
Sí, ya veo exactamente qué pasó 👍. Tienes **dos problemas independientes**:

1. El `origin` quedó apuntando literalmente a `TU_USUARIO`.
2. Tu repositorio local **todavía no tiene una rama/commit `main`**, por eso aparece `src refspec main does not match any`.

Vamos paso a paso.

### 1. Corrige el `origin`

No puedes volver a hacer `git remote add origin` porque `origin` ya existe. Cámbialo con:

```powershell
git remote set-url origin git@github.com:usuario/dbx_admin.git
```

Comprueba:

```powershell
git remote -v
```

Debe aparecer:

```text
origin  git@github.com:usuario/dbx_admin.git (fetch)
origin  git@github.com:usuario/dbx_admin.git (push)
```

---

### 2. Revisa el estado del repositorio

Ejecuta:

```powershell
git status
```

Probablemente verás algo como:

```text
No commits yet
```

o archivos sin seguimiento.

Si es así, agrega los archivos:

```powershell
git add .
```

Luego:

```powershell
git status
```

### ⚠️ Antes del commit

Como veo que estás dentro de:

```text
(.venv) PS D:\Oficina\01_proyectos\dbx-admin>
```

**asegúrate de que `.venv` esté en `.gitignore`**.

Puedes comprobar:

```powershell
Get-Content .gitignore
```

Debería contener al menos:

```gitignore
.venv/
venv/
__pycache__/
*.pyc
.env
```

Esto es importante para no subir tu entorno virtual ni posibles credenciales.

---

### 3. Crea el primer commit

```powershell
git add .
git commit -m "chore: initial commit"
```

Ahora verifica:

```powershell
git log --oneline
```

Deberías tener algo parecido a:

```text
a83f21c chore: initial commit
```

---

### 4. Asegúrate de estar en `main`

Ejecuta:

```powershell
git branch -M main
```

Y comprueba:

```powershell
git branch
```

Deberías ver:

```text
* main
```

---

### 5. Ahora sí haz el `push`

```powershell
git push -u origin main
```

Esta vez ya no debería aparecer:

```text
src refspec main does not match any
```

porque ahora tienes:

```text
main
 │
 └── commit inicial
       │
       ▼
GitHub
usuario/dbx_admin
```

### 6. Una última comprobación importante: SSH

Como estás usando:

```text
git@github.com:usuario/dbx_admin.git
```

GitHub te va a autenticar mediante **SSH**, no mediante el correo que configuraste con `git config`.

Antes del `push`, puedes probar:

```powershell
ssh -T git@github.com
```

Si todo está configurado correctamente, GitHub debería reconocerte.

---

**En resumen, ejecuta ahora esto en orden:**

```powershell
git remote set-url origin git@github.com:usuario/dbx_admin.git

git remote -v

git status

git add .
git commit -m "chore: initial commit"

git branch -M main

git push -u origin main
```

Si el `ssh -T git@github.com` te da un error, **no sigas cambiando cosas todavía**; pégame ese error y revisamos la configuración de tu llave `dbx_admin_personal` para que no se mezcle con tu acceso corporativo.

Perfecto. Eso explica la situación: tienes **dos pares de llaves SSH personales**:

```text
.ssh/
├── dbx_admin_personal
├── dbx_admin_personal.pub
├── dbx_personal
└── dbx_personal.pub
```

No hay problema en tener ambas. Lo importante ahora es saber **cuál está registrada en GitHub** y decirle a SSH cuál debe usar para `dbx_admin`.

### 1. Primero revisemos las huellas de ambas llaves

Ejecuta en PowerShell:

```powershell
ssh-keygen -lf "$env:USERPROFILE\.ssh\dbx_admin_personal.pub"
```

y:

```powershell
ssh-keygen -lf "$env:USERPROFILE\.ssh\dbx_personal.pub"
```

Obtendrás algo parecido a:

```text
256 SHA256:xxxxxxxxxxxxxxxx dbx_admin_personal
256 SHA256:yyyyyyyyyyyyyyyy dbx_personal
```

Esto nos permite distinguirlas sin mostrar las claves.

### 2. Revisa cuál está actualmente cargada

Ejecuta:

```powershell
ssh-add -l
```

Si aparece:

```text
The agent has no identities.
```

no pasa nada. Podemos configurar SSH directamente para que use la llave correcta.

### 3. Te recomiendo usar `dbx_admin_personal`

Para este proyecto:

```text
D:\Oficina\01_proyectos\dbx-admin
```

podemos hacer que GitHub utilice específicamente:

```text
C:\Users\TU_USUARIO\.ssh\dbx_admin_personal
```

Para eso podemos crear:

```text
C:\Users\TU_USUARIO\.ssh\config
```

con:

```text
Host github-dbxa
    HostName github.com
    User git
    IdentityFile ~/.ssh/dbx_admin_personal
    IdentitiesOnly yes
```

Entonces el remoto de `dbx_admin` sería:

```powershell
git remote set-url origin git@github-dbxa:usuario/dbx_admin.git
```

Y probamos:

```powershell
ssh -T git@github-dbxa
```

Esto tiene una ventaja importante: **no tocamos la configuración de tu otra llave `dbx_personal` ni la corporativa**.

### Pero antes de hacer eso

Quiero saber algo: **¿cuál de las dos llaves agregaste a GitHub?**

Puedes comprobarlo entrando a:

**GitHub → Settings → SSH and GPG keys**

y comparar las huellas (`SHA256:...`) con:

```powershell
ssh-keygen -lf "$env:USERPROFILE\.ssh\dbx_admin_personal.pub"
```

y:

```powershell
ssh-keygen -lf "$env:USERPROFILE\.ssh\dbx_personal.pub"
```

Si ninguna aparece en GitHub, simplemente agregamos `dbx_admin_personal.pub` y dejamos `dbx_personal` intacta.

Perfecto. Ese remoto está **bien configurado** para usar el alias SSH `github-dbxa`:

```text
origin  git@github-dbxa:usuario/dbx_admin.git
```

Ahora hay que separar dos cosas: **SSH** y **existencia del repositorio**.

### 1. Prueba la autenticación SSH con el mismo alias

Ejecuta:

```powershell
ssh -T git@github-dbxa
```

Si todo está correcto, deberías recibir algo como:

```text
Hi usuario! You've successfully authenticated, but GitHub does not provide shell access.
```

Eso confirmaría que `dbx_admin` está usando específicamente:

```text
dbx_admin_personal
```

### 2. Si la autenticación funciona, verifica el repositorio

Ejecuta:

```powershell
git ls-remote origin
```

Hay dos escenarios:

**Si el repositorio existe y tienes acceso**, aparecerán referencias como:

```text
a8f3...    HEAD
a8f3...    refs/heads/main
```

**Si aparece:**

```text
ERROR: Repository not found.
```

entonces el problema ya no es SSH. Significa que GitHub no encuentra:

```text
usuario/dbx_admin
```

En ese caso entra a tu GitHub personal y confirma que exista exactamente:

```text
Owner: usuario
Repository: dbx_admin
```

### 3. Si todavía no lo has creado

Créalo vacío en GitHub:

```text
usuario
└── dbx_admin
```

No marques:

* README
* `.gitignore`
* License

porque ya tienes esos elementos en tu proyecto local.

Después:

```powershell
git push -u origin main
```

### 4. Una comprobación adicional muy útil

Puedes ver qué llave está usando realmente el alias:

```powershell
ssh -G github-dbxa | Select-String "hostname|user|identityfile|identitiesonly"
```

Deberíamos ver algo parecido a:

```text
hostname github.com
user git
identityfile C:\Users\...\ .ssh\dbx_admin_personal
identitiesonly yes
```

Así confirmamos que **`dbx_admin` → GitHub personal → `dbx_admin_personal`**, sin tocar tus otras credenciales.

Si me pegas el resultado de:

```powershell
ssh -T git@github-dbxa
```

te digo cuál es exactamente el siguiente paso.
