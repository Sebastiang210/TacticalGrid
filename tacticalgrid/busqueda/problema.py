"""Problema de navegación: interfaz común para todos los algoritmos de búsqueda."""

from collections.abc import Iterable

from tacticalgrid.carga.cargador import DatosEscenario
from tacticalgrid.config import DESPLAZAMIENTOS, ORDEN_DIRECCIONES_POR_DEFECTO
from tacticalgrid.core.escenario import Escenario, Posicion
from tacticalgrid.core.navegacion import EstadoNavegacion

Sucesor = tuple[str, EstadoNavegacion, float] 


class ProblemaNavegacion:
    """
    Navegación de una unidad por el mapa; solo cuenta el terreno (otras unidades no estorban).

    Expone escenario, unidad (id), objetivo (Posicion o None) y es_mision (bool).
    """

    def __init__(
        self,
        datos: DatosEscenario,
        orden_direcciones: Iterable[str] = ORDEN_DIRECCIONES_POR_DEFECTO,
    ) -> None:
        """
        Purpose: Construir el problema a partir de un escenario cargado.
        Preconditions: datos.prueba existe, su modo es "busqueda" y unidad_inicio es una
            unidad de datos.unidades; orden_direcciones es una permutación de las 4 direcciones.
        Postconditions: Queda listo para inicial/sucesores/costo/es_objetivo; lanza ValueError
            si alguna precondición no se cumple.
        Complexity: tiempo O(U), espacio O(1) con U = unidades
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se valida mediante tests/test_problema
        """
        orden = tuple(orden_direcciones)
        if len(orden) != len(DESPLAZAMIENTOS) or set(orden) != set(DESPLAZAMIENTOS):
            raise ValueError(
                f"orden_direcciones debe ser una permutación de {tuple(DESPLAZAMIENTOS)}, "
                f"no {orden!r}"
            )
        prueba = datos.prueba
        if prueba is None or prueba.modo != "busqueda":
            modo = "ausente" if prueba is None else repr(prueba.modo)
            raise ValueError(
                f"El problema de navegación requiere una prueba en modo 'busqueda' "
                f"(prueba: {modo})"
            )
        unidad = next((u for u in datos.unidades if u.id == prueba.unidad_inicio), None)
        if unidad is None:
            raise ValueError(
                f"La unidad de inicio {prueba.unidad_inicio!r} no existe en el escenario"
            )
        self._orden = orden
        self._inicio: Posicion = unidad.posicion
        self._bando = unidad.bando
        self._recurso: Posicion = datos.recurso
        self._hay_portador = datos.portador is not None
        self._lleva_al_inicio = datos.portador == unidad.id
        self.escenario: Escenario = datos.escenario
        self.unidad: str = unidad.id
        self.objetivo: Posicion | None = prueba.objetivo
        self.es_mision: bool = prueba.mision == "llevar_recurso"

    def inicial(self) -> EstadoNavegacion:
        """
        Purpose: Estado de partida de la búsqueda.
        Preconditions: Ninguna.
        Postconditions: Devuelve la posición de la unidad de inicio; lleva_recurso es True
            solo si esa unidad es el portador del recurso.
        Complexity: tiempo O(1), espacio O(1)
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se valida mediante tests/test_problema
        """
        fila, columna = self._inicio
        return EstadoNavegacion(fila, columna, self._lleva_al_inicio)

    def sucesores(self, estado: EstadoNavegacion) -> list[Sucesor]:
        """
        Purpose: Estados alcanzables en un paso, con su acción y costo.
        Preconditions: estado está dentro del mapa y sobre terreno transitable.
        Postconditions: Lista de (accion, sucesor, costo) en el orden de direcciones
            configurado, solo con celdas dentro del mapa y transitables. Entrar a la celda del
            recurso sin portador pone lleva_recurso en True; el indicador nunca vuelve a False.
        Complexity: tiempo O(1), espacio O(1) (4 direcciones)
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se valida mediante tests/test_problema
        """
        resultado: list[Sucesor] = []
        for accion in self._orden:
            d_fila, d_columna = DESPLAZAMIENTOS[accion]
            destino = (estado.fila + d_fila, estado.columna + d_columna)
            if not self.escenario.es_transitable(destino):
                continue
            lleva = estado.lleva_recurso or (
                not self._hay_portador and destino == self._recurso
            )
            sucesor = EstadoNavegacion(destino[0], destino[1], lleva)
            resultado.append((accion, sucesor, self.costo(estado, sucesor)))
        return resultado

    def costo(self, estado: EstadoNavegacion, sucesor: EstadoNavegacion) -> float:
        """
        Purpose: Costo de pasar de estado a sucesor.
        Preconditions: sucesor es un vecino transitable de estado.
        Postconditions: Devuelve el costo del terreno de la celda destino.
        Complexity: tiempo O(1), espacio O(1)
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se valida mediante tests/test_problema
        """
        return self.escenario.costo(sucesor.posicion)

    def es_objetivo(self, estado: EstadoNavegacion) -> bool:
        """
        Purpose: Decidir si estado cumple la meta de la prueba.
        Preconditions: Ninguna.
        Postconditions: En misión "llevar_recurso": True si está en la base del bando de la
            unidad y lleva el recurso. Si no: True si está en prueba.objetivo, con o sin recurso.
        Complexity: tiempo O(1), espacio O(1)
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se valida mediante tests/test_problema
        """
        if self.es_mision:
            return estado.lleva_recurso and estado.posicion == self.escenario.base_de(self._bando)
        return estado.posicion == self.objetivo
