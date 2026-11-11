"""
Módulo generador de datos sintéticos con Faker (es_CO) para el pipeline ETL.
Alineado con las validaciones de EmpresaRequestDTO en Spring Boot.
"""

import random
from typing import Any, Dict, List
from faker import Faker
import pandas as pd

# Inicialización de Faker con configuración regional colombiana
fake = Faker("es_CO")

# Valores válidos del enum SectorEconomico en el backend de Spring Boot
SECTORES_ECONOMICOS: List[str] = [
    "TECNOLOGIA_Y_SOFTWARE",
    "GASTRONOMIA_Y_TURISMO",
    "MANUFACTURA_E_INDUSTRIA",
    "COMERCIO_Y_RETAIL",
    "SERVICIOS_FINANCIEROS",
    "SALUD_Y_BIENESTAR",
    "EDUCACION",
    "LOGISTICA_Y_TRANSPORTE",
    "OTRO",
]


def generar_empresas(cantidad: int = 10) -> List[Dict[str, Any]]:
    """
    Genera una lista de diccionarios con datos sintéticos de empresas colombianas.
    Los campos coinciden con el contrato JSON de `EmpresaRequestDTO` en Spring Boot.

    Args:
        cantidad (int): Número de registros de empresas a generar.

    Returns:
        List[Dict[str, Any]]: Lista de diccionarios lista para convertirse en un DataFrame de Pandas.

    Raises:
        ValueError: Si la cantidad solicitada es menor o igual a cero.
    """
    if cantidad <= 0:
        raise ValueError("La cantidad de empresas a generar debe ser mayor a 0.")

    empresas: List[Dict[str, Any]] = []

    for _ in range(cantidad):
        nit_base = fake.unique.random_number(digits=9, fix_len=True)
        digito_verificacion = random.randint(0, 9)

        empresa: Dict[str, Any] = {
            "nit": f"{nit_base}-{digito_verificacion}",
            "nombre": fake.company()[:150],
            "sector": random.choice(SECTORES_ECONOMICOS),
            "contactoNombre": fake.name()[:150],
            "correo": fake.unique.company_email()[:150],
            "telefono": fake.phone_number()[:30],
        }
        empresas.append(empresa)

    return empresas


def convertir_a_dataframe(registros: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Convierte la lista de diccionarios generada en un DataFrame de Pandas
    para las fases posteriores de ensuciamiento, perfilado y limpieza.

    Args:
        registros (List[Dict[str, Any]]): Datos crudos generados con Faker.

    Returns:
        pd.DataFrame: DataFrame estructurado listo para transformaciones ETL.
    """
    return pd.DataFrame(registros)


if __name__ == "__main__":
    # Prueba rápida de generación y conversión a DataFrame
    datos_muestra = generar_empresas(5)
    df_empresas = convertir_a_dataframe(datos_muestra)
    print("Muestra de empresas generadas (es_CO):")
    print(df_empresas.to_string(index=False))

