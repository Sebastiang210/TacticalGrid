"""Pruebas del estado de juego, las jugadas y las reglas deterministas."""

from dataclasses import FrozenInstanceError, replace

import pytest

from tacticalgrid.core.juego import PASAR, EstadoJuego, Jugada, ReglasJuego


@pytest.fixture
def reglas(datos):
    return ReglasJuego(datos)


def estado(posiciones, recurso=None, portador=None, turno="A", turnos=0):
    """Construye un EstadoJuego a mano; si nadie porta y no se da recurso, usa (0, 3)."""
    if portador is None and recurso is None:
        recurso = (0, 3)
    return EstadoJuego(tuple(sorted(posiciones.items())), recurso, portador, turno, turnos)


def jugadas(reglas, est):
    return [str(j) for j in reglas.jugadas_legales(est)]


def mover(reglas, est, unidad, direccion):
    return reglas.aplicar(est, Jugada(unidad, direccion))


def datos_con_unidades(datos, **posiciones):
    unidades = tuple(
        replace(u, posicion=posiciones.get(u.id, u.posicion)) for u in datos.unidades
    )
    return replace(datos, unidades=unidades)


# --- Jugada y EstadoJuego ---


def test_jugada_str_y_es_pasar():
    assert str(Jugada("A1", "derecha")) == "A1 derecha"
    assert str(PASAR) == "pasar"
    assert PASAR == Jugada(None, None)
    assert PASAR.es_pasar and not Jugada("A1", "derecha").es_pasar


def test_estado_invariante_recurso_portador():
    posiciones = (("A1", (0, 1)),)
    with pytest.raises(ValueError):
        EstadoJuego(posiciones, None, None, "A", 0)
    with pytest.raises(ValueError):
        EstadoJuego(posiciones, (2, 2), "A1", "A", 0)


def test_posicion_de_y_ocupadas(reglas):
    inicial = reglas.estado_inicial()
    assert inicial.posicion_de("B2") == (2, 3)
    assert inicial.ocupadas == frozenset({(0, 1), (1, 0), (3, 2), (2, 3)})
    with pytest.raises(ValueError):
        inicial.posicion_de("X9")


# --- estado inicial y jugadas legales ---


def test_estado_inicial(reglas):
    inicial = reglas.estado_inicial()
    assert inicial.posiciones == (
        ("A1", (0, 1)),
        ("A2", (1, 0)),
        ("B1", (3, 2)),
        ("B2", (2, 3)),
    )
    assert inicial.recurso == (2, 2)
    assert inicial.portador is None
    assert inicial.turno == "A"
    assert inicial.turnos_jugados == 0
    assert reglas.bando_de("B1") == "B"


def test_jugadas_legales_iniciales(reglas):
    esperado = ["A1 derecha", "A1 izquierda", "A2 arriba", "A2 abajo", "pasar"]
    assert jugadas(reglas, reglas.estado_inicial()) == esperado


def test_jugadas_de_b_tras_pasar(reglas):
    est = reglas.aplicar(reglas.estado_inicial(), PASAR)
    esperado = [
        "B1 arriba", "B1 derecha", "B1 izquierda",
        "B2 arriba", "B2 abajo", "B2 izquierda",
        "pasar",
    ]  # fmt: skip
    assert jugadas(reglas, est) == esperado


def test_no_mueve_a_casilla_con_aliado(reglas):
    est = estado({"A1": (0, 1), "A2": (0, 2), "B1": (3, 2), "B2": (2, 3)})
    assert "A1 derecha" not in jugadas(reglas, est)
    assert "A2 izquierda" not in jugadas(reglas, est)


def test_no_mueve_a_casilla_con_rival(reglas):
    est = estado({"A1": (0, 1), "A2": (1, 0), "B1": (2, 0), "B2": (2, 3)})
    assert "A2 abajo" not in jugadas(reglas, est)


def test_base_rival_prohibida_y_base_propia_permitida(reglas):
    est_a = estado({"A1": (3, 2), "A2": (1, 0), "B1": (2, 2), "B2": (2, 3)})
    assert "A1 derecha" not in jugadas(reglas, est_a)
    est_b = estado({"A1": (0, 1), "A2": (1, 0), "B1": (3, 2), "B2": (2, 3)}, turno="B")
    assert "B1 derecha" in jugadas(reglas, est_b)
    assert "B2 abajo" in jugadas(reglas, est_b)


