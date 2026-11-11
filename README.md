# 📊 CESDE Conecta — Microservicio de Datos & Analítica (`integrador_API`)

Microservicio desarrollado en **Python (FastAPI + Pandas + Faker)** que forma parte del ecosistema distribuido de la plataforma **CESDE Conecta**, integrándose con el Backend Transaccional en **Spring Boot (`:8080`)** y el Frontend en **React + Vite (`:5173`)**.

---

## 1. Descripción General del Microservicio

Este componente cumple un **doble rol estratégico** dentro de la arquitectura de software del proyecto:

1. **Misión 1 — Pipeline ETL e Inyección de Datos Sintéticos (`etl/`):**
   - Utiliza **Faker (`es_CO`)** y **Pandas** para generar datos sintéticos contextualizados a Colombia (Empresas con NIT y sectores económicos reales, Usuarios con roles institucionales/empresariales y Retos de innovación abierta con fechas consistentes).
   - Ejecuta la fase de carga (*Load*) consumiendo los endpoints REST protegidos con **JWT** del backend en Spring Boot (`http://localhost:8080`), respetando estrictamente las validaciones de los DTOs y el orden de integridad referencial (`Empresas` → `Usuarios` → `Catálogos` → `Retos`).

2. **Misión 2 — API Analítica de KPIs en Tiempo Real (`api/`):**
   - Expone endpoints RESTful ultrarrápidos sobre **FastAPI (Puerto `8000`)** que consultan los registros de negocio, los procesan mediante operaciones vectorizadas en memoria con **Pandas** y entregan estructuras **JSON puras** (sin depender de imágenes estáticas como Matplotlib).
   - Permite que el Frontend en React renderice gráficas interactivas con **Recharts** desacoplando la carga analítica del motor transaccional en Java.

---

## 2. Arquitectura de Directorios

El proyecto sigue principios de **Clean Architecture** y separación de responsabilidades:

```text
integrador_API/
├── .venv/                       # Entorno virtual aislado de Python (no versionado en Git)
├── api/                         # Capa de Exposición HTTP y Analítica (Misión 2)
│   ├── __init__.py
│   ├── main.py                  # Punto de entrada FastAPI, configuración CORS y Health Check
│   ├── routes/
│   │   ├── __init__.py
│   │   └── metrics.py           # Endpoints REST (/v1/metrics/top-companies) y esquemas Pydantic
│   └── services/
│       ├── __init__.py
│       └── kpi_calculator.py    # Motor de cálculo vectorizado con Pandas (groupby, merge)
├── etl/                         # Capa de Ingeniería de Datos y Poblado (Misión 1)
│   ├── __init__.py
│   ├── generator.py             # Generación sintética (Faker es_CO) alineada con DTOs de Java
│   └── seeder.py                # Cliente HTTP masivo con autenticación JWT y Connection Pooling
├── requirements.txt             # Dependencias declarativas del microservicio
└── README.md                    # Documentación técnica y operativa
```

---

## 3. Prerrequisitos y Configuración del Entorno

### ⚠️ Prerrequisito Crítico de Ecosistema
Antes de ejecutar el **Seeder ETL** o consultar métricas en vivo (`spring_boot_live`), asegúrate de que:
1. El motor de base de datos **MySQL** esté activo.
2. El **Backend Central en Spring Boot (`integrador_Bk_sabados20262_2`)** esté corriendo en **`http://localhost:8080`** y haya ejecutado su `DataSeedConfig` inicial (que crea el usuario administrador `admin.conecta@cesde.edu.co` y los catálogos base).

### Paso a Paso: Creación y Activación del Entorno Virtual (`.venv`)

Ubícate siempre en la raíz del microservicio:
```bash
cd integrador_API
```

#### Opción A: Windows (PowerShell)
```powershell
# 1. Crear el entorno virtual (solo si no existe la carpeta .venv)
python -m venv .venv

# 2. Activar el entorno virtual en PowerShell
.\.venv\Scripts\Activate.ps1
# (Si PowerShell bloquea la ejecución de scripts, ejecuta primero:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process)

# 3. Actualizar pip e instalar las dependencias oficiales
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### Opción B: Windows (Git Bash)
```bash
# 1. Crear el entorno virtual (solo si no existe)
python -m venv .venv

# 2. Activar el entorno virtual en Git Bash
source .venv/Scripts/activate

