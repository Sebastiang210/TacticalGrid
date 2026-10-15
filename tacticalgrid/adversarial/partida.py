"""Partida completa: bucle de decisión adversarial hasta que el juego termina."""

from dataclasses import dataclass

from tacticalgrid.adversarial.minimax import ResultadoDecision, alfa_beta, minimax
from tacticalgrid.adversarial.utilidad import Evaluador
from tacticalgrid.core.juego import EstadoJuego, Jugada, ReglasJuego

ALGORITMOS = {"minimax": minimax, "alfa_beta": alfa_beta}


@dataclass(frozen=True)
class Partida:
    """Historial de una partida; estados incluye el inicial (len(estados) == len(jugadas) + 1)."""

    estados: tuple[EstadoJuego, ...]
    jugadas: tuple[Jugada, ...]
    decisiones: tuple[ResultadoDecision, ...]
    ganador: str | None  
    turnos: int


def jugar_partida(
    reglas: ReglasJuego,
    evaluador: Evaluador,
    profundidad: int,
    algoritmo: str = "alfa_beta",
    estado_inicial: EstadoJuego | None = None,
) -> Partida:
    """
    Purpose: Jugar una partida completa; en cada turno decide quien lo tiene (MAX) con el
        algoritmo elegido y aplica su jugada.
    Preconditions: algoritmo es "minimax" o "alfa_beta"; profundidad >= 1.
    Postconditions: Devuelve la Partida con todos los estados (incluido el inicial), jugadas
        y decisiones; ganador es reglas.ganador del estado final (None = empate por límite).
        ValueError si el algoritmo es desconocido o la profundidad es inválida.
    Complexity: tiempo O(T * b^d) con minimax (mejor caso O(T * b^(d/2)) con alfa-beta),
        espacio O(T) con T = turnos jugados, b <= 4u+1 jugadas y d = profundidad
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida en tests/test_partida.py
    """
    if algoritmo not in ALGORITMOS:
        raise ValueError(
            f"Algoritmo desconocido {algoritmo!r}; opciones: {tuple(ALGORITMOS)}"
        )
    decidir = ALGORITMOS[algoritmo]
    estado = estado_inicial if estado_inicial is not None else reglas.estado_inicial()
    estados = [estado]
    jugadas: list[Jugada] = []
    decisiones: list[ResultadoDecision] = []
    while not reglas.es_terminal(estado):
        decision = decidir(reglas, evaluador, estado, profundidad)
        estado = reglas.aplicar(estado, decision.jugada)
        estados.append(estado)
        jugadas.append(decision.jugada)
        decisiones.append(decision)
    return Partida(
        estados=tuple(estados),
        jugadas=tuple(jugadas),
        decisiones=tuple(decisiones),
        ganador=reglas.ganador(estado),
        turnos=len(jugadas),
    )
