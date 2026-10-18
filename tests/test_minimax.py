"""Pruebas de Minimax y Minimax con poda alfa-beta."""

from dataclasses import replace

import pytest
from conftest import RAIZ

from tacticalgrid.adversarial.minimax import alfa_beta, minimax
from tacticalgrid.adversarial.utilidad import Evaluador
from tacticalgrid.carga.cargador import cargar_escenario
from tacticalgrid.core.juego import PASAR, EstadoJuego, Jugada, ReglasJuego

RUTA_ADV = RAIZ / "scenarios" / "casos" / "caso7_8_10_adversarial.json"


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


# --- jugadas consideradas en la raíz ---

JUGADAS_RAIZ = ["A1 derecha", "A1 izquierda", "A2 arriba", "A2 abajo", "pasar"]
ORDEN_ALTERNATIVO = ("abajo", "izquierda", "arriba", "derecha")


def decidir_adv(algoritmo, profundidad, orden=None):
    datos = cargar_escenario(RUTA_ADV)
    reglas = ReglasJuego(datos) if orden is None else ReglasJuego(datos, orden)
    return reglas, algoritmo(reglas, Evaluador(reglas), reglas.estado_inicial(), profundidad)


def textos(decision):
    return [str(vj.jugada) for vj in decision.jugadas_consideradas]


def valores(decision):
    return [vj.valor for vj in decision.jugadas_consideradas]


def exactos(decision):
    return [vj.exacto for vj in decision.jugadas_consideradas]


def test_minimax_p2_jugadas_consideradas():
    _, decision = decidir_adv(minimax, 2)
    assert textos(decision) == JUGADAS_RAIZ
    assert valores(decision) == [-117, -117, -120, -114, -117]
    assert all(exactos(decision))
    assert str(decision.jugada) == "A2 abajo"
    assert decision.valor == max(valores(decision))


def test_alfa_beta_p2_jugadas_consideradas():
    _, decision = decidir_adv(alfa_beta, 2)
    assert textos(decision) == JUGADAS_RAIZ
    assert valores(decision) == [-117, -117, -120, -114, -117]
    assert exactos(decision) == [True, False, False, True, False]


def test_minimax_p3_jugadas_consideradas():
    _, decision = decidir_adv(minimax, 3)
    assert textos(decision) == JUGADAS_RAIZ
    assert valores(decision) == [0, -114, -117, 0, -114]
    assert all(exactos(decision))
    assert str(decision.jugada) == "A1 derecha"  # empata con A2 abajo; gana la primera


def test_alfa_beta_p3_jugadas_consideradas():
    _, decision = decidir_adv(alfa_beta, 3)
    assert exactos(decision) == [True, False, False, False, False]


@pytest.mark.parametrize("orden", [None, ORDEN_ALTERNATIVO])
@pytest.mark.parametrize("profundidad", [1, 2, 3, 4])
def test_propiedades_de_jugadas_consideradas(profundidad, orden):
    reglas, mm = decidir_adv(minimax, profundidad, orden)
    _, ab = decidir_adv(alfa_beta, profundidad, orden)
    cantidad = len(reglas.jugadas_legales(reglas.estado_inicial()))
    for decision in (mm, ab):
        assert len(decision.jugadas_consideradas) == cantidad
        elegida = next(vj for vj in decision.jugadas_consideradas if vj.jugada == decision.jugada)
        assert elegida.valor == decision.valor and elegida.exacto
    assert all(vj.valor <= ab.valor for vj in ab.jugadas_consideradas if not vj.exacto)
    por_jugada = {vj.jugada: vj.valor for vj in mm.jugadas_consideradas}
    for vj in ab.jugadas_consideradas:
        if vj.exacto:
            assert vj.valor == por_jugada[vj.jugada]
