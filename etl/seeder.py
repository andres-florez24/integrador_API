"""
Módulo de carga (Load) del pipeline ETL para poblar el backend de Spring Boot.
Autentica vía JWT y reutiliza conexiones TCP mediante `requests.Session()`.
"""

import os
from typing import Any, Dict, List, Optional
import requests
from requests.exceptions import RequestException, HTTPError

from etl.generator import generar_empresas, generar_usuarios, generar_retos

# Configuración de endpoints del Backend Central en Spring Boot
SPRING_BASE_URL: str = os.getenv("SPRING_API_URL", "http://localhost:8080")
AUTH_LOGIN_URL: str = f"{SPRING_BASE_URL}/api/v1/auth/login"
EMPRESAS_URL: str = f"{SPRING_BASE_URL}/api/empresas"
USUARIOS_URL: str = f"{SPRING_BASE_URL}/api/v1/auth/register"
RETOS_URL: str = f"{SPRING_BASE_URL}/api/retos"
CATEGORIAS_URL: str = f"{SPRING_BASE_URL}/api/categorias"
PRIORIDADES_URL: str = f"{SPRING_BASE_URL}/api/prioridades"


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


def obtener_ids_catalogo(url: str, token: str) -> List[str]:
    """
    Recupera los UUIDs reales de catálogos maestros (Categorías Académicas y Prioridades)
    sembrados en Spring Boot para garantizar la integridad referencial al crear Retos.
    """
    try:
        response = requests.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=10,
        )
        response.raise_for_status()
        items: List[Dict[str, Any]] = response.json()
        return [str(item["id"]) for item in items if item.get("id")]
    except RequestException as exc:
        print(f"[WARN Catálogo] No se pudieron recuperar IDs desde {url}: {exc}")
        return []


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
        f"Fallidas         : {fallidas}\n"
    )

    return empresas_creadas


def poblar_usuarios(usuarios_data: List[Dict[str, Any]], token: str) -> List[Dict[str, Any]]:
    """
    Envía masivamente la lista de usuarios hacia `POST /api/v1/auth/register` (o `/api/v1/usuarios`)
    reutilizando una única sesión TCP con `requests.Session()`.

    Args:
        usuarios_data (List[Dict[str, Any]]): Lista de diccionarios generada por `generar_usuarios`.
        token (str): Token JWT válido inyectado en la sesión.

    Returns:
        List[Dict[str, Any]]: Lista de usuarios registrados exitosamente.
    """
    usuarios_creados: List[Dict[str, Any]] = []
    fallidos: int = 0

    with requests.Session() as session:
        session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        for idx, usuario in enumerate(usuarios_data, start=1):
            email_actual = usuario.get("email", "SIN_EMAIL")
            rol_actual = usuario.get("rol", "SIN_ROL")

            try:
                response = session.post(USUARIOS_URL, json=usuario, timeout=10)
                response.raise_for_status()

                usuario_guardado: Dict[str, Any] = response.json()
                usuarios_creados.append(usuario_guardado)
                print(
                    f"[{idx}/{len(usuarios_data)}] OK -> Usuario creado: '{email_actual}' "
                    f"(Rol: {rol_actual} | UUID: {usuario_guardado.get('id')})"
                )

            except HTTPError as http_err:
                fallidos += 1
                status_code = getattr(http_err.response, "status_code", "N/A")
                cuerpo_error = http_err.response.text if http_err.response is not None else str(http_err)
                print(
                    f"[{idx}/{len(usuarios_data)}] FALLO HTTP {status_code} al insertar usuario "
                    f"'{email_actual}' (Rol: {rol_actual}): {cuerpo_error}"
                )
            except RequestException as req_err:
                fallidos += 1
                print(
                    f"[{idx}/{len(usuarios_data)}] FALLO DE RED al insertar usuario "
                    f"'{email_actual}': {req_err}"
                )

    print(
        f"\n--- Resumen de Poblado de Usuarios ---\n"
        f"Total procesados : {len(usuarios_data)}\n"
        f"Exitosos         : {len(usuarios_creados)}\n"
        f"Fallidos         : {fallidos}\n"
    )

    return usuarios_creados


