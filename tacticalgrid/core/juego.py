"""Estado de la partida, jugadas y reglas deterministas del juego por turnos."""

from collections.abc import Iterable
from dataclasses import dataclass

from tacticalgrid.carga.cargador import DatosEscenario
from tacticalgrid.config import DESPLAZAMIENTOS, ORDEN_DIRECCIONES_POR_DEFECTO
from tacticalgrid.core.escenario import Escenario, Posicion


@dataclass(frozen=True)
class Jugada:
    """Mover una unidad en una dirección, o pasar (unidad y dirección en None)."""

    unidad: str | None
    direccion: str | None

    @property
    def es_pasar(self) -> bool:
        """True si la jugada es pasar el turno."""
        return self.unidad is None

    def __str__(self) -> str:
        return "pasar" if self.es_pasar else f"{self.unidad} {self.direccion}"


PASAR = Jugada(None, None)


@dataclass(frozen=True)
class EstadoJuego:
    """
    Estado dinámico de la partida; igualdad y hash por valor.

    posiciones va siempre ordenada por id. Exactamente uno de recurso (casilla libre) y
    portador (id de quien lo lleva) tiene valor.
    """

    posiciones: tuple[tuple[str, Posicion], ...]
    recurso: Posicion | None
    portador: str | None
    turno: str
    turnos_jugados: int

    def __post_init__(self) -> None:
        """Verifica la invariante: exactamente uno de recurso / portador tiene valor."""
        if (self.recurso is None) == (self.portador is None):
            raise ValueError(
                "Exactamente uno de recurso y portador debe tener valor "
                f"(recurso={self.recurso}, portador={self.portador})"
            )

    def posicion_de(self, unidad: str) -> Posicion:
        """
        Purpose: Posición de una unidad.
        Preconditions: unidad es el id de una unidad del estado.
        Postconditions: Devuelve su (fila, columna); ValueError si el id no existe.
        Complexity: tiempo O(U), espacio O(1) con U = unidades
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se valida mediante tests/test_juego
        """
        for id_unidad, posicion in self.posiciones:
            if id_unidad == unidad:
                return posicion
        raise ValueError(f"La unidad {unidad!r} no existe en el estado")

    @property
    def ocupadas(self) -> frozenset[Posicion]:
        """
        Purpose: Casillas ocupadas por alguna unidad (aliada o rival).
        Preconditions: Ninguna.
        Postconditions: Devuelve un frozenset de posiciones; no modifica nada.
        Complexity: tiempo O(U), espacio O(U)
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se valida mediante tests/test_juego
        """
        return frozenset(posicion for _, posicion in self.posiciones)


def _rival(bando: str) -> str:
    return "B" if bando == "A" else "A"


