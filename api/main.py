"""
Punto de entrada principal del microservicio Analítico y ETL - CESDE Conecta.
Puerto por defecto: 8000
"""

from typing import Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.metrics import router as metrics_router

app = FastAPI(
    title="CESDE Conecta - Analytics & Data Microservice",
    description=(
        "Microservicio de analítica avanzada y generación de datos sintéticos (ETL) "
        "integrado con Spring Boot (8080) y React/Vite (5173)."
    ),
    version="1.0.0",
)

# Configuración de orígenes permitidos (React Vite en 5173 y Backend Spring Boot en 8080)
ALLOWED_ORIGINS: list[str] = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Registro de routers modulares
app.include_router(metrics_router)


@app.get("/health", tags=["Health Check"])
def health_check() -> Dict[str, str]:
    """Endpoint de verificación de estado del microservicio."""
    return {
        "status": "UP",
        "service": "integrador_API",
        "environment": "development",
    }

