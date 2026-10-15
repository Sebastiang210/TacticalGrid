"""Pruebas de la tabla de distancias."""

from dataclasses import replace

import pytest

from tacticalgrid.adversarial.distancias import TablaDistancias
from tacticalgrid.config import DISTANCIA_INALCANZABLE


@pytest.fixture
def tabla(datos):
    return TablaDistancias(datos.escenario)


@pytest.mark.parametrize(
    ("a", "b", "esperado"),
    [((0, 1), (2, 2), 11), ((1, 0), (2, 2), 9), ((3, 2), (2, 2), 7), ((2, 2), (3, 3), 2)],
)
def test_distancias_del_enunciado(tabla, a, b, esperado):
    assert tabla.distancia(a, b) == esperado


def test_distancia_a_si_misma_es_cero(tabla):
    assert tabla.distancia((2, 2), (2, 2)) == 0


def test_celda_aislada_es_inalcanzable(datos):
    terreno = [list(fila) for fila in datos.escenario.terreno]
    terreno[2][3] = terreno[3][2] = "muro"  # 
    escenario = replace(datos.escenario, terreno=tuple(tuple(f) for f in terreno))
    tabla = TablaDistancias(escenario)
    assert tabla.distancia((0, 0), (3, 3)) == DISTANCIA_INALCANZABLE
    assert tabla.distancia((3, 3), (0, 0)) == DISTANCIA_INALCANZABLE
    assert tabla.distancia((0, 0), (1, 1)) == DISTANCIA_INALCANZABLE  
