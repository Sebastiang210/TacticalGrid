"""Pruebas de la partida completa y de su verificación."""

from dataclasses import replace

import pytest

from tacticalgrid.adversarial.partida import jugar_partida
from tacticalgrid.adversarial.utilidad import Evaluador
from tacticalgrid.core.juego import PASAR, EstadoJuego, Jugada, ReglasJuego
from tacticalgrid.verificacion.verificador import verificar_partida


def preparar(datos):
    reglas = ReglasJuego(datos)
    return reglas, Evaluador(reglas)


@pytest.fixture(scope="module")
def partida_prof2():
    from conftest import RUTA_ENUNCIADO

    from tacticalgrid.carga.cargador import cargar_escenario

    datos = cargar_escenario(RUTA_ENUNCIADO)
    reglas, evaluador = preparar(datos)
    return datos, jugar_partida(reglas, evaluador, 2)


def test_profundidad_2_gana_b_en_18_turnos(partida_prof2):
    _, partida = partida_prof2
    assert partida.ganador == "B"
    assert partida.turnos == 18
    assert len(partida.estados) == len(partida.jugadas) + 1 == len(partida.decisiones) + 1
    assert partida.estados[0].turnos_jugados == 0
    assert partida.estados[-1].turnos_jugados == 18


def test_profundidad_3_termina_en_empate_por_limite(datos):
    reglas, evaluador = preparar(datos)
    partida = jugar_partida(reglas, evaluador, 3)
    assert partida.ganador is None
    assert partida.turnos == 200
    assert verificar_partida(datos, partida).valido


def test_limite_pequeno_termina_en_empate(datos):
    chico = replace(datos, limite_turnos=6)
    reglas, evaluador = preparar(chico)
    partida = jugar_partida(reglas, evaluador, 2)
    assert partida.ganador is None
    assert partida.turnos == 6
    assert verificar_partida(chico, partida).valido


def test_minimax_y_alfa_beta_juegan_la_misma_partida(partida_prof2):
    datos, con_poda = partida_prof2
    reglas, evaluador = preparar(datos)
    sin_poda = jugar_partida(reglas, evaluador, 2, algoritmo="minimax")
    assert sin_poda.estados == con_poda.estados
    assert sin_poda.jugadas == con_poda.jugadas
    assert sin_poda.ganador == con_poda.ganador
    assert {d.algoritmo for d in sin_poda.decisiones} == {"Minimax"}
    assert {d.algoritmo for d in con_poda.decisiones} == {"Alfa-beta"}
    assert verificar_partida(datos, sin_poda).valido


def test_algoritmo_desconocido_lanza_valueerror(datos):
    reglas, evaluador = preparar(datos)
    with pytest.raises(ValueError):
        jugar_partida(reglas, evaluador, 2, algoritmo="mcts")


def test_estado_inicial_terminal_da_partida_vacia(datos):
    reglas, evaluador = preparar(replace(datos, limite_turnos=0))
    partida = jugar_partida(reglas, evaluador, 2)
    assert partida.jugadas == () and partida.turnos == 0 and len(partida.estados) == 1


def test_verificar_partida_valida(partida_prof2):
    datos, partida = partida_prof2
    reporte = verificar_partida(datos, partida)
    assert reporte.valido, reporte.errores
    assert reporte.costo_recalculado is None


def textos(reporte):
    return " | ".join(reporte.errores)


def test_detecta_jugada_cambiada(partida_prof2):
    datos, partida = partida_prof2
    jugadas = (Jugada("B1", "arriba"), *partida.jugadas[1:])
    reporte = verificar_partida(datos, replace(partida, jugadas=jugadas))
    assert not reporte.valido
    assert "Turno 1" in textos(reporte)


def test_detecta_jugada_legal_que_no_produce_el_estado(partida_prof2):
    datos, partida = partida_prof2
    jugadas = list(partida.jugadas)
    jugadas[0] = PASAR if jugadas[0] != PASAR else Jugada("A1", "derecha")
    reporte = verificar_partida(datos, replace(partida, jugadas=tuple(jugadas)))
    assert not reporte.valido


def test_detecta_estado_intermedio_cambiado(partida_prof2):
    datos, partida = partida_prof2
    estados = list(partida.estados)
    estados[3] = replace(estados[3], turnos_jugados=99)
    reporte = verificar_partida(datos, replace(partida, estados=tuple(estados)))
    assert not reporte.valido
    assert "turnos_jugados" in textos(reporte)


def test_detecta_ganador_falso(partida_prof2):
    datos, partida = partida_prof2
    reporte = verificar_partida(datos, replace(partida, ganador="A"))
    assert not reporte.valido
    assert "ganador" in textos(reporte)


def test_detecta_unidad_movida_a_casilla_ocupada(datos):
    reglas = ReglasJuego(datos)
    inicial = reglas.estado_inicial()
    antes = replace(
        inicial,
        posiciones=(("A1", (0, 1)), ("A2", (0, 0)), ("B1", (3, 2)), ("B2", (2, 3))),
    )
    despues = EstadoJuego(
        (("A1", (0, 0)), ("A2", (0, 0)), ("B1", (3, 2)), ("B2", (2, 3))),
        (2, 2),
        None,
        "B",
        1,
    )
    partida = replace(
        verificar_base(), estados=(antes, despues), jugadas=(Jugada("A1", "izquierda"),)
    )
    reporte = verificar_partida(datos, partida)
    assert not reporte.valido
    assert "comparte" in textos(reporte)


def verificar_base():
    """Partida mínima sin estados reales, para armar casos alterados a mano."""
    from tacticalgrid.adversarial.partida import Partida

    return Partida(estados=(), jugadas=(), decisiones=(), ganador=None, turnos=1)


def test_escenario_inicial_con_dos_unidades_en_la_misma_casilla_es_valido(datos):
    unidades = tuple(
        replace(u, posicion=(0, 1)) if u.id == "A2" else u for u in datos.unidades
    )
    compartido = replace(datos, unidades=unidades, limite_turnos=4)
    reglas, evaluador = preparar(compartido)
    inicial = reglas.estado_inicial()
    assert inicial.posicion_de("A1") == inicial.posicion_de("A2")
    partida = jugar_partida(reglas, evaluador, 2)
    assert partida.turnos == 4
    reporte = verificar_partida(compartido, partida)
    assert reporte.valido, reporte.errores
