"""
Servicio de cálculo analítico de KPIs utilizando operaciones vectorizadas de Pandas.
Evita iteraciones manuales (`for` loops) delegando las agregaciones al motor en C de Pandas/NumPy.
"""

from typing import Any, Dict, List
import pandas as pd


def calcular_top_empresas(
    retos_raw: List[Dict[str, Any]],
    empresas_raw: List[Dict[str, Any]],
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """
    Calcula los indicadores clave de desempeño (KPIs) por empresa a partir de listas crudas
    provenientes de Spring Boot (`GET /api/retos` y `GET /api/empresas`).

    ¿Por qué usar `groupby` y operaciones vectorizadas en lugar de bucles `for` en Python?
    -------------------------------------------------------------------------------------
    1. Vectorización en bajo nivel (SIMD / Cython):
       En un bucle `for` tradicional de Python, cada iteración verifica tipos dinámicos y crea
       objetos en memoria (alto overhead de intérprete). Pandas ejecuta las comparaciones,
       fechas y sumas sobre arreglos contiguos de memoria en C (vía NumPy).
    2. Split-Apply-Combine (`groupby`):
       `df.groupby("idEmpresa").agg(...)` particiona los datos en una tabla hash interna en C,
       aplica todas las funciones de agregación (`count`, `sum`, `mean`) en una sola pasada y
       combina el resultado en milisegundos, incluso con decenas de miles de retos.

    Args:
        retos_raw (List[Dict[str, Any]]): Lista de diccionarios de retos (`RetoResponseDTO`).
        empresas_raw (List[Dict[str, Any]]): Lista de diccionarios de empresas (`EmpresaResponseDTO`).
        top_n (int): Cantidad máxima de empresas a retornar ordenadas por volumen y cumplimiento.

    Returns:
        List[Dict[str, Any]]: Lista de diccionarios con la estructura exacta de `CompanyMetricItem`.
    """
    if not empresas_raw or not retos_raw:
        return []

    # 1. Conversión de listas de diccionarios JSON a DataFrames de Pandas
    df_empresas = pd.DataFrame(empresas_raw)
    df_retos = pd.DataFrame(retos_raw)

    # Normalización defensiva de nombres de columnas según DTOs de Spring Boot
    if "id" not in df_empresas.columns or "idEmpresa" not in df_retos.columns:
        return []

    df_empresas["id"] = df_empresas["id"].astype(str)
    df_retos["idEmpresa"] = df_retos["idEmpresa"].astype(str)

    # 2. Operaciones vectorizadas sobre columnas (sin bucles `for`):
    #    a) Columna booleana/entera (1 o 0) cuando el estado es exactamente 'FINALIZADO'
    df_retos["es_finalizado"] = (df_retos["estadoActual"] == "FINALIZADO").astype(int)

    #    b) Cálculo vectorizado del tiempo de resolución/duración en días (fechaFin - fechaInicio)
    fechas_inicio = pd.to_datetime(df_retos["fechaInicio"], errors="coerce")
    fechas_fin = pd.to_datetime(df_retos["fechaFin"], errors="coerce")
    df_retos["dias_duracion"] = (fechas_fin - fechas_inicio).dt.days.clip(lower=0).fillna(0)

    # 3. Agregación simultánea con Split-Apply-Combine (`groupby` + Named Aggregation)
    df_agrupado = (
        df_retos.groupby("idEmpresa", as_index=False)
        .agg(
            total_retos=("id", "count"),
            retos_finalizados=("es_finalizado", "sum"),
            dias_promedio_resolucion=("dias_duracion", "mean"),
        )
    )

    # 4. Cruce relacional en memoria (`pd.merge` equivalente a un INNER JOIN en SQL)
    df_consolidado = pd.merge(
        df_empresas[["id", "nombre", "sector"]],
        df_agrupado,
        left_on="id",
        right_on="idEmpresa",
        how="inner",
    )

    if df_consolidado.empty:
        return []

    # 5. Cálculo vectorizado de la Tasa de Cumplimiento (%) y redondeo a 2 decimales
    df_consolidado["tasa_cumplimiento"] = (
        (df_consolidado["retos_finalizados"] / df_consolidado["total_retos"]) * 100.0
    ).round(2)

    df_consolidado["dias_promedio_resolucion"] = (
        df_consolidado["dias_promedio_resolucion"].round(1)
    )

    # 6. Ordenamiento descendente por mayor cantidad de retos y mayor tasa de cumplimiento
    df_top = (
        df_consolidado.sort_values(
            by=["total_retos", "tasa_cumplimiento"],
            ascending=[False, False],
        )
        .head(top_n)
        .rename(columns={"id": "empresa_id"})
    )

    # 7. Selección de columnas que coinciden exactamente con el contrato Pydantic `CompanyMetricItem`
    columnas_salida = [
        "empresa_id",
        "nombre",
        "sector",
        "total_retos",
        "retos_finalizados",
        "tasa_cumplimiento",
        "dias_promedio_resolucion",
    ]

    return df_top[columnas_salida].to_dict(orient="records")

