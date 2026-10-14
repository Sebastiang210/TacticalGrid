"""Pruebas de las búsquedas no informadas BFS, DFS y UCS"""

from dataclasses import FrozenInstanceError, replace

import pytest
from conftest import posiciones, verificar_camino, verificar_metricas

from tacticalgrid.busqueda.no_informada import bfs, dfs, ucs
from tacticalgrid.busqueda.problema import ProblemaNavegacion
from tacticalgrid.busqueda.resultado import reconstruir_camino
from tacticalgrid.carga.cargador import Prueba
from tacticalgrid.core.navegacion import EstadoNavegacion

ALGORITMOS = [bfs, dfs, ucs]


def test_bfs_enunciado(problema):
    resultado = bfs(problema)
    assert resultado.exito
    assert resultado.algoritmo == "BFS"
    assert posiciones(resultado) == [(0, 1), (0, 2), (1, 2), (2, 2), (3, 2)]
    assert resultado.movimientos == 4
    assert resultado.costo == 14


def test_dfs_enunciado(problema):
    resultado = dfs(problema)
    assert resultado.exito
    assert resultado.algoritmo == "DFS"
    assert posiciones(resultado) == [(0, 1), (0, 2), (0, 3), (1, 3), (2, 3), (3, 3), (3, 2)]
    assert resultado.costo == 10


def test_ucs_enunciado(problema):
    resultado = ucs(problema)
    assert resultado.exito
    assert resultado.algoritmo == "UCS"
    assert posiciones(resultado) == [(0, 1), (0, 0), (1, 0), (2, 0), (2, 1), (3, 1), (3, 2)]
    assert resultado.costo == 7


def test_ucs_mision_llevar_recurso(problema_mision):
    resultado = ucs(problema_mision)
    assert resultado.exito
    assert resultado.costo == 15
    assert posiciones(resultado) == [
        (0, 1), (0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (2, 1), (2, 0), (1, 0), (0, 0)
    ]
    assert resultado.estados[-1].lleva_recurso is True


@pytest.mark.parametrize("algoritmo", ALGORITMOS)
@pytest.mark.parametrize("caso", ["problema", "problema_mision"])
def test_camino_valido_y_metricas_coherentes(algoritmo, caso, request):
    problema = request.getfixturevalue(caso)
    resultado = algoritmo(problema)
    verificar_camino(problema, resultado)
    verificar_metricas(resultado)
    assert resultado.algoritmo


@pytest.mark.parametrize("algoritmo", ALGORITMOS)
def test_objetivo_inalcanzable(algoritmo, problema_inalcanzable):
    resultado = algoritmo(problema_inalcanzable)
    assert resultado.exito is False
    assert resultado.estados == ()
    assert resultado.acciones == ()
    assert resultado.movimientos == 0
    assert resultado.costo == 0
    assert resultado.nodos_expandidos > 0
    verificar_metricas(resultado)


@pytest.mark.parametrize("algoritmo", ALGORITMOS)
def test_inicial_ya_es_objetivo(algoritmo, datos):
    prueba = Prueba(modo="busqueda", unidad_inicio="A1", objetivo=(0, 1), mision=None)
    problema = ProblemaNavegacion(replace(datos, prueba=prueba))
    resultado = algoritmo(problema)
    assert resultado.exito is True
    assert resultado.movimientos == 0
    assert resultado.costo == 0
    assert resultado.estados == (problema.inicial(),)
    assert resultado.nodos_expandidos == 0
    assert resultado.nodos_generados == 1
    verificar_metricas(resultado)


def test_dfs_con_otro_orden_cambia_el_camino(datos, problema):
    otro = ProblemaNavegacion(
        datos, orden_direcciones=("abajo", "izquierda", "arriba", "derecha")
    )
    resultado = dfs(otro)
    verificar_camino(otro, resultado)
    assert posiciones(resultado) != posiciones(dfs(problema))
    assert posiciones(resultado) == [
        (0, 1), (0, 0), (1, 0), (2, 0), (3, 0), (3, 1), (2, 1), (2, 2), (3, 2)
    ]


@pytest.mark.parametrize("caso", ["problema", "problema_mision"])
def test_ucs_nunca_es_mas_caro(caso, request):
    problema = request.getfixturevalue(caso)
    costo_ucs = ucs(problema).costo
    assert costo_ucs <= bfs(problema).costo
    assert costo_ucs <= dfs(problema).costo


def test_resultado_es_inmutable(problema):
    resultado = bfs(problema)
    with pytest.raises(FrozenInstanceError):
        resultado.costo = 0


def test_reconstruir_camino_solo_inicial():
    inicial = EstadoNavegacion(0, 1, False)
    assert reconstruir_camino({inicial: None}, inicial) == ((inicial,), (), 0.0)
