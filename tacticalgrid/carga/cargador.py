"""Lectura de escenarios JSON y construcción de objetos inmutables."""

import json
from dataclasses import dataclass
from pathlib import Path

from tacticalgrid.config import LIMITE_TURNOS_POR_DEFECTO
from tacticalgrid.core.escenario import Escenario, Posicion, TipoTerreno


class ErrorCarga(Exception):
    """Error al leer o interpretar un archivo de escenario."""


@dataclass(frozen=True)
class UnidadInicial:
    """Unidad tal como aparece en el escenario inicial."""

    id: str
    bando: str
    tipo: str
    posicion: Posicion


@dataclass(frozen=True)
class Prueba:
    """Configuración opcional de una prueba asociada al escenario."""

    modo: str
    unidad_inicio: str | None
    objetivo: Posicion | None
    mision: str | None


@dataclass(frozen=True)
class DatosEscenario:
    """Todo lo leído del JSON, ya convertido a objetos inmutables."""

    version: str
    escenario: Escenario
    unidades: tuple[UnidadInicial, ...]
    recurso: Posicion
    turno: str
    portador: str | None
    profundidad_maxima: int | None
    limite_turnos: int
    prueba: Prueba | None


def _posicion(celda: dict) -> Posicion:
    """Convierte {"fila": f, "columna": c} en (f, c)."""
    return (int(celda["fila"]), int(celda["columna"]))


def leer_json(ruta: str | Path) -> dict:
    """
    Purpose: Leer un archivo JSON (UTF-8) y devolver su contenido como dict.
    Preconditions: ruta apunta a un archivo legible.
    Postconditions: Devuelve el objeto raíz; lanza ErrorCarga si falla la lectura o el formato.
    Complexity: tiempo O(n), espacio O(n) con n = tamaño del archivo
    Student validation: Se prueba mediante los tests en /tests/test_cargador
    """
    try:
        
        texto = Path(ruta).read_text(encoding="utf-8-sig")
    except FileNotFoundError:
        raise ErrorCarga(f"No existe el archivo de escenario: {ruta}") from None
    except UnicodeDecodeError as error:
        raise ErrorCarga(f"El archivo {ruta} no está codificado en UTF-8: {error.reason}") from error
    except OSError as error:
        raise ErrorCarga(f"No se pudo leer el archivo {ruta}: {error.strerror or error}") from error

    try:
        datos = json.loads(texto)
    except json.JSONDecodeError as error:
        raise ErrorCarga(
            f"JSON mal formado en {ruta}: línea {error.lineno}, columna {error.colno} ({error.msg})"
        ) from error

    if not isinstance(datos, dict):
        raise ErrorCarga(
            f"La raíz del JSON en {ruta} debe ser un objeto, no {type(datos).__name__}"
        )
    return datos


def construir_datos(datos: dict) -> DatosEscenario:
    """
    Purpose: Convertir el dict del JSON en objetos inmutables, con bandos y turno en mayúscula.
    Preconditions: datos es un escenario válido
    Postconditions: Devuelve DatosEscenario; unidades en el orden del JSON; costo None en
        terrenos no transitables.
    Complexity: tiempo O(F*C + U), espacio O(F*C + U) con F filas, C columnas, U unidades
    Student validation:  Se prueba mediante los tests en /tests/test_cargador
    """
    tipos = {}
    for nombre, definicion in datos["tipos_terreno"].items():
        transitable = bool(definicion["transitable"])
        costo = float(definicion["costo"]) if transitable else None
        tipos[nombre] = TipoTerreno(nombre=nombre, transitable=transitable, costo=costo)

    escenario = Escenario(
        filas=int(datos["mapa"]["filas"]),
        columnas=int(datos["mapa"]["columnas"]),
        tipos_terreno=tipos,
        terreno=tuple(tuple(fila) for fila in datos["terreno"]),
        bases={bando.upper(): _posicion(p) for bando, p in datos["bases"].items()},
    )

    unidades = tuple(
        UnidadInicial(
            id=u["id"],
            bando=u["bando"].upper(),
            tipo=u["tipo"],
            posicion=_posicion(u),
        )
        for u in datos["unidades"]
    )

    juego = datos.get("juego", {})
    prueba = None
    if "prueba" in datos:
        p = datos["prueba"]
        objetivo = p.get("objetivo")
        prueba = Prueba(
            modo=p["modo"],
            unidad_inicio=p.get("unidad_inicio"),
            objetivo=_posicion(objetivo) if objetivo is not None else None,
            mision=p.get("mision"),
        )

    return DatosEscenario(
        version=datos["version"],
        escenario=escenario,
        unidades=unidades,
        recurso=_posicion(datos["recurso"]),
        turno=datos["turno"].upper(),
        portador=juego.get("portador_recurso"),
        profundidad_maxima=juego.get("profundidad_maxima_minimax"),
        limite_turnos=juego.get("limite_turnos", LIMITE_TURNOS_POR_DEFECTO),
        prueba=prueba,
    )


def cargar_escenario(ruta: str | Path) -> DatosEscenario:
    """
    Purpose: Cargar un escenario completo desde un archivo JSON.
    Preconditions: ruta apunta a un escenario JSON legible.
    Postconditions: Devuelve DatosEscenario; lanza ErrorCarga si la lectura falla.
    Complexity: tiempo O(n), espacio O(n) con n = tamaño del escenario
    Student validation:  Se prueba mediante los tests en /tests/test_cargador
    """
    datos = leer_json(ruta)
    
    return construir_datos(datos)
