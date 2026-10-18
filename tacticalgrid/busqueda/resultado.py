"""Resultado común de los algoritmos de búsqueda y reconstrucción del camino."""

from dataclasses import dataclass

from tacticalgrid.core.navegacion import EstadoNavegacion


Padres = dict[EstadoNavegacion, tuple[EstadoNavegacion, str, float] | None]


@dataclass(frozen=True)
class Resultado:
    """
    Camino encontrado (vacío si no hay éxito) y métricas de la búsqueda.

    orden_expansion son los estados en el orden en que se expandieron (uno por cada
    nodos_expandidos).
    """

    algoritmo: str
    exito: bool
    estados: tuple[EstadoNavegacion, ...]
    acciones: tuple[str, ...]
    costo: float
    nodos_expandidos: int
    nodos_generados: int
    max_frontera: int
    tiempo_ms: float
    orden_expansion: tuple[EstadoNavegacion, ...] = ()

    @property
    def movimientos(self) -> int:
        """Cantidad de pasos del camino."""
        return len(self.acciones)


def reconstruir_camino(
    padres: Padres, estado_final: EstadoNavegacion
) -> tuple[tuple[EstadoNavegacion, ...], tuple[str, ...], float]:
    """
    Purpose: Reconstruir el camino desde el estado inicial hasta estado_final.
    Preconditions: estado_final está en padres y la cadena de padres termina en un estado
        con valor None (el inicial).
    Postconditions: Devuelve (estados, acciones, costo); estados incluye el inicial y
        estado_final, len(estados) == len(acciones) + 1 y costo es la suma de los costo_paso.
    Complexity: tiempo O(L), espacio O(L) con L = largo del camino
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida mediante tests/test_no_informada.py::test_reconstruir_camino
    """
    estados = [estado_final]
    acciones: list[str] = []
    costo = 0.0
    paso = padres[estado_final]
    while paso is not None:
        padre, accion, costo_paso = paso
        estados.append(padre)
        acciones.append(accion)
        costo += costo_paso
        paso = padres[padre]
    estados.reverse()
    acciones.reverse()
    return tuple(estados), tuple(acciones), costo
