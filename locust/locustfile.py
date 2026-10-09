"""
Pruebas de rendimiento de la API de usuarios — Taller Ingeniería de Software II.

Mezcla de operaciones (GET predominante, POST minoritario):
    GET  /api/users              peso 4
    GET  /api/users/emails       peso 3
    GET  /api/users/over-twenty  peso 2
    POST /api/users/bulk         peso 1

Uso con interfaz web (usuarios, spawn rate y duración se fijan a mano):
    locust -f locustfile.py --host=http://HOST:8000

Uso con un escenario predefinido (la forma de carga la controla la variable ESCENARIO;
en ese caso -u, -r y -t se ignoran):
    ESCENARIO=carga     locust -f locustfile.py --host=http://HOST:8000 --headless --html reporte.html
    ESCENARIO=estres    locust -f locustfile.py --host=http://HOST:8000 --headless --html reporte.html
    ESCENARIO=capacidad locust -f locustfile.py --host=http://HOST:8000 --headless --html reporte.html

Variables de entorno opcionales (por defecto, los valores de ESCENARIOS):
    USUARIOS, SPAWN_RATE, DURACION_S         carga / capacidad
    USUARIOS_PASO, DURACION_PASO_S, USUARIOS_MAX   estrés (rampa escalonada)
    WAIT_MIN, WAIT_MAX     segundos de espera entre tareas de un usuario simulado
    PER_PAGE               tamaño de página pedido a la API (máx. 200)
    PAGINAS_MAX            se consulta una página aleatoria entre 1 y este valor
    TIMEOUT_S              tiempo máximo por petición; si se supera cuenta como fallo
"""

import os
import random
import uuid
from datetime import date, timedelta

from locust import HttpUser, LoadTestShape, between, events, task

ESCENARIO = os.getenv("ESCENARIO", "").strip().lower()

ESCENARIOS = {
    # Meseta con concurrencia moderada.
    "carga": {"USUARIOS": 10, "SPAWN_RATE": 1, "DURACION_S": 600},
    # Rampa escalonada más allá de lo nominal hasta encontrar el quiebre.
    "estres": {"USUARIOS_PASO": 5, "DURACION_PASO_S": 60, "USUARIOS_MAX": 60, "SPAWN_RATE": 5},
    # Cerca del máximo estable, sostenida por un periodo prolongado.
    "capacidad": {"USUARIOS": 15, "SPAWN_RATE": 1, "DURACION_S": 3600},
}

if ESCENARIO and ESCENARIO not in ESCENARIOS:
    raise ValueError(f"ESCENARIO debe ser uno de {sorted(ESCENARIOS)}; se recibió '{ESCENARIO}'")


def parametro(nombre, defecto=None):
    """Valor de una variable de entorno, o el definido para el escenario activo."""
    valor = os.getenv(nombre)
    if valor is None:
        valor = ESCENARIOS.get(ESCENARIO, {}).get(nombre, defecto)
    return float(valor)


WAIT_MIN = parametro("WAIT_MIN", 1)
WAIT_MAX = parametro("WAIT_MAX", 3)
PER_PAGE = int(parametro("PER_PAGE", 50))
PAGINAS_MAX = int(parametro("PAGINAS_MAX", 100))
TIMEOUT_S = parametro("TIMEOUT_S", 30)

CAMPOS_USUARIO = {"id", "name", "email", "birth_date", "email_verified_at", "created_at", "updated_at"}
CAMPOS_EMAIL = {"id", "email"}


def validar_pagina(resp, campos, con_cutoff=False):
    """Marca la respuesta como fallo si el código o la estructura no son los esperados."""
    if resp.error is not None and resp.status_code == 0:
        resp.failure(f"Error de red / timeout: {type(resp.error).__name__}")
        return
    if resp.status_code != 200:
        resp.failure(f"HTTP {resp.status_code} (se esperaba 200)")
        return
    try:
        cuerpo = resp.json()
    except ValueError:
        resp.failure("La respuesta no es JSON")
        return

    datos = cuerpo.get("data")
    if not isinstance(cuerpo.get("total"), int) or not isinstance(datos, list):
        resp.failure("Faltan 'total' (entero) o 'data' (arreglo)")
        return
    if len(datos) > PER_PAGE:
        resp.failure(f"'data' trae {len(datos)} elementos y per_page es {PER_PAGE}")
        return
    if datos and set(datos[0]) != campos:
        resp.failure(f"Campos inesperados: {sorted(datos[0])}")
        return
    if con_cutoff:
        cutoff = cuerpo.get("cutoff_date")
        if not cutoff:
            resp.failure("Falta 'cutoff_date'")
            return
        if any(u["birth_date"][:10] > cutoff for u in datos):
            resp.failure("Hay usuarios con birth_date posterior a cutoff_date")
            return
    resp.success()


