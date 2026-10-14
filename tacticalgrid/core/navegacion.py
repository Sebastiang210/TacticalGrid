"""Estado de una unidad que navega por el mapa."""

from dataclasses import dataclass

from tacticalgrid.core.escenario import Posicion


@dataclass(frozen=True)
class EstadoNavegacion:
    """Posición de la unidad y si ya lleva el recurso; igualdad y hash por valor."""

    fila: int
    columna: int
    lleva_recurso: bool

    @property
    def posicion(self) -> Posicion:
        """Posición (fila, columna) del estado."""
        return (self.fila, self.columna)
