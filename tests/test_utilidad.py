"""Pruebas de la función de utilidad."""

from dataclasses import replace

import pytest

from tacticalgrid.adversarial.utilidad import Evaluador
from tacticalgrid.config import UTILIDAD_VICTORIA
from tacticalgrid.core.juego import EstadoJuego, Jugada, ReglasJuego


@pytest.fixture
def reglas(datos):
    return ReglasJuego(datos)


@pytest.fixture
def evaluador(reglas):
    return Evaluador(reglas)


def estado(posiciones, recurso=None, portador=None, turno="A", turnos=0):
    return EstadoJuego(tuple(sorted(posiciones.items())), recurso, portador, turno, turnos)


def test_utilidad_estado_inicial(reglas, evaluador):
    inicial = reglas.estado_inicial()
    assert evaluador.puntaje(inicial, "A") == -18
    assert evaluador.puntaje(inicial, "B") == -14
    assert evaluador.utilidad(inicial, "A") == -4


def test_utilidad_tras_recoger_b1_y_simetria(reglas, evaluador):
    est = reglas.aplicar(reglas.estado_inicial(), Jugada("A1", "derecha"))
    est = reglas.aplicar(est, Jugada("B1", "arriba"))
    assert est.portador == "B1"
    assert evaluador.puntaje(est, "B") == 90
    assert evaluador.puntaje(est, "A") == -27
    assert evaluador.utilidad(est, "A") == -117
    assert evaluador.utilidad(est, "B") == 117


def test_victoria_derrota_y_empate(datos):
    posiciones = {"A1": (0, 1), "A2": (1, 0), "B1": (3, 3), "B2": (2, 3)}
    reglas = ReglasJuego(datos)
    evaluador = Evaluador(reglas)
    gana_b = estado(posiciones, portador="B1")
    assert evaluador.utilidad(gana_b, "B") == UTILIDAD_VICTORIA == 10000
    assert evaluador.utilidad(gana_b, "A") == -UTILIDAD_VICTORIA
    limite = ReglasJuego(replace(datos, limite_turnos=2))
    est = limite.estado_inicial()
    est = limite.aplicar(limite.aplicar(est, Jugada(None, None)), Jugada(None, None))
    assert limite.es_terminal(est) and limite.ganador(est) is None
    assert Evaluador(limite).utilidad(est, "A") == 0