def fecha_nacimiento_aleatoria():
    inicio = date(1950, 1, 1)
    return (inicio + timedelta(days=random.randint(0, 365 * 60))).isoformat()


class UsuarioApi(HttpUser):
    """Cliente HTTP de la API de usuarios."""

    wait_time = between(WAIT_MIN, WAIT_MAX)

    def _get_paginado(self, ruta, campos, con_cutoff=False):
        params = {"page": random.randint(1, PAGINAS_MAX), "per_page": PER_PAGE}
        with self.client.get(
            ruta,
            params=params,
            headers={"Accept": "application/json"},
            name=ruta,
            timeout=TIMEOUT_S,
            catch_response=True,
        ) as resp:
            validar_pagina(resp, campos, con_cutoff)

    @task(4)
    def listado(self):
        self._get_paginado("/api/users", CAMPOS_USUARIO)

    @task(3)
    def correos(self):
        self._get_paginado("/api/users/emails", CAMPOS_EMAIL)

    @task(2)
    def mayores_de_veinte(self):
        self._get_paginado("/api/users/over-twenty", CAMPOS_USUARIO, con_cutoff=True)

    @task(1)
    def alta_lote(self):
        # uuid4 garantiza correos únicos entre todos los usuarios simulados y ejecuciones.
        lote = uuid.uuid4().hex
        usuarios = [
            {
                "name": f"Locust {lote[:8]} {i}",
                "email": f"locust.{lote}.{i}@loadtest.local",
                "birth_date": fecha_nacimiento_aleatoria(),
            }
            for i in range(1, 4)
        ]
        with self.client.post(
            "/api/users/bulk",
            json={"users": usuarios},
            headers={"Accept": "application/json"},
            timeout=TIMEOUT_S,
            catch_response=True,
        ) as resp:
            if resp.error is not None and resp.status_code == 0:
                resp.failure(f"Error de red / timeout: {type(resp.error).__name__}")
            elif resp.status_code != 201:
                # Un 422 (p. ej. correo duplicado) es un fallo, no un éxito.
                resp.failure(f"HTTP {resp.status_code} (se esperaba 201): {resp.text[:200]}")
            else:
                try:
                    creados = resp.json().get("users", [])
                except ValueError:
                    resp.failure("La respuesta no es JSON")
                    return
                if sorted(u.get("email") for u in creados) != sorted(u["email"] for u in usuarios):
                    resp.failure("La respuesta no contiene los 3 usuarios enviados")
                else:
                    resp.success()


_VARIABLES = {
    "USUARIOS", "SPAWN_RATE", "DURACION_S", "USUARIOS_PASO", "DURACION_PASO_S", "USUARIOS_MAX",
    "WAIT_MIN", "WAIT_MAX", "PER_PAGE", "PAGINAS_MAX", "TIMEOUT_S",
}


@events.test_start.add_listener
def registrar_configuracion(environment, **_kwargs):
    print(
        f"[config] escenario={ESCENARIO or 'manual'} host={environment.host} "
        f"wait={WAIT_MIN}-{WAIT_MAX}s per_page={PER_PAGE} paginas_max={PAGINAS_MAX} "
        f"timeout={TIMEOUT_S}s parametros={ESCENARIOS.get(ESCENARIO, {})} "
        f"overrides={ {k: v for k, v in os.environ.items() if k in _VARIABLES} }"
    )


if ESCENARIO in ("carga", "capacidad"):

    class Meseta(LoadTestShape):
        """Rampa de subida a USUARIOS, meseta hasta DURACION_S y fin."""

        usuarios = int(parametro("USUARIOS"))
        spawn_rate = parametro("SPAWN_RATE")
        duracion = parametro("DURACION_S")

        def tick(self):
            if self.get_run_time() >= self.duracion:
                return None
            return self.usuarios, self.spawn_rate

elif ESCENARIO == "estres":

    class RampaEscalonada(LoadTestShape):
        """Suma USUARIOS_PASO cada DURACION_PASO_S hasta USUARIOS_MAX; termina al acabar ese último paso."""

        paso = int(parametro("USUARIOS_PASO"))
        duracion_paso = parametro("DURACION_PASO_S")
        maximo = int(parametro("USUARIOS_MAX"))
        spawn_rate = parametro("SPAWN_RATE")

        def tick(self):
            n_paso = int(self.get_run_time() // self.duracion_paso) + 1
            usuarios = n_paso * self.paso
            if usuarios > self.maximo:
                return None
            return usuarios, self.spawn_rate