def poblar_retos(retos_data: List[Dict[str, Any]], token: str) -> List[Dict[str, Any]]:
    """
    Envía masivamente la lista de retos hacia `POST /api/retos` en Spring Boot
    reutilizando la sesión HTTP autenticada con JWT (`ADMIN_UNIVERSIDAD` o `REPRESENTANTE_EMPRESA`).

    Args:
        retos_data (List[Dict[str, Any]]): Lista de diccionarios generada por `generar_retos`.
        token (str): Token JWT válido con rol autorizado para crear retos.

    Returns:
        List[Dict[str, Any]]: Lista de retos creados exitosamente en la base de datos.
    """
    retos_creados: List[Dict[str, Any]] = []
    fallidos: int = 0

    with requests.Session() as session:
        session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

        for idx, reto in enumerate(retos_data, start=1):
            nombre_reto = reto.get("nombre", "SIN_TITULO")
            estado_reto = reto.get("estadoActual", "SIN_ESTADO")

            try:
                response = session.post(RETOS_URL, json=reto, timeout=10)
                response.raise_for_status()

                reto_guardado: Dict[str, Any] = response.json()
                retos_creados.append(reto_guardado)
                print(
                    f"[{idx}/{len(retos_data)}] OK -> Reto creado: '{nombre_reto}' "
                    f"(Estado: {estado_reto} | UUID: {reto_guardado.get('id')})"
                )

            except HTTPError as http_err:
                fallidos += 1
                status_code = getattr(http_err.response, "status_code", "N/A")
                cuerpo_error = http_err.response.text if http_err.response is not None else str(http_err)
                print(
                    f"[{idx}/{len(retos_data)}] FALLO HTTP {status_code} al insertar reto "
                    f"'{nombre_reto}': {cuerpo_error}"
                )
            except RequestException as req_err:
                fallidos += 1
                print(
                    f"[{idx}/{len(retos_data)}] FALLO DE RED al insertar reto "
                    f"'{nombre_reto}': {req_err}"
                )

    print(
        f"\n--- Resumen de Poblado de Retos ---\n"
        f"Total procesados : {len(retos_data)}\n"
        f"Exitosos         : {len(retos_creados)}\n"
        f"Fallidos         : {fallidos}\n"
    )

    return retos_creados


if __name__ == "__main__":
    # Credenciales iniciales sembradas por DataSeedConfig.java en Spring Boot
    ADMIN_EMAIL: str = os.getenv("SEED_ADMIN_EMAIL", "admin.conecta@cesde.edu.co")
    ADMIN_PASSWORD: str = os.getenv("SEED_ADMIN_PASSWORD", "Cesde2026*")

    CANTIDAD_EMPRESAS: int = 10
    CANTIDAD_USUARIOS: int = 15
    CANTIDAD_RETOS: int = 20

    print(f"1. Autenticando en {AUTH_LOGIN_URL} con el usuario '{ADMIN_EMAIL}'...")
    jwt_token: Optional[str] = obtener_token(ADMIN_EMAIL, ADMIN_PASSWORD)

    if not jwt_token:
        print("Abortando pipeline ETL: No fue posible obtener el token JWT.")
        raise SystemExit(1)

    print("   -> Token JWT obtenido exitosamente.\n")

    # Paso A: Generar y poblar Empresas (Entidad Maestra)
    print(f"2. Generando y poblando {CANTIDAD_EMPRESAS} empresas sintéticas (es_CO)...")
    lote_empresas: List[Dict[str, Any]] = generar_empresas(CANTIDAD_EMPRESAS)
    empresas_persistidas: List[Dict[str, Any]] = poblar_empresas(lote_empresas, jwt_token)

    if not empresas_persistidas:
        print("Abortando pipeline ETL: No se crearon empresas para vincular usuarios y retos.")
        raise SystemExit(1)

    # Paso B: Generar y poblar Usuarios vinculados a las Empresas creadas
    print(f"3. Generando y poblando {CANTIDAD_USUARIOS} usuarios sintéticos...")
    lote_usuarios: List[Dict[str, Any]] = generar_usuarios(CANTIDAD_USUARIOS, empresas_persistidas)
    usuarios_persistidos: List[Dict[str, Any]] = poblar_usuarios(lote_usuarios, jwt_token)

    # Paso C: Obtener catálogos reales (Categorías y Prioridades) y poblar Retos
    categorias_bd: List[str] = obtener_ids_catalogo(CATEGORIAS_URL, jwt_token)
    prioridades_bd: List[str] = obtener_ids_catalogo(PRIORIDADES_URL, jwt_token)

    print(f"4. Generando y poblando {CANTIDAD_RETOS} retos de innovación...")
    lote_retos: List[Dict[str, Any]] = generar_retos(
        CANTIDAD_RETOS,
        empresas_persistidas,
        categorias_ids=categorias_bd if categorias_bd else None,
        prioridades_ids=prioridades_bd if prioridades_bd else None,
    )
    retos_persistidos: List[Dict[str, Any]] = poblar_retos(lote_retos, jwt_token)

    print("=====================================================")
    print("PIPELINE ETL COMPLETADO:")
    print(f"  - Empresas insertadas : {len(empresas_persistidas)}")
    print(f"  - Usuarios insertados : {len(usuarios_persistidos)}")
    print(f"  - Retos insertados    : {len(retos_persistidos)}")
    print("=====================================================")
