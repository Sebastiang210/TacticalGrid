"""Pruebas de las búsquedas informadas A* y Beam Search (paso 5)."""

from dataclasses import replace

import pytest
from conftest import posiciones, verificar_camino, verificar_metricas

from tacticalgrid.busqueda.heuristicas import h_manhattan, h_pasos
from tacticalgrid.busqueda.informada import a_estrella, beam
from tacticalgrid.busqueda.no_informada import ucs
from tacticalgrid.busqueda.problema import ProblemaNavegacion
from tacticalgrid.carga.cargador import Prueba

HEURISTICAS = [(h_manhattan, "manhattan"), (h_pasos, "pasos")]
CASOS = ["problema", "problema_mision", "problema_muro"]


def correr_a_estrella(problema, fabrica, nombre):
    return a_estrella(problema, fabrica(problema), nombre)


def correr_beam(problema, fabrica, nombre, k):
    return beam(problema, fabrica(problema), nombre, k)


@pytest.mark.parametrize(("fabrica", "nombre"), HEURISTICAS)
def test_a_estrella_enunciado_igual_que_ucs(fabrica, nombre, problema):
    referencia = ucs(problema)
    resultado = correr_a_estrella(problema, fabrica, nombre)
    assert resultado.exito
    assert resultado.costo == 7
    assert posiciones(resultado) == posiciones(referencia)
    assert resultado.nodos_expandidos <= referencia.nodos_expandidos


@pytest.mark.parametrize(("fabrica", "nombre"), HEURISTICAS)
def test_a_estrella_mision(fabrica, nombre, problema_mision):
    referencia = ucs(problema_mision)
    resultado = correr_a_estrella(problema_mision, fabrica, nombre)
    assert resultado.exito
    assert resultado.costo == 15
    assert resultado.estados[-1].lleva_recurso is True
    assert resultado.nodos_expandidos <= referencia.nodos_expandidos


def test_a_estrella_muro_pasos_expande_menos(problema_muro):
    con_h1 = correr_a_estrella(problema_muro, h_manhattan, "manhattan")
    con_h2 = correr_a_estrella(problema_muro, h_pasos, "pasos")
    assert con_h1.costo == 10
    assert con_h2.costo == 10
    assert con_h2.nodos_expandidos < con_h1.nodos_expandidos


@pytest.mark.parametrize(("fabrica", "nombre"), HEURISTICAS)
def test_beam_enunciado(fabrica, nombre, problema):
    voraz = correr_beam(problema, fabrica, nombre, 1)
    assert voraz.costo == 12
    assert posiciones(voraz) == [(0, 1), (0, 2), (1, 2), (1, 3), (2, 3), (3, 3), (3, 2)]
    for k in (2, 4, 8):
        assert correr_beam(problema, fabrica, nombre, k).costo == 7


@pytest.mark.parametrize(("fabrica", "nombre"), HEURISTICAS)
def test_beam_mision(fabrica, nombre, problema_mision):
    assert correr_beam(problema_mision, fabrica, nombre, 1).exito is False
    for k, costo in ((2, 21), (4, 18), (8, 15)):
        resultado = correr_beam(problema_mision, fabrica, nombre, k)
        assert resultado.exito
        assert resultado.costo == costo, k


@pytest.mark.parametrize(("fabrica", "nombre"), HEURISTICAS)
@pytest.mark.parametrize("caso", CASOS)
def test_beam_con_k_grande_igual_que_a_estrella(caso, fabrica, nombre, request):
    problema = request.getfixturevalue(caso)
    con_beam = correr_beam(problema, fabrica, nombre, 1000)
    con_a_estrella = correr_a_estrella(problema, fabrica, nombre)
    assert posiciones(con_beam) == posiciones(con_a_estrella)
    assert con_beam.costo == con_a_estrella.costo


@pytest.mark.parametrize("k", [None, 1, 2, 4, 8, 1000])
@pytest.mark.parametrize(("fabrica", "nombre"), HEURISTICAS)
@pytest.mark.parametrize("caso", CASOS)
def test_caminos_validos_y_metricas_coherentes(caso, fabrica, nombre, k, request):
    problema = request.getfixturevalue(caso)
    if k is None:
        resultado = correr_a_estrella(problema, fabrica, nombre)
    else:
        resultado = correr_beam(problema, fabrica, nombre, k)
    verificar_metricas(resultado)
    if resultado.exito:
        verificar_camino(problema, resultado)


@pytest.mark.parametrize("k", [None, 1, 1000])
@pytest.mark.parametrize(("fabrica", "nombre"), HEURISTICAS)
def test_objetivo_inalcanzable(fabrica, nombre, k, problema_inalcanzable):
    if k is None:
        resultado = correr_a_estrella(problema_inalcanzable, fabrica, nombre)
    else:
        resultado = correr_beam(problema_inalcanzable, fabrica, nombre, k)
    assert resultado.exito is False
    assert resultado.estados == ()
    assert resultado.acciones == ()
    assert resultado.costo == 0
    verificar_metricas(resultado)


@pytest.mark.parametrize("k", [None, 1, 3])
@pytest.mark.parametrize(("fabrica", "nombre"), HEURISTICAS)
def test_inicial_ya_es_objetivo(fabrica, nombre, k, datos):
    prueba = Prueba(modo="busqueda", unidad_inicio="A1", objetivo=(0, 1), mision=None)
    problema = ProblemaNavegacion(replace(datos, prueba=prueba))
    if k is None:
        resultado = correr_a_estrella(problema, fabrica, nombre)
    else:
        resultado = correr_beam(problema, fabrica, nombre, k)
    assert resultado.exito
    assert resultado.movimientos == 0
    assert resultado.costo == 0
    assert resultado.nodos_expandidos == 0


def test_nombres_de_algoritmo(problema):
    assert correr_a_estrella(problema, h_manhattan, "manhattan").algoritmo == "A* (manhattan)"
    assert correr_beam(problema, h_pasos, "pasos", 3).algoritmo == "Beam k=3 (pasos)"


@pytest.mark.parametrize("k", [0, -1])
def test_beam_k_invalido(k, problema):
    with pytest.raises(ValueError):
        correr_beam(problema, h_manhattan, "manhattan", k)
