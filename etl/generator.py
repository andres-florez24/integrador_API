"""
Módulo generador de datos sintéticos con Faker (es_CO) para el pipeline ETL.
Alineado con las validaciones de EmpresaRequestDTO, UsuarioRequestDTO y RetoRequestDTO en Spring Boot.
"""

from datetime import date, datetime, time, timedelta
import random
from typing import Any, Dict, List, Optional
import uuid
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

# Valores válidos del enum RolUsuario en Spring Boot
# Nota: En el backend el rol de empresa se denomina REPRESENTANTE_EMPRESA
ROLES_USUARIO: List[str] = [
    "REPRESENTANTE_EMPRESA",
    "ESTUDIANTE",
    "ADMIN_UNIVERSIDAD",
]

# Valores válidos del enum EstadoReto para el flujo de retos
ESTADOS_RETO: List[str] = [
    "EN_CONVOCATORIA",
    "EN_DESARROLLO",
    "FINALIZADO",
    "CANCELADO",
    "APLAZADO",
]

# Títulos base realistas para retos de innovación abierta
TEMAS_RETOS: List[str] = [
    "Automatización de atención al cliente con IA",
    "Dashboard predictivo de rotación de inventario",
    "Plataforma web de trazabilidad logística última milla",
    "Sistema de agendamiento digital y recordatorios omnicanal",
    "Optimización de facturación electrónica y conciliación bancaria",
    "Portal de autogestión para proveedores regionales",
    "Aplicación móvil de fidelización para comercios minoristas",
    "Integración de pasarela de pagos y billeteras digitales",
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


def generar_usuarios(
    cantidad: int,
    empresas_creadas: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Genera usuarios sintéticos respetando el contrato de `UsuarioRequestDTO` en Spring Boot.

    Reglas de integridad referencial y validación:
    - `nombreCompleto`: obligatorio, máx. 150 caracteres.
    - `email`: obligatorio, formato email válido, máx. 100 caracteres.
    - `password`: obligatorio, entre 8 y 100 caracteres.
    - `rol`: seleccionado de `ROLES_USUARIO` ("REPRESENTANTE_EMPRESA", "ESTUDIANTE", "ADMIN_UNIVERSIDAD").
    - `idEmpresa`: si el rol es "REPRESENTANTE_EMPRESA" (o "EMPRESA"), se asigna aleatoriamente
      el UUID (`id`) de una empresa existente en `empresas_creadas`; en caso contrario es `None`.

    Args:
        cantidad (int): Número de usuarios a generar.
        empresas_creadas (List[Dict[str, Any]]): Lista de empresas previamente persistidas con su `id` (UUID).

    Returns:
        List[Dict[str, Any]]: Lista de payloads de usuarios lista para enviar al backend.
    """
    if cantidad <= 0:
        raise ValueError("La cantidad de usuarios a generar debe ser mayor a 0.")

    usuarios: List[Dict[str, Any]] = []
    ids_empresas: List[str] = [
        str(emp["id"]) for emp in empresas_creadas if emp.get("id")
    ]

    for _ in range(cantidad):
        nombre_completo: str = f"{fake.first_name()} {fake.last_name()} {fake.last_name()}"[:150]
        rol_seleccionado: str = random.choice(ROLES_USUARIO)

        # Si el usuario representa a una empresa, vinculamos un UUID real de empresas_creadas
        id_empresa_asignada: Optional[str] = None
        if rol_seleccionado in ("REPRESENTANTE_EMPRESA", "EMPRESA") and ids_empresas:
            id_empresa_asignada = random.choice(ids_empresas)

        usuario: Dict[str, Any] = {
            "nombreCompleto": nombre_completo,
            "email": fake.unique.email()[:100],
            "password": fake.password(
                length=12,
                special_chars=True,
                digits=True,
                upper_case=True,
                lower_case=True,
            ),
            "rol": rol_seleccionado,
            "idEmpresa": id_empresa_asignada,
            "activo": True,
        }
        usuarios.append(usuario)

    return usuarios


def generar_retos(
    cantidad: int,
    empresas_creadas: List[Dict[str, Any]],
    categorias_ids: Optional[List[str]] = None,
    prioridades_ids: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Genera retos de innovación abierta respetando `RetoRequestDTO` y la integridad referencial.

    Reglas de validación de Spring Boot (`RetoRequestDTO`):
    - `nombre`: máx. 100 caracteres.
    - `descripcion`: texto obligatorio.
    - `fechaInicio`: LocalDate (YYYY-MM-DD) en el pasado.
    - `fechaFin`: LocalDate (YYYY-MM-DD) estrictamente posterior a `fechaInicio`.
    - `fechaLimiteRpta`: LocalDateTime (YYYY-MM-DDTHH:MM:SS) obligatoria.
    - `idEmpresa`, `idCategoria`, `idPrioridad`: UUIDs válidos existentes en la base de datos.
    - `estadoActual`: uno de ("EN_CONVOCATORIA", "EN_DESARROLLO", "FINALIZADO", "CANCELADO", "APLAZADO").

    Args:
        cantidad (int): Número de retos a generar.
        empresas_creadas (List[Dict[str, Any]]): Empresas creadas de donde tomar `idEmpresa`.
        categorias_ids (Optional[List[str]]): Lista de UUIDs reales de categorías académicas en BD.
        prioridades_ids (Optional[List[str]]): Lista de UUIDs reales de prioridades en BD.

    Returns:
        List[Dict[str, Any]]: Lista de diccionarios lista para poblar `POST /api/retos`.
    """
    if cantidad <= 0:
        raise ValueError("La cantidad de retos a generar debe ser mayor a 0.")
    if not empresas_creadas:
        raise ValueError("Se requiere al menos una empresa creada para asignar retos.")

    ids_empresas: List[str] = [
        str(emp["id"]) for emp in empresas_creadas if emp.get("id")
    ]

    # TODO: Si no se inyectan los UUIDs desde GET /api/categorias y GET /api/prioridades,
    # se generan UUIDs determinísticos de respaldo (del 1 al 5) para pruebas locales.
    cat_pool: List[str] = categorias_ids or [
        str(uuid.uuid5(uuid.NAMESPACE_DNS, f"categoria-{i}")) for i in range(1, 6)
    ]
    prio_pool: List[str] = prioridades_ids or [
        str(uuid.uuid5(uuid.NAMESPACE_DNS, f"prioridad-{i}")) for i in range(1, 6)
    ]

    retos: List[Dict[str, Any]] = []

    for i in range(1, cantidad + 1):
        # 1. Generación de fechas lógicas garantizando: fecha_fin > fecha_inicio
        fecha_inicio_date: date = fake.date_between(start_date="-90d", end_date="-10d")
        dias_duracion: int = random.randint(15, 120)
        fecha_fin_date: date = fecha_inicio_date + timedelta(days=dias_duracion)

        # Fecha límite de respuesta de convocatoria (entre fecha_inicio y fecha_fin)
        fecha_limite_dt: datetime = datetime.combine(
            fecha_inicio_date + timedelta(days=random.randint(5, 14)),
            time(hour=23, minute=59, second=0),
        )

        tema_base: str = random.choice(TEMAS_RETOS)
        titulo_reto: str = f"{tema_base} #{i}"[:100]

        reto: Dict[str, Any] = {
            "nombre": titulo_reto,
            "descripcion": (
                f"{fake.paragraph(nb_sentences=3)} "
                f"Objetivo esperado: optimizar indicadores clave en {fake.bs()}."
            ),
            "fechaInicio": fecha_inicio_date.isoformat(),
            "fechaFin": fecha_fin_date.isoformat(),
            "fechaLimiteRpta": fecha_limite_dt.isoformat(),
            "idEmpresa": random.choice(ids_empresas),
            "idCategoria": random.choice(cat_pool),
            "idPrioridad": random.choice(prio_pool),
            "estadoActual": random.choice(ESTADOS_RETO),
        }
        retos.append(reto)

    return retos


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
    empresas_demo = [{"id": str(uuid.uuid4()), **emp} for emp in generar_empresas(3)]
    usuarios_demo = generar_usuarios(5, empresas_demo)
    retos_demo = generar_retos(5, empresas_demo)

    print("=== Muestra de Usuarios Generados ===")
    print(convertir_a_dataframe(usuarios_demo)[["nombreCompleto", "email", "rol", "idEmpresa"]])
    print("\n=== Muestra de Retos Generados ===")
    print(convertir_a_dataframe(retos_demo)[["nombre", "fechaInicio", "fechaFin", "estadoActual", "idEmpresa"]])