# 3. Instalar las dependencias
pip install -r requirements.txt
```

#### Opción C: Linux / macOS
```bash
# 1. Crear el entorno virtual
python3 -m venv .venv

# 2. Activar el entorno virtual
source .venv/bin/activate

# 3. Instalar las dependencias
pip install -r requirements.txt
```

---

## 4. Instrucciones de Ejecución

Con el entorno virtual (`.venv`) **activo** y ubicado en la raíz `integrador_API/`, puedes ejecutar cualquiera de las dos misiones:

### A. Ejecutar la Misión 1: Poblar la Base de Datos vía Spring Boot (Seeder ETL)
El script se ejecuta como módulo de Python (`-m`) para resolver correctamente las importaciones entre `etl` y `api`:

```bash
python -m etl.seeder
```

**Flujo automático que ejecuta el comando:**
1. Autentica contra `POST http://localhost:8080/api/v1/auth/login` y obtiene el `accessToken` JWT.
2. Genera e inserta **Empresas** (`POST /api/empresas`) capturando sus `UUID` reales.
3. Genera e inserta **Usuarios** (`POST /api/v1/auth/register`) asociando representantes a los `UUID` de las empresas creadas.
4. Recupera los `UUID` de Categorías y Prioridades (`GET /api/categorias`, `GET /api/prioridades`) y puebla los **Retos** (`POST /api/retos`).

---

### B. Ejecutar la Misión 2: Levantar el Servidor Analítico FastAPI (Puerto 8000)
Para iniciar el servidor ASGI con recarga en caliente (`--reload`):

```bash
uvicorn api.main:app --reload --port 8000
```

**Endpoints disponibles una vez encendido:**
| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| `GET` | `http://localhost:8000/health` | Verificación de estado del servicio (*Health Check*). |
| `GET` | `http://localhost:8000/v1/metrics/top-companies` | Ranking de empresas por volumen de retos, finalizados y tasa de cumplimiento (consumido por React). |
| `GET` | `http://localhost:8000/api/v1/metrics/top-companies` | Alias versionado del endpoint de KPIs. |
| `GET` | `http://localhost:8000/docs` | Documentación interactiva **Swagger UI** autogenerada. |

---

## 5. Consideraciones Técnicas y Decisiones de Arquitectura

### 1. ¿Por qué usamos `requests.Session()` (Connection Pooling) en `etl/seeder.py`?
Cuando el pipeline ETL inyecta decenas o cientos de registros hacia Spring Boot (`http://localhost:8080`), usar llamadas sueltas a `requests.post()` obligaría al sistema operativo a abrir un socket nuevo, realizar el *Three-Way Handshake* TCP y cerrarlo en **cada registro**:
- **Reutilización de Conexión TCP (*HTTP Keep-Alive*):** `requests.Session()` mantiene un *pool* de conexiones persistentes hacia `localhost:8080`, enviando todos los `POST` de Empresas, Usuarios y Retos sobre el mismo canal TCP abierto.
- **Inyección Centralizada del JWT:** El encabezado `Authorization: Bearer <token>` se configura una sola vez en la sesión y se propaga automáticamente a cada petición del lote, reduciendo latencia y código repetitivo.

### 2. ¿Por qué usamos Operaciones Vectorizadas de Pandas (`groupby`) en lugar de bucles `for` en `kpi_calculator.py`?
En Python estándar, recorrer listas de diccionarios con bucles `for` anidados para contar retos y promediar fechas por empresa tiene complejidad e intérprete lento debido al tipado dinámico (*boxing/unboxing* de objetos Python en cada iteración):
- **Ejecución Vectorizada en C / Cython:** Al transformar los JSON en `DataFrames`, expresiones como `(df_retos["estadoActual"] == "FINALIZADO").astype(int)` o `(fechas_fin - fechas_inicio).dt.days` operan directamente sobre bloques contiguos de memoria en bajo nivel (NumPy) sin iterar en el intérprete de Python.
- **Patrón *Split-Apply-Combine* (`groupby` + `agg`):** `df_retos.groupby("idEmpresa").agg(...)` agrupa mediante tablas hash optimizadas en C y calcula en una **única pasada** el conteo total (`count`), la suma de retos cumplidos (`sum`) y el promedio de días de resolución (`mean`), escalando de decenas a cientos de miles de registros en cuestión de milisegundos.