# --- aplicar ---


def test_pasar_no_mueve_cambia_turno_y_suma(reglas):
    inicial = reglas.estado_inicial()
    nuevo = reglas.aplicar(inicial, PASAR)
    assert nuevo.posiciones == inicial.posiciones
    assert nuevo.recurso == inicial.recurso and nuevo.portador is None
    assert nuevo.turno == "B"
    assert nuevo.turnos_jugados == 1


def test_aplicar_no_modifica_el_original_y_hash_por_valor(reglas):
    inicial = reglas.estado_inicial()
    copia = reglas.estado_inicial()
    nuevo = mover(reglas, inicial, "A1", "derecha")
    assert inicial == copia and hash(inicial) == hash(copia)
    assert nuevo != inicial
    assert nuevo.posicion_de("A1") == (0, 2)
    assert len({inicial, copia}) == 1
    with pytest.raises(FrozenInstanceError):
        inicial.turno = "B"  # type: ignore[misc]


def test_recogida_y_el_recurso_viaja(reglas):
    est = reglas.aplicar(reglas.estado_inicial(), PASAR)
    est = mover(reglas, est, "B1", "arriba")
    assert est.portador == "B1" and est.recurso is None
    assert est.posicion_de("B1") == (2, 2)
    est = reglas.aplicar(est, PASAR)
    est = mover(reglas, est, "B1", "arriba")
    assert est.portador == "B1" and est.recurso is None
    assert est.posicion_de("B1") == (1, 2)


def test_intercepcion_por_rival_adyacente(reglas):
    est = estado({"A1": (0, 1), "A2": (2, 0), "B1": (1, 2), "B2": (3, 0)}, portador="B1")
    nuevo = mover(reglas, est, "A1", "derecha")
    assert nuevo.portador == "A1" and nuevo.recurso is None


def test_portador_junto_a_rival_no_pierde_el_recurso(reglas):
    est = estado(
        {"A1": (0, 1), "A2": (2, 0), "B1": (1, 2), "B2": (3, 0)}, portador="B1", turno="B"
    )
    nuevo = mover(reglas, est, "B1", "arriba")  # (0, 2) queda junto a A1 (0, 1)
    assert nuevo.portador == "B1"


def test_aliado_junto_al_portador_no_intercepta(reglas):
    est = estado(
        {"A1": (0, 0), "A2": (2, 0), "B1": (1, 2), "B2": (2, 3)}, portador="B1", turno="B"
    )
    nuevo = mover(reglas, est, "B2", "arriba")  # (1, 3) junto a B1
    assert nuevo.portador == "B1"


def test_diagonal_no_intercepta(reglas):
    est = estado({"A1": (0, 2), "A2": (1, 0), "B1": (2, 3), "B2": (3, 0)}, portador="B1")
    nuevo = mover(reglas, est, "A1", "abajo")  # (1, 2) es diagonal a (2, 3)
    assert nuevo.portador == "B1"


def test_perdedor_sin_jugada_que_lo_deje_vecino_del_nuevo_portador(reglas):
    est = estado({"A1": (0, 1), "A2": (2, 0), "B1": (1, 2), "B2": (3, 0)}, portador="B1")
    est = mover(reglas, est, "A1", "derecha")  # A1 intercepta a B1
    assert est.portador == "A1" and est.turno == "B"
    movimientos = [j for j in reglas.jugadas_legales(est) if j.unidad == "B1"]
    assert movimientos  # B1 tiene jugadas, pero ninguna intercepta
    for jugada in movimientos:
        nuevo = reglas.aplicar(est, jugada)
        assert nuevo.portador == "A1"
        distancia = sum(
            abs(a - b) for a, b in zip(nuevo.posicion_de("B1"), nuevo.posicion_de("A1"), strict=True)
        )
        assert distancia != 1


# --- unidad que empieza sobre el recurso ---


