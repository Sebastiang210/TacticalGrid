"""Información fija del mapa: catálogo de terrenos, grilla y bases."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

Posicion = tuple[int, int]  # (fila, columna)


@dataclass(frozen=True)
class TipoTerreno:
    """Tipo de terreno del catálogo; costo es None si no es transitable."""

    nombre: str
    transitable: bool
    costo: float | None


@dataclass(frozen=True)
class Escenario:
    """Mapa inmutable: dimensiones, catálogo de terrenos, grilla y bases."""

    filas: int
    columnas: int
    tipos_terreno: Mapping[str, TipoTerreno]
    terreno: tuple[tuple[str, ...], ...]
    bases: Mapping[str, Posicion]

    def __post_init__(self) -> None:
        """Envuelve los mapeos en MappingProxyType para que sean de solo lectura."""
        object.__setattr__(self, "tipos_terreno", MappingProxyType(dict(self.tipos_terreno)))
        object.__setattr__(self, "bases", MappingProxyType(dict(self.bases)))

    def dentro(self, pos: Posicion) -> bool:
        """True si pos está dentro de los límites del mapa."""
        fila, columna = pos
        return 0 <= fila < self.filas and 0 <= columna < self.columnas

    def tipo_en(self, pos: Posicion) -> TipoTerreno:
        """
        Purpose: Obtener el tipo de terreno de una celda.
        Preconditions: pos está dentro del mapa.
        Postconditions: Devuelve el TipoTerreno del catálogo; no modifica nada.
        Complexity: tiempo O(1), espacio O(1)
        Student validation:  Se prueba mediante los tests en /tests/test_cargador
        """
        if not self.dentro(pos):
            raise ValueError(f"La posición {pos} está fuera del mapa")
        fila, columna = pos
        return self.tipos_terreno[self.terreno[fila][columna]]

    def es_transitable(self, pos: Posicion) -> bool:
        """True si pos está dentro del mapa y su terreno es transitable."""
        return self.dentro(pos) and self.tipo_en(pos).transitable

    def costo(self, pos: Posicion) -> float:
        """
        Purpose: Costo de entrar a una celda (se cobra la celda destino).
        Preconditions: pos está dentro del mapa y su terreno es transitable.
        Postconditions: Devuelve el costo del catálogo; ValueError si no se cumple la
            precondición.
        Complexity: tiempo O(1), espacio O(1)
        Student validation:  Se prueba mediante los tests en /tests/test_cargador
        """
        tipo = self.tipo_en(pos)
        if not tipo.transitable or tipo.costo is None:
            raise ValueError(f"La celda {pos} ({tipo.nombre}) no es transitable")
        return tipo.costo

    @property
    def costo_minimo(self) -> float:
        """
        Purpose: Menor costo entre los terrenos transitables del catálogo.
        Preconditions: El catálogo tiene al menos un terreno transitable.
        Postconditions: Devuelve el mínimo; no modifica nada.
        Complexity: tiempo O(T), espacio O(1) con T = tipos de terreno
        Student validation:  Se prueba mediante los tests en /tests/test_cargador
        """
        return min(t.costo for t in self.tipos_terreno.values() if t.costo is not None)

    def base_de(self, bando: str) -> Posicion:
        """Posición de la base del bando indicado ("A" o "B")."""
        return self.bases[bando]
