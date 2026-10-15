"""Pruebas de Minimax y Minimax con poda alfa-beta."""

from dataclasses import replace

import pytest

from tacticalgrid.adversarial.minimax import alfa_beta, minimax
from tacticalgrid.adversarial.utilidad import Evaluador
from tacticalgrid.core.juego import PASAR, EstadoJuego, Jugada, ReglasJuego


@pytest.fixture
def reglas(datos):
    return ReglasJuego(datos)


@pytest.fixture
def evaluador(reglas):
    return Evaluador(reglas)


def estado(posiciones, recurso=None, portador=None, turno="A", turnos=0):
    return EstadoJuego(tuple(sorted(posiciones.items())), recurso, portador, turno, turnos)


ESPERADO = {
    1: ("A2 abajo", -2, 5, 5, 0),
    2: ("A2 abajo", -114, 40, 22, 3),
    3: ("A1 derecha", 0, 201, 62, 9),
    4: ("A1 derecha", -111, 1136, 234, 39),
}


@pytest.mark.parametrize("profundidad", [1, 2, 3, 4])
def test_valores_y_nodos_desde_el_estado_inicial(reglas, evaluador, profundidad):
    jugada, valor, nodos_mm, nodos_ab, podas = ESPERADO[profundidad]
    inicial = reglas.estado_inicial()
    mm = minimax(reglas, evaluador, inicial, profundidad)
    ab = alfa_beta(reglas, evaluador, inicial, profundidad)
    assert (mm.algoritmo, ab.algoritmo) == ("Minimax", "Alfa-beta")
    for resultado in (mm, ab):
        assert str(resultado.jugada) == jugada
        assert resultado.valor == valor
        assert resultado.profundidad == profundidad
        assert resultado.tiempo_ms >= 0
    assert mm.nodos_generados == nodos_mm and mm.podas == 0
    assert ab.nodos_generados == nodos_ab and ab.podas == podas
    assert ab.nodos_evaluados <= mm.nodos_evaluados
    if profundidad == 1:
        assert ab.nodos_generados <= mm.nodos_generados
    else:
        assert ab.nodos_generados < mm.nodos_generados


def estados_variados(reglas):
    inicial = reglas.estado_inicial()
    tras_a = reglas.aplicar(inicial, Jugada("A1", "derecha"))
    tras_b = reglas.aplicar(tras_a, Jugada("B1", "arriba")) 
    return [
        inicial,
        tras_a, 
        tras_b,
        reglas.aplicar(tras_b, Jugada("A2", "abajo")),
        estado({"A1": (0, 1), "A2": (2, 0), "B1": (1, 2), "B2": (3, 0)}, portador="B1"),
    ]


@pytest.mark.parametrize("profundidad", [1, 2, 3, 4])
def test_alfa_beta_equivale_a_minimax(reglas, evaluador, profundidad):
    for est in estados_variados(reglas):
        mm = minimax(reglas, evaluador, est, profundidad)
        ab = alfa_beta(reglas, evaluador, est, profundidad)
        assert ab.jugada == mm.jugada
        assert ab.valor == mm.valor


def test_victoria_inmediata(reglas, evaluador):
    est = estado(
        {"A1": (0, 1), "A2": (1, 0), "B1": (3, 2), "B2": (2, 3)}, portador="B1", turno="B"
    )
    for algoritmo in (minimax, alfa_beta):
        resultado = algoritmo(reglas, evaluador, est, 1)
        assert str(resultado.jugada) == "B1 derecha"
        assert resultado.valor == 10000


def test_orden_alternativo_mantiene_el_valor(datos):
    reglas = ReglasJuego(datos, ("abajo", "izquierda", "derecha", "arriba"))
    evaluador = Evaluador(reglas)
    inicial = reglas.estado_inicial()
    for profundidad in (1, 2, 3, 4):
        mm = minimax(reglas, evaluador, inicial, profundidad)
        ab = alfa_beta(reglas, evaluador, inicial, profundidad)
        assert ab.valor == mm.valor
        assert ab.jugada == mm.jugada
        assert ab.nodos_generados <= mm.nodos_generados
    referencia = minimax(ReglasJuego(datos), Evaluador(ReglasJuego(datos)), inicial, 4)
    assert mm.valor == referencia.valor


@pytest.mark.parametrize("algoritmo", [minimax, alfa_beta])
def test_profundidad_invalida_lanza_valueerror(reglas, evaluador, algoritmo):
    with pytest.raises(ValueError):
        algoritmo(reglas, evaluador, reglas.estado_inicial(), 0)


@pytest.mark.parametrize("algoritmo", [minimax, alfa_beta])
def test_estado_terminal_lanza_valueerror(datos, algoritmo):
    reglas = ReglasJuego(replace(datos, limite_turnos=1))
    evaluador = Evaluador(reglas)
    terminal = reglas.aplicar(reglas.estado_inicial(), PASAR)
    with pytest.raises(ValueError):
        algoritmo(reglas, evaluador, terminal, 1)
