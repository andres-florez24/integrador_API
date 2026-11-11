"""
Rutas analíticas para exponer KPIs y métricas reales calculadas con Pandas hacia el Frontend en React.
"""

from datetime import datetime, timezone
import os
from typing import Any, Dict, List, Optional, Tuple
import uuid
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
import requests
from requests.exceptions import RequestException

from api.services.kpi_calculator import calcular_top_empresas
from etl.generator import generar_empresas, generar_retos
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
    Intenta consultar en vivo los endpoints `/api/empresas` y `/api/retos` de Spring Boot (Puerto 8080).
    Si el backend no está disponible o aún no tiene retos sembrados, genera un lote sintético
    en memoria con Faker para garantizar que el cálculo de Pandas siempre pueda probarse.
    """
    try:
        token = obtener_token(ADMIN_EMAIL, ADMIN_PASSWORD)
        if token:
            with requests.Session() as session:
                session.headers.update(
                    {
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                    }
                )
                resp_empresas = session.get(f"{SPRING_BASE_URL}/api/empresas", timeout=5)
                resp_retos = session.get(f"{SPRING_BASE_URL}/api/retos", timeout=5)

                if resp_empresas.ok and resp_retos.ok:
                    empresas_bd: List[Dict[str, Any]] = resp_empresas.json()
                    retos_bd: List[Dict[str, Any]] = resp_retos.json()
                    if empresas_bd and retos_bd:
                        return retos_bd, empresas_bd, "spring_boot_live"
    except RequestException:
        pass

    # Fallback: Simulación fresca en memoria si Spring Boot está apagado o vacío
    empresas_simuladas: List[Dict[str, Any]] = [
        {"id": str(uuid.uuid4()), **emp} for emp in generar_empresas(8)
    ]
    retos_simulados: List[Dict[str, Any]] = [
        {"id": str(uuid.uuid4()), **reto}
        for reto in generar_retos(35, empresas_simuladas)
    ]
    return retos_simulados, empresas_simuladas, "synthetic_simulation"


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