class ReglasJuego:
    """Reglas deterministas de la partida; no guardan estado, solo transforman EstadoJuego."""

    def __init__(
        self,
        datos: DatosEscenario,
        orden_direcciones: Iterable[str] = ORDEN_DIRECCIONES_POR_DEFECTO,
    ) -> None:
        """
        Purpose: Construir las reglas a partir de un escenario cargado.
        Preconditions: orden_direcciones es una permutación de las 4 direcciones.
        Postconditions: Quedan listas las operaciones sobre estados; ValueError si el orden
            de direcciones no es una permutación válida.
        Complexity: tiempo O(U), espacio O(U) con U = unidades
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se valida mediante tests/test_juego
        """
        orden = tuple(orden_direcciones)
        if len(orden) != len(DESPLAZAMIENTOS) or set(orden) != set(DESPLAZAMIENTOS):
            raise ValueError(
                f"orden_direcciones debe ser una permutación de {tuple(DESPLAZAMIENTOS)}, "
                f"no {orden!r}"
            )
        self._datos = datos
        self._orden = orden
        self._bandos: dict[str, str] = {u.id: u.bando for u in datos.unidades}
        self.escenario: Escenario = datos.escenario
        self.limite_turnos: int = datos.limite_turnos

    def bando_de(self, unidad: str) -> str:
        """Bando ("A" o "B") de la unidad con ese id."""
        return self._bandos[unidad]

    def estado_inicial(self) -> EstadoJuego:
        """
        Purpose: Estado de partida del escenario.
        Preconditions: Ninguna.
        Postconditions: Posiciones ordenadas por id; si el escenario trae portador, el recurso
            queda en None y viaja con él; turno del escenario y 0 turnos jugados.
        Complexity: tiempo O(U log U), espacio O(U)
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se valida mediante tests/test_juego
        """
        datos = self._datos
        posiciones = tuple(sorted((u.id, u.posicion) for u in datos.unidades))
        portador = datos.portador
        return EstadoJuego(
            posiciones=posiciones,
            recurso=None if portador is not None else datos.recurso,
            portador=portador,
            turno=datos.turno,
            turnos_jugados=0,
        )

    def ganador(self, estado: EstadoJuego) -> str | None:
        """
        Purpose: Bando ganador, si lo hay.
        Preconditions: Ninguna.
        Postconditions: Devuelve el bando del portador si este está sobre la base de su propio
            bando; si no, None.
        Complexity: tiempo O(U), espacio O(1)
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se valida mediante tests/test_juego
        """
        if estado.portador is None:
            return None
        bando = self._bandos[estado.portador]
        if estado.posicion_de(estado.portador) == self.escenario.base_de(bando):
            return bando
        return None

    def es_terminal(self, estado: EstadoJuego) -> bool:
        """
        Purpose: Decidir si la partida terminó (victoria o límite de turnos).
        Preconditions: Ninguna.
        Postconditions: True si hay ganador o turnos_jugados >= limite_turnos.
        Complexity: tiempo O(U), espacio O(1)
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se valida mediante tests/test_juego
        """
        return self.ganador(estado) is not None or estado.turnos_jugados >= self.limite_turnos

    def _destino(self, estado: EstadoJuego, unidad: str, direccion: str) -> Posicion | None:
        """Destino legal de mover la unidad en esa dirección, o None si no es legal."""
        fila, columna = estado.posicion_de(unidad)
        d_fila, d_columna = DESPLAZAMIENTOS[direccion]
        destino = (fila + d_fila, columna + d_columna)
        if not self.escenario.es_transitable(destino) or destino in estado.ocupadas:
            return None
        if destino == self.escenario.base_de(_rival(self._bandos[unidad])):
            return None
        return destino

    def jugadas_legales(self, estado: EstadoJuego) -> list[Jugada]:
        """
        Purpose: Jugadas que puede hacer el bando en turno.
        Preconditions: Ninguna.
        Postconditions: [] si el estado es terminal. Si no, movimientos por id de unidad
            ascendente y dirección en el orden configurado (destino dentro del mapa,
            transitable, libre y distinto de la base rival), y PASAR al final.
        Complexity: tiempo O(U) (4 direcciones por unidad), espacio O(U)
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se valida mediante tests/test_juego
        """
        if self.es_terminal(estado):
            return []
        jugadas = [
            Jugada(unidad, direccion)
            for unidad, _ in estado.posiciones
            if self._bandos[unidad] == estado.turno
            for direccion in self._orden
            if self._destino(estado, unidad, direccion) is not None
        ]
        jugadas.append(PASAR)
        return jugadas

    def aplicar(self, estado: EstadoJuego, jugada: Jugada) -> EstadoJuego:
        """
        Purpose: Resultado de hacer una jugada, sin modificar el estado original.
        Preconditions: estado no es terminal y jugada está en jugadas_legales(estado).
        Postconditions: Devuelve un EstadoJuego nuevo tras, en orden: mover (el recurso viaja
            con el portador), recogida (solo quien entra a la casilla del recurso),
            intercepción (solo quien se mueve junto al portador rival) y cambio de turno con
            turnos_jugados + 1. ValueError si no se cumplen las precondiciones.
        Complexity: tiempo O(U), espacio O(U)
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se valida mediante tests/test_juego
        """
        if self.es_terminal(estado):
            raise ValueError("No se puede jugar sobre un estado terminal")
        if jugada not in self.jugadas_legales(estado):
            raise ValueError(f"Jugada ilegal en este estado: {jugada}")

        posiciones = dict(estado.posiciones)
        recurso = estado.recurso
        portador = estado.portador

        if not jugada.es_pasar:
            destino = self._destino(estado, jugada.unidad, jugada.direccion)
            posiciones[jugada.unidad] = destino  

            if portador is None and destino == recurso: 
                portador, recurso = jugada.unidad, None

            if (  
                portador is not None
                and self._bandos[portador] != self._bandos[jugada.unidad]
                and _son_vecinas(destino, posiciones[portador])
            ):
                portador = jugada.unidad

        return EstadoJuego(
            posiciones=tuple(sorted(posiciones.items())),
            recurso=recurso,
            portador=portador,
            turno=_rival(estado.turno),
            turnos_jugados=estado.turnos_jugados + 1,
        )


def _son_vecinas(a: Posicion, b: Posicion) -> bool:
    """True si a y b son vecinas ortogonales (distancia de Manhattan 1)."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1
