"""Pruebas de las heurísticas h_manhattan y h_pasos (paso 5)."""

import heapq
import math
from collections import deque
from dataclasses import replace

import pytest
from conftest import datos_mision

from tacticalgrid.busqueda.heuristicas import h_manhattan, h_pasos
from tacticalgrid.busqueda.problema import ProblemaNavegacion
from tacticalgrid.core.navegacion import EstadoNavegacion

CASOS = ["problema", "problema_mision", "problema_muro"]
FABRICAS = [h_manhattan, h_pasos]


def alcanzables(problema):
    """Todos los estados alcanzables desde el inicial (BFS sobre estados)."""
    inicial = problema.inicial()
    vistos = {inicial}
    cola = deque([inicial])
    while cola:
        estado = cola.popleft()
        for _, sucesor, _ in problema.sucesores(estado):
            if sucesor not in vistos:
                vistos.add(sucesor)
                cola.append(sucesor)
    return vistos


def costo_real(problema):
    """Costo mínimo de cada estado alcanzable a algún objetivo (Dijkstra hacia atrás)."""
    estados = alcanzables(problema)
    entrantes = {estado: [] for estado in estados}
    for estado in estados:
        for _, sucesor, costo in problema.sucesores(estado):
            entrantes[sucesor].append((estado, costo))
    distancia = {e: 0.0 for e in estados if problema.es_objetivo(e)}
    heap = [(0.0, i, e) for i, e in enumerate(distancia)]
    contador = len(heap)
    while heap:
        d, _, estado = heapq.heappop(heap)
        if d > distancia[estado]:
            continue
        for anterior, costo in entrantes[estado]:
            nuevo = d + costo
            if nuevo < distancia.get(anterior, math.inf):
                distancia[anterior] = nuevo
                contador += 1
                heapq.heappush(heap, (nuevo, contador, anterior))
    return distancia


@pytest.mark.parametrize("fabrica", FABRICAS)
@pytest.mark.parametrize("caso", CASOS)
def test_admisible(caso, fabrica, request):
    problema = request.getfixturevalue(caso)
    h = fabrica(problema)
    reales = costo_real(problema)
    for estado in alcanzables(problema):
        assert h(estado) <= reales.get(estado, math.inf), estado


@pytest.mark.parametrize("fabrica", FABRICAS)
@pytest.mark.parametrize("caso", CASOS)
def test_consistente(caso, fabrica, request):
    problema = request.getfixturevalue(caso)
    h = fabrica(problema)
    for estado in alcanzables(problema):
        for _, sucesor, costo in problema.sucesores(estado):
            assert h(estado) <= costo + h(sucesor), (estado, sucesor)


@pytest.mark.parametrize("caso", CASOS)
def test_pasos_domina_a_manhattan(caso, request):
    problema = request.getfixturevalue(caso)
    h1, h2 = h_manhattan(problema), h_pasos(problema)
    for estado in alcanzables(problema):
        assert h2(estado) >= h1(estado), estado


def test_pasos_supera_a_manhattan_detras_del_muro(problema_muro):
    inicial = problema_muro.inicial()
    assert h_manhattan(problema_muro)(inicial) == 4
    assert h_pasos(problema_muro)(inicial) == 10


@pytest.mark.parametrize("fabrica", FABRICAS)
def test_cero_en_el_objetivo(fabrica, problema):
    h = fabrica(problema)
    assert h(EstadoNavegacion(3, 2, False)) == 0
    assert h(EstadoNavegacion(3, 2, True)) == 0


@pytest.mark.parametrize("fabrica", FABRICAS)
def test_cero_en_la_base_con_recurso(fabrica, problema_mision):
    h = fabrica(problema_mision)
    assert h(EstadoNavegacion(0, 0, True)) == 0
    assert h(EstadoNavegacion(0, 0, False)) > 0


@pytest.mark.parametrize("fabrica", FABRICAS)
def test_mision_con_recurso_ajeno_es_infinita(fabrica, datos):
    problema = ProblemaNavegacion(replace(datos_mision(datos), portador="B1"))
    assert fabrica(problema)(problema.inicial()) == math.inf


def test_objetivo_encerrado(problema_inalcanzable):
    inicial = problema_inalcanzable.inicial()
    assert h_pasos(problema_inalcanzable)(inicial) == math.inf
    assert h_manhattan(problema_inalcanzable)(inicial) < math.inf
