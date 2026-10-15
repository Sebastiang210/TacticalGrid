"""Función de utilidad para evaluar estados desde el punto de vista de un bando."""

from tacticalgrid.adversarial.distancias import TablaDistancias
from tacticalgrid.config import (
    PESO_AVANCE,
    PESO_CARRERA,
    PESO_PERSECUCION,
    PESO_POSESION,
    UTILIDAD_VICTORIA,
)
from tacticalgrid.core.juego import EstadoJuego, ReglasJuego


class Evaluador:
    """Evalúa estados con una combinación lineal de posesión, avance, carrera y persecución."""

    def __init__(
        self,
        reglas: ReglasJuego,
        peso_posesion: float = PESO_POSESION,
        peso_avance: float = PESO_AVANCE,
        peso_carrera: float = PESO_CARRERA,
        peso_persecucion: float = PESO_PERSECUCION,
    ) -> None:
        """
        Purpose: Construir el evaluador y su tabla de distancias (una sola vez).
        Preconditions: reglas es un ReglasJuego válido.
        Postconditions: Queda listo para puntaje/utilidad con los pesos dados.
        Complexity: tiempo O(N^2 log N), espacio O(N^2) con N = celdas transitables
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se valida mediante pruebas unitarias y de integración en test_utilidad.py.
        """
        self.reglas = reglas
        self.distancias = TablaDistancias(reglas.escenario)
        self.peso_posesion = peso_posesion
        self.peso_avance = peso_avance
        self.peso_carrera = peso_carrera
        self.peso_persecucion = peso_persecucion

    def _distancia_minima(self, estado: EstadoJuego, bando: str, destino) -> float:
        """Menor distancia de una unidad del bando al destino."""
        return min(
            self.distancias.distancia(posicion, destino)
            for unidad, posicion in estado.posiciones
            if self.reglas.bando_de(unidad) == bando
        )

    def puntaje(self, estado: EstadoJuego, bando: str) -> float:
        """
        Purpose: Puntaje heurístico del estado para un bando.
        Preconditions: bando es "A" o "B" y estado es un estado de la partida.
        Postconditions: Suma posesión (+), avance (−, distancia del portador a su base),
            carrera (−, distancia mínima al recurso en el suelo) y persecución (−, distancia
            mínima al portador rival).
        Complexity: tiempo O(U), espacio O(1) con U = unidades
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se valida mediante pruebas unitarias y de integración en test_utilidad.py.
        """
        total = 0.0
        if estado.portador is not None:
            posicion = estado.posicion_de(estado.portador)
            if self.reglas.bando_de(estado.portador) == bando:
                base = self.reglas.escenario.base_de(bando)
                total += self.peso_posesion
                total -= self.peso_avance * self.distancias.distancia(posicion, base)
            else:
                total -= self.peso_persecucion * self._distancia_minima(estado, bando, posicion)
        else:
            total -= self.peso_carrera * self._distancia_minima(estado, bando, estado.recurso)
        return total

    def utilidad(self, estado: EstadoJuego, bando_max: str) -> float:
        """
        Purpose: Valor del estado para el bando que maximiza.
        Preconditions: bando_max es "A" o "B".
        Postconditions: +UTILIDAD_VICTORIA si gana bando_max, −UTILIDAD_VICTORIA si gana el
            otro, 0 si es terminal sin ganador; si no, puntaje(max) − puntaje(min).
        Complexity: tiempo O(U), espacio O(1)
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se valida mediante pruebas unitarias y de integración en test_utilidad.py.
        """
        ganador = self.reglas.ganador(estado)
        if ganador is not None:
            return UTILIDAD_VICTORIA if ganador == bando_max else -UTILIDAD_VICTORIA
        if self.reglas.es_terminal(estado):
            return 0.0
        bando_min = "B" if bando_max == "A" else "A"
        return self.puntaje(estado, bando_max) - self.puntaje(estado, bando_min)
