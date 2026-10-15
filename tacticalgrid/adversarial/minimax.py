"""Decisión adversarial: Minimax y Minimax con poda alfa-beta."""

import math
import time
from dataclasses import dataclass

from tacticalgrid.adversarial.utilidad import Evaluador
from tacticalgrid.core.juego import EstadoJuego, Jugada, ReglasJuego


@dataclass(frozen=True)
class ResultadoDecision:
    """Jugada elegida y métricas de la búsqueda."""

    algoritmo: str
    jugada: Jugada
    valor: float
    profundidad: int
    nodos_generados: int
    nodos_evaluados: int
    podas: int
    tiempo_ms: float


class _Busqueda:
    """Contexto de una búsqueda: reglas, evaluador, bando MAX y contadores."""

    def __init__(self, reglas: ReglasJuego, evaluador: Evaluador, estado: EstadoJuego) -> None:
        self.reglas = reglas
        self.evaluador = evaluador
        self.max = estado.turno
        self.generados = 0
        self.evaluados = 0
        self.podas = 0

    def hoja(self, estado: EstadoJuego, profundidad: int) -> float | None:
        """Utilidad si el nodo es hoja (terminal o profundidad 0); None si hay que expandir."""
        if profundidad == 0 or self.reglas.es_terminal(estado):
            self.evaluados += 1
            return self.evaluador.utilidad(estado, self.max)
        return None

    def hijo(self, estado: EstadoJuego, jugada: Jugada) -> EstadoJuego:
        self.generados += 1
        return self.reglas.aplicar(estado, jugada)

    def minimax(self, estado: EstadoJuego, profundidad: int) -> float:
        valor = self.hoja(estado, profundidad)
        if valor is not None:
            return valor
        maximiza = estado.turno == self.max
        mejor = -math.inf if maximiza else math.inf
        for jugada in self.reglas.jugadas_legales(estado):
            v = self.minimax(self.hijo(estado, jugada), profundidad - 1)
            mejor = max(mejor, v) if maximiza else min(mejor, v)
        return mejor

    def alfa_beta(self, estado: EstadoJuego, profundidad: int, alfa: float, beta: float) -> float:
        valor = self.hoja(estado, profundidad)
        if valor is not None:
            return valor
        maximiza = estado.turno == self.max
        mejor = -math.inf if maximiza else math.inf
        for jugada in self.reglas.jugadas_legales(estado):
            v = self.alfa_beta(self.hijo(estado, jugada), profundidad - 1, alfa, beta)
            if maximiza:
                mejor = max(mejor, v)
                alfa = max(alfa, mejor)
            else:
                mejor = min(mejor, v)
                beta = min(beta, mejor)
            if alfa >= beta:
                self.podas += 1
                break
        return mejor


def _decidir(
    algoritmo: str,
    reglas: ReglasJuego,
    evaluador: Evaluador,
    estado: EstadoJuego,
    profundidad: int,
) -> ResultadoDecision:
    """Recorre las jugadas de la raíz y elige la primera con el mejor valor."""
    if profundidad < 1:
        raise ValueError(f"La profundidad debe ser al menos 1, no {profundidad}")
    if reglas.es_terminal(estado):
        raise ValueError("No se puede decidir una jugada desde un estado terminal")
    inicio = time.perf_counter()
    busqueda = _Busqueda(reglas, evaluador, estado)
    mejor_jugada = None
    mejor_valor = -math.inf
    for jugada in reglas.jugadas_legales(estado):
        hijo = busqueda.hijo(estado, jugada)
        if algoritmo == "Minimax":
            valor = busqueda.minimax(hijo, profundidad - 1)
        else:
            valor = busqueda.alfa_beta(hijo, profundidad - 1, mejor_valor, math.inf)
        if valor > mejor_valor:
            mejor_valor, mejor_jugada = valor, jugada
    tiempo_ms = (time.perf_counter() - inicio) * 1000
    return ResultadoDecision(
        algoritmo=algoritmo,
        jugada=mejor_jugada,
        valor=mejor_valor,
        profundidad=profundidad,
        nodos_generados=busqueda.generados,
        nodos_evaluados=busqueda.evaluados,
        podas=busqueda.podas,
        tiempo_ms=tiempo_ms,
    )


def minimax(
    reglas: ReglasJuego, evaluador: Evaluador, estado: EstadoJuego, profundidad: int
) -> ResultadoDecision:
    """
    Purpose: Elegir la mejor jugada del bando en turno explorando el árbol completo.
    Preconditions: profundidad >= 1 y estado no terminal.
    Postconditions: Devuelve la primera jugada con el mejor valor (MAX = turno de la raíz) y
        las métricas; ValueError si no se cumplen las precondiciones.
    Complexity: tiempo O(b^d), espacio O(d) con b <= 4u+1 jugadas y d = profundidad
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida con pruebas unitarias y de integración en test_minimax.py.
    """
    return _decidir("Minimax", reglas, evaluador, estado, profundidad)


def alfa_beta(
    reglas: ReglasJuego, evaluador: Evaluador, estado: EstadoJuego, profundidad: int
) -> ResultadoDecision:
    """
    Purpose: Igual que minimax, pero podando ramas que no pueden cambiar la decisión.
    Preconditions: profundidad >= 1 y estado no terminal.
    Postconditions: Misma jugada y mismo valor que minimax con igual profundidad; podas
        cuenta los cortes; ValueError si no se cumplen las precondiciones.
    Complexity: tiempo O(b^(d/2)) en el mejor caso y O(b^d) en el peor, espacio O(d), con
        b <= 4u+1 jugadas y d = profundidad
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida con pruebas unitarias y de integración en test_minimax.py.
    """
    return _decidir("Alfa-beta", reglas, evaluador, estado, profundidad)