def test_unidad_sobre_el_recurso_no_lo_recoge_hasta_salir_y_volver(datos):
    reglas = ReglasJuego(datos_con_unidades(datos, B1=(2, 2)))
    est = reglas.estado_inicial()
    assert est.portador is None and est.recurso == (2, 2)
    est = reglas.aplicar(est, PASAR)  # A pasa
    est = reglas.aplicar(est, PASAR)  # B1 sigue sobre el recurso sin moverse
    assert est.portador is None
    est = mover(reglas, est, "A1", "derecha")  # otra unidad se mueve
    est = mover(reglas, est, "B2", "arriba")  # otra unidad de B se mueve
    assert est.portador is None
    est = reglas.aplicar(est, PASAR)
    est = mover(reglas, est, "B1", "arriba")  # sale
    assert est.portador is None
    est = reglas.aplicar(est, PASAR)
    est = mover(reglas, est, "B1", "abajo")  # vuelve a entrar
    assert est.portador == "B1" and est.recurso is None


# --- victoria y fin de partida ---


def test_victoria_al_entrar_a_la_base_propia(reglas):
    est = estado({"A1": (0, 2), "A2": (1, 0), "B1": (3, 2), "B2": (2, 3)}, portador="B1", turno="B")
    assert not reglas.es_terminal(est)
    nuevo = mover(reglas, est, "B1", "derecha")
    assert reglas.ganador(nuevo) == "B"
    assert reglas.es_terminal(nuevo)
    assert reglas.jugadas_legales(nuevo) == []


def test_intercepcion_sobre_la_propia_base_gana_en_el_acto(reglas):
    est = estado({"A1": (0, 2), "A2": (1, 0), "B1": (0, 1), "B2": (3, 0)}, portador="B1")
    nuevo = mover(reglas, est, "A2", "arriba")  # A2 entra a su base junto a B1
    assert nuevo.portador == "A2"
    assert reglas.ganador(nuevo) == "A"
    assert reglas.es_terminal(nuevo)


def test_portador_en_su_base_desde_el_inicio_es_terminal(datos):
    base = replace(datos_con_unidades(datos, A1=(0, 0)), portador="A1")
    reglas = ReglasJuego(base)
    inicial = reglas.estado_inicial()
    assert inicial.portador == "A1" and inicial.recurso is None
    assert reglas.ganador(inicial) == "A"
    assert reglas.es_terminal(inicial)
    assert reglas.jugadas_legales(inicial) == []


def test_limite_de_turnos_es_empate(datos):
    reglas = ReglasJuego(replace(datos, limite_turnos=2))
    est = reglas.estado_inicial()
    est = reglas.aplicar(est, PASAR)
    assert not reglas.es_terminal(est)
    est = reglas.aplicar(est, PASAR)
    assert reglas.es_terminal(est)
    assert reglas.ganador(est) is None
    assert reglas.jugadas_legales(est) == []


# --- errores y configuración ---


def test_aplicar_jugada_ilegal_lanza_valueerror(reglas):
    with pytest.raises(ValueError):
        reglas.aplicar(reglas.estado_inicial(), Jugada("A1", "arriba"))  # fuera del mapa
    with pytest.raises(ValueError):
        reglas.aplicar(reglas.estado_inicial(), Jugada("B1", "arriba"))  # no es su turno


def test_aplicar_sobre_estado_terminal_lanza_valueerror(datos):
    reglas = ReglasJuego(replace(datos, limite_turnos=0))
    with pytest.raises(ValueError):
        reglas.aplicar(reglas.estado_inicial(), PASAR)


def test_orden_alternativo_de_direcciones(datos):
    reglas = ReglasJuego(datos, ("abajo", "arriba", "izquierda", "derecha"))
    esperado = ["A1 izquierda", "A1 derecha", "A2 abajo", "A2 arriba", "pasar"]
    assert jugadas(reglas, reglas.estado_inicial()) == esperado


@pytest.mark.parametrize(
    "orden",
    [("arriba", "abajo"), ("arriba", "arriba", "abajo", "izquierda"), ("a", "b", "c", "d")],
)
def test_orden_invalido_lanza_valueerror(datos, orden):
    with pytest.raises(ValueError):
        ReglasJuego(datos, orden)
