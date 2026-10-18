"""Pruebas del orden de expansión que registran los algoritmos de búsqueda."""

import pytest
from conftest import RAIZ, datos_mision

from tacticalgrid.busqueda.heuristicas import h_manhattan, h_pasos
from tacticalgrid.busqueda.informada import a_estrella, beam
from tacticalgrid.busqueda.no_informada import bfs, dfs, ucs
from tacticalgrid.busqueda.problema import ProblemaNavegacion
from tacticalgrid.carga.cargador import cargar_escenario

CASOS = RAIZ / "scenarios" / "casos"
ESCENARIOS = {
    "enunciado_4x4": RAIZ / "scenarios" / "dev" / "enunciado_4x4.json",
    "caso3_muro": CASOS / "caso3_muro.json",
    "caso6_mision": CASOS / "caso6_mision.json",
    "caso6_mision_grande": CASOS / "caso6_mision_grande.json",
}
ALGORITMOS = {
    "BFS": bfs,
    "DFS": dfs,
    "UCS": ucs,
    "A* h1": lambda p: a_estrella(p, h_manhattan(p), "h1"),
    "A* h2": lambda p: a_estrella(p, h_pasos(p), "h2"),
    "Beam k=1": lambda p: beam(p, h_pasos(p), "h2", 1),
    "Beam k=4": lambda p: beam(p, h_pasos(p), "h2", 4),
}


def problema_de(nombre):
    return ProblemaNavegacion(cargar_escenario(ESCENARIOS[nombre]))


@pytest.mark.parametrize("escenario", list(ESCENARIOS))
@pytest.mark.parametrize("algoritmo", list(ALGORITMOS))
def test_orden_expansion_coincide_con_los_expandidos(escenario, algoritmo):
    problema = problema_de(escenario)
    resultado = ALGORITMOS[algoritmo](problema)
    assert len(resultado.orden_expansion) == resultado.nodos_expandidos
    if resultado.nodos_expandidos:
        assert resultado.orden_expansion[0] == problema.inicial()


@pytest.mark.parametrize(
    ("algoritmo", "esperado"), [("BFS", 42), ("UCS", 42), ("A* h1", 24), ("A* h2", 10)]
)
def test_expandidos_conocidos_en_el_muro(algoritmo, esperado):
    resultado = ALGORITMOS[algoritmo](problema_de("caso3_muro"))
    assert resultado.nodos_expandidos == esperado
    assert len(resultado.orden_expansion) == esperado


def test_mision_expande_con_y_sin_recurso():
    resultado = ucs(problema_de("caso6_mision"))
    llevas = {e.lleva_recurso for e in resultado.orden_expansion}
    assert llevas == {False, True}


def test_sin_solucion_tambien_registra_la_expansion(datos):
    problema = ProblemaNavegacion(datos_mision(datos))
    resultado = beam(problema, h_pasos(problema), "h2", 1)
    assert not resultado.exito
    assert len(resultado.orden_expansion) == resultado.nodos_expandidos > 0
