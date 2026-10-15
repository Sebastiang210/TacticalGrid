"""Tabla de distancias mínimas entre celdas (Dijkstra desde cada celda transitable)."""

import heapq

from tacticalgrid.config import DESPLAZAMIENTOS, DISTANCIA_INALCANZABLE
from tacticalgrid.core.escenario import Escenario, Posicion


class TablaDistancias:
    """Distancias de menor costo entre celdas; las unidades no bloquean el camino."""

    def __init__(self, escenario: Escenario) -> None:
        """
        Purpose: Precalcular la distancia entre todo par de celdas transitables.
        Preconditions: escenario es un mapa válido.
        Postconditions: Queda lista la tabla; mover de p a v cuesta escenario.costo(v), igual
            que en la navegación.
        Complexity: tiempo O(N * N log N), espacio O(N^2) con N = celdas transitables
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se  verifico con pruebas unitarias y de integración en test_distancias.py.
        """
        self._escenario = escenario
        celdas = [
            (fila, columna)
            for fila in range(escenario.filas)
            for columna in range(escenario.columnas)
            if escenario.es_transitable((fila, columna))
        ]
        self._tabla: dict[Posicion, dict[Posicion, float]] = {
            origen: self._dijkstra(origen) for origen in celdas
        }

    def _dijkstra(self, origen: Posicion) -> dict[Posicion, float]:
        """Distancias desde origen a todas las celdas alcanzables."""
        distancias: dict[Posicion, float] = {}
        frontera: list[tuple[float, Posicion]] = [(0.0, origen)]
        while frontera:
            costo, pos = heapq.heappop(frontera)
            if pos in distancias:
                continue
            distancias[pos] = costo
            for d_fila, d_columna in DESPLAZAMIENTOS.values():
                vecino = (pos[0] + d_fila, pos[1] + d_columna)
                if vecino not in distancias and self._escenario.es_transitable(vecino):
                    heapq.heappush(frontera, (costo + self._escenario.costo(vecino), vecino))
        return distancias

    def distancia(self, a: Posicion, b: Posicion) -> float:
        """
        Purpose: Costo mínimo de ir de a a b.
        Preconditions: Ninguna.
        Postconditions: 0 si a == b; DISTANCIA_INALCANZABLE si b no es alcanzable desde a (o
            alguna no es transitable); si no, el costo mínimo.
        Complexity: tiempo O(1), espacio O(1)
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se verificó con pruebas unitarias y de integración, incluyendo casos de celdas aisladas y distancias en test_distancias.py.
        """
        if a == b:
            return 0.0
        return self._tabla.get(a, {}).get(b, DISTANCIA_INALCANZABLE)
