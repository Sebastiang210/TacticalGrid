"""Fixtures y helpers compartidos por las pruebas de búsqueda."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from tacticalgrid.busqueda.problema import ProblemaNavegacion
from tacticalgrid.carga.cargador import Prueba, cargar_escenario

RAIZ = Path(__file__).resolve().parent.parent
RUTA_ENUNCIADO = RAIZ / "scenarios" / "dev" / "enunciado_4x4.json"
RUTA_MURO = RAIZ / "scenarios" / "casos" / "caso3_muro.json"


@pytest.fixture
def datos():
    return cargar_escenario(RUTA_ENUNCIADO)


@pytest.fixture
def problema(datos):
    return ProblemaNavegacion(datos)


@pytest.fixture
def problema_mision(datos):
    return ProblemaNavegacion(datos_mision(datos))


@pytest.fixture
def problema_muro():
    return ProblemaNavegacion(cargar_escenario(RUTA_MURO))


@pytest.fixture
def problema_inalcanzable(tmp_path):
    contenido = json.loads(RUTA_ENUNCIADO.read_text(encoding="utf-8"))
    contenido["terreno"][2][3] = "muro"
    contenido["terreno"][3][2] = "muro"
    contenido["unidades"] = [
        {"id": "A1", "bando": "A", "tipo": "estandar", "fila": 0, "columna": 1},
        {"id": "A2", "bando": "A", "tipo": "estandar", "fila": 1, "columna": 0},
        {"id": "B1", "bando": "B", "tipo": "estandar", "fila": 3, "columna": 3},
    ]
    contenido["prueba"]["objetivo"] = {"fila": 3, "columna": 3}
    ruta = tmp_path / "inalcanzable.json"
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return ProblemaNavegacion(cargar_escenario(ruta))


def datos_mision(datos):
    prueba = Prueba(modo="busqueda", unidad_inicio="A1", objetivo=None, mision="llevar_recurso")
    return replace(datos, prueba=prueba)


def posiciones(resultado):
    return [e.posicion for e in resultado.estados]


def verificar_metricas(resultado):
    assert resultado.nodos_generados >= resultado.nodos_expandidos
    assert resultado.max_frontera >= 1
    assert resultado.tiempo_ms >= 0


def verificar_camino(problema, resultado):
    assert resultado.exito
    assert resultado.estados[0] == problema.inicial()
    assert problema.es_objetivo(resultado.estados[-1])
    assert len(resultado.estados) == resultado.movimientos + 1
    costo = 0.0
    pasos = zip(resultado.estados[:-1], resultado.estados[1:], resultado.acciones, strict=True)
    for anterior, siguiente, accion in pasos:
        costos = [c for a, s, c in problema.sucesores(anterior) if a == accion and s == siguiente]
        assert len(costos) == 1, f"{anterior} -> {siguiente} ({accion}) no es un sucesor real"
        costo += costos[0]
    assert resultado.costo == costo
