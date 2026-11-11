"""
Módulo de carga (Load) del pipeline ETL para poblar el backend de Spring Boot.
Autentica vía JWT y reutiliza conexiones TCP mediante `requests.Session()`.
"""

import os
from typing import Any, Dict, List, Optional
import requests
from requests.exceptions import RequestException, HTTPError

from etl.generator import generar_empresas

# Configuración de endpoints del Backend Central en Spring Boot
SPRING_BASE_URL: str = os.getenv("SPRING_API_URL", "http://localhost:8080")
AUTH_LOGIN_URL: str = f"{SPRING_BASE_URL}/api/v1/auth/login"
EMPRESAS_URL: str = f"{SPRING_BASE_URL}/api/empresas"


def obtener_token(email: str, password: str) -> Optional[str]:
    """
    Autentica contra el endpoint de login de Spring Boot y extrae el token JWT.

    Args:
        email (str): Correo electrónico del usuario registrado (ej. ADMIN_UNIVERSIDAD).
        password (str): Contraseña en texto plano del usuario.

    Returns:
        Optional[str]: El token JWT si la autenticación es exitosa, o None si falla.
    """
    payload: Dict[str, str] = {
        "email": email,
        "password": password,
    }

    try:
        response = requests.post(
            AUTH_LOGIN_URL,
            json=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=10,
        )
        response.raise_for_status()

        data: Dict[str, Any] = response.json()
        # AuthResponseDTO en Spring Boot retorna el token en la llave 'accessToken' (o 'token')
        token: Optional[str] = data.get("accessToken") or data.get("token")

        if not token:
            print("[ERROR Auth] La respuesta de login no contenía 'accessToken' ni 'token'.")
            return None

        return token

    except HTTPError as http_err:
        detalle_error: str = ""
        if http_err.response is not None:
            detalle_error = http_err.response.text
        print(f"[ERROR HTTP en Login] Código {getattr(http_err.response, 'status_code', 'N/A')}: {detalle_error}")
        return None
    except RequestException as req_err:
        print(f"[ERROR de Conexión en Login] No se pudo conectar a {AUTH_LOGIN_URL}: {req_err}")
        return None


def poblar_empresas(empresas_data: List[Dict[str, Any]], token: str) -> List[Dict[str, Any]]:
    """
    Envía masivamente la lista de empresas hacia `POST /api/empresas` en Spring Boot.

    Por qué usamos `requests.Session()`:
    - Reutiliza la misma conexión TCP subyacente (HTTP Keep-Alive / Connection Pooling)
      hacia localhost:8080 en lugar de abrir y cerrar un socket nuevo en cada POST.
    - Persiste automáticamente los encabezados (`Authorization: Bearer <token>`,
      `Content-Type: application/json`) en todas las peticiones del lote, reduciendo
      la latencia y el consumo de CPU/red durante cargas masivas.

    Args:
        empresas_data (List[Dict[str, Any]]): Lista de diccionarios generada por `generator.py`.
        token (str): Token JWT válido con permisos para crear empresas.

    Returns:
        List[Dict[str, Any]]: Lista de empresas creadas exitosamente (con sus UUID asignados por Spring Boot).
    """
    empresas_creadas: List[Dict[str, Any]] = []
    fallidas: int = 0

    # Uso de Context Manager (with) para asegurar el cierre limpio del pool de conexiones al terminar
    with requests.Session() as session:
        session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        for idx, empresa in enumerate(empresas_data, start=1):
            nit_actual = empresa.get("nit", "SIN_NIT")
            nombre_actual = empresa.get("nombre", "SIN_NOMBRE")

            try:
                response = session.post(EMPRESAS_URL, json=empresa, timeout=10)
                response.raise_for_status()

                empresa_guardada: Dict[str, Any] = response.json()
                empresas_creadas.append(empresa_guardada)
                print(
                    f"[{idx}/{len(empresas_data)}] OK -> Empresa creada: '{nombre_actual}' "
                    f"(NIT: {nit_actual} | UUID: {empresa_guardada.get('id')})"
                )

            except HTTPError as http_err:
                fallidas += 1
                status_code = getattr(http_err.response, "status_code", "N/A")
                cuerpo_error = http_err.response.text if http_err.response is not None else str(http_err)
                print(
                    f"[{idx}/{len(empresas_data)}] FALLO HTTP {status_code} al insertar "
                    f"'{nombre_actual}' (NIT: {nit_actual}): {cuerpo_error}"
                )
            except RequestException as req_err:
                fallidas += 1
                print(
                    f"[{idx}/{len(empresas_data)}] FALLO DE RED al insertar "
                    f"'{nombre_actual}' (NIT: {nit_actual}): {req_err}"
                )

    print(
        f"\n--- Resumen de Poblado de Empresas ---\n"
        f"Total procesadas : {len(empresas_data)}\n"
        f"Exitosas         : {len(empresas_creadas)}\n"
        f"Fallidas         : {fallidas}"
    )

    return empresas_creadas


if __name__ == "__main__":
    # Credenciales iniciales sembradas por DataSeedConfig.java en Spring Boot
    ADMIN_EMAIL: str = os.getenv("SEED_ADMIN_EMAIL", "admin.conecta@cesde.edu.co")
    ADMIN_PASSWORD: str = os.getenv("SEED_ADMIN_PASSWORD", "Cesde2026*")
    CANTIDAD_EMPRESAS: int = 10

    print(f"1. Autenticando en {AUTH_LOGIN_URL} con el usuario '{ADMIN_EMAIL}'...")
    jwt_token: Optional[str] = obtener_token(ADMIN_EMAIL, ADMIN_PASSWORD)

    if not jwt_token:
        print("Abortando pipeline ETL: No fue posible obtener el token JWT.")
        raise SystemExit(1)

    print("   -> Token JWT obtenido exitosamente.\n")

    print(f"2. Generando {CANTIDAD_EMPRESAS} empresas sintéticas (es_CO)...")
    lote_empresas: List[Dict[str, Any]] = generar_empresas(CANTIDAD_EMPRESAS)

    print(f"3. Iniciando carga hacia {EMPRESAS_URL}...\n")
    poblar_empresas(lote_empresas, jwt_token)

