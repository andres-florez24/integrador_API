"""
Rutas analíticas para exponer KPIs y métricas reales calculadas con Pandas hacia el Frontend en React.
"""

from datetime import datetime, timezone
import os
from typing import Any, Dict, List, Optional, Tuple
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import requests
from requests.exceptions import RequestException

from api.services.kpi_calculator import calcular_top_empresas, calcular_resumen_landing
from etl.seeder import obtener_token

router = APIRouter(
    tags=["Analytics & KPIs"],
)

SPRING_BASE_URL: str = os.getenv("SPRING_API_URL", "http://localhost:8080")
ADMIN_EMAIL: str = os.getenv("SEED_ADMIN_EMAIL", "admin.conecta@cesde.edu.co")
ADMIN_PASSWORD: str = os.getenv("SEED_ADMIN_PASSWORD", "Cesde2026*")


class CompanyMetricItem(BaseModel):
    """Modelo de respuesta para el KPI de empresas con mayor participación."""

    empresa_id: str = Field(..., description="UUID de la empresa en Spring Boot")
    nombre: str = Field(..., description="Razón social o nombre comercial")
    sector: str = Field(..., description="Sector económico según enum SectorEconomico")
    total_retos: int = Field(..., ge=0, description="Cantidad total de retos publicados")
    retos_finalizados: int = Field(..., ge=0, description="Cantidad de retos cumplidos/finalizados")
    tasa_cumplimiento: float = Field(..., ge=0.0, le=100.0, description="Porcentaje de éxito (%)")
    dias_promedio_resolucion: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        description="Tiempo promedio de duración/resolución de retos en días",
    )


class TopCompaniesResponse(BaseModel):
    """Estructura JSON estandarizada lista para graficar en React (Recharts/Chart.js)."""

    kpi: str
    fuente_datos: str = Field(..., description="Origen de los datos ('spring_boot_live' o 'synthetic_simulation')")
    generado_en: str
    total_empresas_evaluadas: int
    data: List[CompanyMetricItem]


def _obtener_datos_frescos() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], str]:
    """
    Consulta en vivo los endpoints `/api/empresas` y `/api/retos` de Spring Boot (Puerto 8080).
    Desactiva el fallback sintético de Faker: si la autenticación o la petición HTTP falla,
    imprime la causa real en consola y lanza HTTPException 502 Bad Gateway.
    """
    try:
        token = obtener_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        if not token:
            msg_auth = (
                f"Fallo de autenticación contra {SPRING_BASE_URL}/api/v1/auth/login "
                f"con el usuario '{ADMIN_EMAIL}'."
            )
            print(f"[ERROR Analytics -> Spring Boot] {msg_auth}")
            raise HTTPException(
                status_code=502,
                detail=f"Error de conexión con el Backend Core: {msg_auth}",
            )

        with requests.Session() as session:
            session.headers.update(
                {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                }
            )
            resp_empresas = session.get(f"{SPRING_BASE_URL}/api/empresas", timeout=5)
            resp_retos = session.get(f"{SPRING_BASE_URL}/api/retos", timeout=5)

            if not resp_empresas.ok:
                msg_emp = (
                    f"GET /api/empresas respondió HTTP {resp_empresas.status_code}: "
                    f"{resp_empresas.text}"
                )
                print(f"[ERROR Analytics -> Spring Boot] {msg_emp}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Error de conexión con el Backend Core ({msg_emp})",
                )

            if not resp_retos.ok:
                msg_ret = (
                    f"GET /api/retos respondió HTTP {resp_retos.status_code}: "
                    f"{resp_retos.text}"
                )
                print(f"[ERROR Analytics -> Spring Boot] {msg_ret}")
                raise HTTPException(
                    status_code=502,
                    detail=f"Error de conexión con el Backend Core ({msg_ret})",
                )

            empresas_bd: List[Dict[str, Any]] = resp_empresas.json()
            retos_bd: List[Dict[str, Any]] = resp_retos.json()

            return retos_bd, empresas_bd, "spring_boot_live"

    except HTTPException:
        raise
    except RequestException as exc:
        print(
            f"[ERROR CRÍTICO Analytics -> Spring Boot] No se pudo conectar a "
            f"{SPRING_BASE_URL}: {exc}"
        )
        raise HTTPException(
            status_code=502,
            detail=f"Error de conexión con el Backend Core en {SPRING_BASE_URL}: {exc}",
        ) from exc
    except Exception as exc:
        print(f"[ERROR INESPERADO Analytics] {exc}")
        raise HTTPException(
            status_code=502,
            detail=f"Error inesperado al procesar datos del Backend Core: {exc}",
        ) from exc


@router.get(
    "/top-companies",
    response_model=TopCompaniesResponse,
    summary="Obtener el Top de empresas calculado dinámicamente con Pandas",
)
def get_top_companies(
    limit: int = Query(default=10, ge=1, le=50, description="Cantidad máxima de empresas en el ranking"),
) -> TopCompaniesResponse:
    """
    Obtiene los datos frescos de Retos y Empresas, los procesa mediante operaciones
    vectorizadas en Pandas (`kpi_calculator.py`) y retorna el JSON listo para React.
    """
    retos_raw, empresas_raw, fuente = _obtener_datos_frescos()

    resultados_calculados: List[Dict[str, Any]] = calcular_top_empresas(
        retos_raw=retos_raw,
        empresas_raw=empresas_raw,
        top_n=limit,
    )

    metric_items: List[CompanyMetricItem] = [
        CompanyMetricItem(**item) for item in resultados_calculados
    ]

    return TopCompaniesResponse(
        kpi="top_empresas_por_retos",
        fuente_datos=fuente,
        generado_en=datetime.now(timezone.utc).isoformat(),
        total_empresas_evaluadas=len(metric_items),
        data=metric_items,
    )


@router.get(
    "/resumen",
    summary="Resumen estadístico de retos por categoría y estado para la Landing Page",
)
def get_analytics_resumen() -> Dict[str, Any]:
    """
    Endpoint consumido por `LandingAnalyticsSection.jsx` en la Landing Page pública.
    Retorna conteos por categoría académica (BarChart) y distribución por estado (PieChart).
    """
    retos_raw, empresas_raw, fuente = _obtener_datos_frescos()
    resumen = calcular_resumen_landing(retos_raw=retos_raw, empresas_raw=empresas_raw)
    return {
        "kpi": "resumen_ecosistema_landing",
        "fuente_datos": fuente,
        "generado_en": datetime.now(timezone.utc).isoformat(),
        **resumen,
    }
