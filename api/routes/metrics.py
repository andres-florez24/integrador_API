"""
Rutas analíticas para exponer KPIs y métricas hacia el Frontend en React.
"""

from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/api/v1/metrics",
    tags=["Analytics & KPIs"],
)


class CompanyMetricItem(BaseModel):
    """Modelo de respuesta para el KPI de empresas con mayor participación."""

    empresa_id: str = Field(..., description="UUID de la empresa en Spring Boot")
    nombre: str = Field(..., description="Razón social o nombre comercial")
    sector: str = Field(..., description="Sector económico según enum SectorEconomico")
    total_retos: int = Field(..., ge=0, description="Cantidad total de retos publicados")
    retos_finalizados: int = Field(..., ge=0, description="Cantidad de retos cumplidos/finalizados")
    tasa_cumplimiento: float = Field(..., ge=0.0, le=100.0, description="Porcentaje de éxito (%)")


class TopCompaniesResponse(BaseModel):
    """Estructura JSON estandarizada lista para graficar en React (Recharts/Chart.js)."""

    kpi: str
    generado_en: str
    total_empresas_evaluadas: int
    data: List[CompanyMetricItem]


@router.get(
    "/top-companies",
    response_model=TopCompaniesResponse,
    summary="Obtener el Top de empresas con más retos y mejor cumplimiento",
)
def get_top_companies() -> TopCompaniesResponse:
    """
    Retorna un JSON estructurado con las empresas líderes en formulación de retos.
    Diseñado para ser consumido directamente por componentes de gráficas en React
    sin depender de renderizado estático (Matplotlib).
    """
    mock_data: List[CompanyMetricItem] = [
        CompanyMetricItem(
            empresa_id="a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
            nombre="Pragma S.A.",
            sector="TECNOLOGIA_Y_SOFTWARE",
            total_retos=14,
            retos_finalizados=11,
            tasa_cumplimiento=78.57,
        ),
        CompanyMetricItem(
            empresa_id="b2c3d4e5-f6a7-4b6c-9d0e-1f2a3b4c5d6e",
            nombre="Grupo Éxito",
            sector="COMERCIO_Y_RETAIL",
            total_retos=10,
            retos_finalizados=8,
            tasa_cumplimiento=80.0,
        ),
        CompanyMetricItem(
            empresa_id="c3d4e5f6-a7b8-4c7d-8e1f-2a3b4c5d6e7f",
            nombre="Bancolombia",
            sector="SERVICIOS_FINANCIEROS",
            total_retos=9,
            retos_finalizados=7,
            tasa_cumplimiento=77.78,
        ),
        CompanyMetricItem(
            empresa_id="d4e5f6a7-b8c9-4d8e-9f2a-3b4c5d6e7f8a",
            nombre="Coordinadora Mercantil",
            sector="LOGISTICA_Y_TRANSPORTE",
            total_retos=6,
            retos_finalizados=5,
            tasa_cumplimiento=83.33,
        ),
    ]

    return TopCompaniesResponse(
        kpi="top_empresas_por_retos",
        generado_en=datetime.now(timezone.utc).isoformat(),
        total_empresas_evaluadas=len(mock_data),
        data=mock_data,
    )

