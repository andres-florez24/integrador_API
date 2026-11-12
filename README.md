# 📊 CESDE Conecta — Motor de Analítica & ETL (`integrador_API`)

Microservicio desarrollado en **Python (FastAPI + Pandas + Faker)** que forma parte del ecosistema distribuido de **CESDE Conecta**, integrándose con el **Backend Core en Spring Boot (`:8080`)** y el **Frontend Web en React + Vite (`:5173`)**.

---

## 1. Descripción General del Microservicio

Este componente cumple un **doble rol estratégico** dentro de la arquitectura del proyecto:

1. **Misión 1 — Pipeline ETL e Inyección de Datos Sintéticos (`etl/`):**
   - Utiliza **Faker (`es_CO`)** y **Pandas** para generar datos sintéticos contextualizados a Colombia (Empresas con NIT y sectores económicos reales, Usuarios con roles institucionales/empresariales y Retos de innovación abierta con fechas consistentes).
   - Ejecuta la fase de carga (*Load*) consumiendo los endpoints REST protegidos con **JWT** del backend en Spring Boot (`http://localhost:8080`), respetando estrictamente las validaciones de los DTOs y el orden de integridad referencial (`Empresas` → `Usuarios` → `Catálogos` → `Retos`).

2. **Misión 2 — API Analítica de KPIs en Tiempo Real (`api/`):**
   - Expone endpoints RESTful sobre **FastAPI (Puerto `8000`)** que consultan los registros de negocio en vivo desde Spring Boot, los procesan mediante operaciones vectorizadas en memoria con **Pandas** y entregan estructuras **JSON puras** listas para graficar en React con **Recharts**.

---

## 2. Arquitectura de Directorios

```text
integrador_API/
├── venv/                        # Entorno virtual aislado de Python
├── api/                         # Capa de Exposición HTTP y Analítica (Misión 2)
│   ├── __init__.py
│   ├── main.py                  # Punto de entrada FastAPI, configuración CORS y Health Check
│   ├── routes/
│   │   ├── __init__.py
│   │   └── metrics.py           # Endpoints REST (/api/v1/metrics/dashboard, /api/analytics/resumen)
│   └── services/
│       ├── __init__.py
│       └── kpi_calculator.py    # Motor de cálculo vectorizado con Pandas (groupby, value_counts)
├── etl/                         # Capa de Ingeniería de Datos y Poblado (Misión 1)
│   ├── __init__.py
│   ├── generator.py             # Generación sintética (Faker es_CO) alineada con DTOs de Java
│   └── seeder.py                # Cliente HTTP masivo con autenticación JWT y Connection Pooling
├── requirements.txt             # Dependencias declarativas del microservicio
└── README.md                    # Documentación técnica y operativa
```

---

## 3. Prerrequisitos y Configuración del Entorno

### ⚠️ Orden de Encendido del Ecosistema
Antes de ejecutar el **Seeder ETL** o consultar métricas en vivo, asegúrate de que:
1. El motor de base de datos **MySQL (`:3306`)** esté activo con la base de datos `proyecta_db`.
2. El **Backend Central en Spring Boot (`integrador_Bk_sabados20262_2`)** esté corriendo en **`http://localhost:8080`** y haya ejecutado su `DataSeedConfig` inicial.

### Paso a Paso: Creación del Entorno Virtual e Instalación

Ubícate en la carpeta del microservicio:

```bash
cd integrador_API

# 1. Crear el entorno virtual
python -m venv venv

# 2. Activar el entorno virtual:
# En Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# En Windows (CMD):
venv\Scripts\activate.bat
# En Linux / macOS / Git Bash:
source venv/bin/activate

# 3. Instalar las librerías requeridas
pip install fastapi "uvicorn[standard]" pandas faker requests pydantic mysql-connector-python
# O mediante el archivo de requisitos:
pip install -r requirements.txt
```

---

## 4. Instrucciones de Ejecución

### A. Ejecutar el Pipeline ETL (Poblado de Base de Datos)
Con Spring Boot activo en `http://localhost:8080`, ejecuta:

```bash
python -m etl.seeder
```

### B. Levantar el Servidor Analítico FastAPI (`Puerto 8000`)

```bash
# Desde la raíz de integrador_API:
uvicorn api.main:app --reload --port 8000

# O desde dentro de la carpeta integrador_API/api:
uvicorn main:app --reload --port 8000
```

### Endpoints Disponibles

| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| `GET` | `http://localhost:8000/health` | Verificación de estado del servicio (*Health Check*). |
| `GET` | `http://localhost:8000/api/v1/metrics/dashboard` | KPIs ejecutivos completos: retos por estado, retos por categoría, retos por sector y top empresas. |
| `GET` | `http://localhost:8000/api/analytics/resumen` | Endpoint consumido por la Landing Page pública de React (`LandingAnalyticsSection.jsx`). |
| `GET` | `http://localhost:8000/v1/metrics/top-companies` | Ranking de empresas aliadas por volumen de retos y tasa de cumplimiento. |
| `GET` | `http://localhost:8000/docs` | Documentación interactiva **Swagger UI** autogenerada. |

---

## 5. Credenciales de Prueba del Ecosistema

| Rol | Correo Electrónico (`email`) | Contraseña (`password`) | Uso en el Ecosistema |
| :--- | :--- | :--- | :--- |
| **`ADMIN_UNIVERSIDAD`** | `admin.conecta@cesde.edu.co` | `Cesde2026*` | Cuenta utilizada por `etl/seeder.py` y `kpi_calculator.py` para autenticar vía JWT contra Spring Boot y consultar el 100% de los retos. |
| **`REPRESENTANTE_EMPRESA`** | `representante@techantioquia.com` | `Cesde2026*` | Representante de **Tech Antioquia SAS** para pruebas multi-tenant de empresa. |
| **`ESTUDIANTE`** | `estudiante.conecta@cesde.edu.co` | `Cesde2026*` | Cuenta de estudiante para pruebas de visualización de convocatorias abiertas. |
