"""Heurísticas admisibles y consistentes para el problema de navegación."""

import math
from collections import deque
from collections.abc import Callable

from tacticalgrid.busqueda.problema import ProblemaNavegacion
from tacticalgrid.config import DESPLAZAMIENTOS
from tacticalgrid.core.escenario import Escenario, Posicion
from tacticalgrid.core.navegacion import EstadoNavegacion

Heuristica = Callable[[EstadoNavegacion], float]
Distancia = Callable[[Posicion, Posicion], float]


def _manhattan(a: Posicion, b: Posicion) -> float:
    """Distancia Manhattan entre dos posiciones."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _tabla_pasos(escenario: Escenario, destino: Posicion) -> dict[Posicion, int]:
    """
    Purpose: Movimientos mínimos desde cada celda hasta destino, rodeando lo no transitable.
    Preconditions: destino está dentro del mapa.
    Postconditions: Devuelve celda -> número de movimientos solo para las celdas transitables
        que llegan a destino; vacío si destino no es transitable. Ignora costos (BFS desde
        destino; vale como distancia hacia destino porque los movimientos son simétricos).
    Complexity: tiempo O(F·C), espacio O(F·C) con F filas y C columnas
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    """
    if not escenario.es_transitable(destino):
        return {}
    tabla = {destino: 0}
    cola = deque([destino])
    while cola:
        celda = cola.popleft()
        for d_fila, d_columna in DESPLAZAMIENTOS.values():
            vecina = (celda[0] + d_fila, celda[1] + d_columna)
            if vecina not in tabla and escenario.es_transitable(vecina):
                tabla[vecina] = tabla[celda] + 1
                cola.append(vecina)
    return tabla


def _construir(problema: ProblemaNavegacion, dist: Distancia) -> Heuristica:
    """
    Purpose: Armar h(n) a partir de una distancia entre posiciones, según el tipo de prueba.
    Preconditions: dist(a, b) nunca supera los movimientos reales de a a b (math.inf si no se
        puede llegar) y cambia a lo sumo en 1 por movimiento.
    Postconditions: Prueba normal: dist(n, objetivo) * c_min. Misión: si n lleva el recurso,
        dist(n, base) * c_min; si no y nadie puede recogerlo, math.inf; si no,
        (dist(n, recurso) + dist(recurso, base)) * c_min. c_min = escenario.costo_minimo.
    Complexity: tiempo O(1) al crearla y por llamada (más lo que cueste dist), espacio O(1)
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    """
    c_min = problema.escenario.costo_minimo
    if not problema.es_mision:
        objetivo = problema.objetivo

        def h_prueba(estado: EstadoNavegacion) -> float:
            return dist(estado.posicion, objetivo) * c_min

        return h_prueba

    base = problema.base
    recurso = problema.recurso_disponible
    recurso_a_base = dist(recurso, base) if recurso is not None else math.inf

    def h_mision(estado: EstadoNavegacion) -> float:
        if estado.lleva_recurso:
            return dist(estado.posicion, base) * c_min
        if recurso is None:
            return math.inf
        return (dist(estado.posicion, recurso) + recurso_a_base) * c_min

    return h_mision


def h_manhattan(problema: ProblemaNavegacion) -> Heuristica:
    """
    Purpose: Heurística h1: distancia Manhattan por el costo mínimo de terreno.
    Preconditions: problema es un ProblemaNavegacion válido.
    Postconditions: Devuelve h admisible y consistente (cada paso cuesta >= c_min y la
        distancia Manhattan cambia a lo sumo en 1 por paso); h = 0 en los objetivos.
    Complexity: tiempo O(1) al crearla y por llamada, espacio O(1)
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida mediante tests/informada/test_heuristicas.py::test_h_manhattan
    """
    return _construir(problema, _manhattan)


def h_pasos(problema: ProblemaNavegacion) -> Heuristica:
    """
    Purpose: Heurística h2: movimientos mínimos rodeando muros por el costo mínimo de terreno.
    Preconditions: problema es un ProblemaNavegacion válido.
    Postconditions: Devuelve h admisible y consistente, con h_pasos >= h_manhattan en todo
        estado; math.inf en celdas que no llegan al destino. Las tablas (objetivo, o base y
        recurso en misión) se calculan una sola vez, al crearla.
    Complexity: tiempo O(F·C) al crearla y O(1) por llamada, espacio O(F·C), con F filas y
        C columnas
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida mediante tests/informada/test_heuristicas.py::test_h_pasos
    """
    if problema.es_mision:
        destinos = [problema.base, problema.recurso_disponible]
    else:
        destinos = [problema.objetivo]
    tablas = {
        destino: _tabla_pasos(problema.escenario, destino)
        for destino in destinos
        if destino is not None
    }

    def dist(a: Posicion, b: Posicion) -> float:
        return tablas[b].get(a, math.inf)

    return _construir(problema, dist)
