"""Búsquedas no informadas en grafo: BFS, DFS y UCS.

Reglas comunes para que las métricas sean comparables:
- La prueba de objetivo se hace al sacar un estado de la frontera.
- nodos_expandidos cuenta los estados a los que se les pidieron sucesores.
- nodos_generados empieza en 1 (el inicial) y suma los sucesores devueltos.
- max_frontera es el tamaño máximo que alcanzó la frontera.
"""

import heapq
import itertools
from collections import deque
from time import perf_counter

from tacticalgrid.busqueda.problema import ProblemaNavegacion
from tacticalgrid.busqueda.resultado import Padres, Resultado, reconstruir_camino
from tacticalgrid.core.navegacion import EstadoNavegacion


def _resultado(
    algoritmo: str,
    padres: Padres,
    final: EstadoNavegacion | None,
    expandidos: int,
    generados: int,
    max_frontera: int,
    inicio: float,
) -> Resultado:
    """
    Purpose: Armar el Resultado de una búsqueda terminada, con o sin éxito.
    Preconditions: Si final no es None, está en padres; inicio viene de perf_counter().
    Postconditions: Con final, el camino reconstruido y exito True; sin final, exito False,
        camino vacío y costo 0. Las métricas se copian tal cual.
    Complexity: tiempo O(L), espacio O(L) con L = largo del camino
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida mediatne tests/test_no_informada.py
    """
    if final is None:
        estados, acciones, costo = (), (), 0.0
    else:
        estados, acciones, costo = reconstruir_camino(padres, final)
    return Resultado(
        algoritmo=algoritmo,
        exito=final is not None,
        estados=estados,
        acciones=acciones,
        costo=costo,
        nodos_expandidos=expandidos,
        nodos_generados=generados,
        max_frontera=max_frontera,
        tiempo_ms=(perf_counter() - inicio) * 1000,
    )


def bfs(problema: ProblemaNavegacion) -> Resultado:
    """
    Purpose: Búsqueda en anchura (frontera FIFO); minimiza la cantidad de movimientos.
    Preconditions: problema es un ProblemaNavegacion válido.
    Postconditions: Devuelve un Resultado; si hay solución, es una de menor cantidad de
        movimientos (no necesariamente de menor costo). Cada estado se encola a lo sumo
        una vez (se marca como alcanzado al generarse). Nunca lanza si no hay solución.
    Complexity: tiempo O(b^d) acotado por O(V), espacio O(b^d) acotado por O(V), con
        b ≤ 4 el factor de ramificación, d la profundidad de la solución y V los estados
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida mediante tests/test_no_informada.py
    """
    inicio = perf_counter()
    inicial = problema.inicial()
    frontera = deque([inicial])
    padres: Padres = {inicial: None}
    expandidos, generados, max_frontera = 0, 1, 1
    while frontera:
        estado = frontera.popleft()
        if problema.es_objetivo(estado):
            return _resultado("BFS", padres, estado, expandidos, generados, max_frontera, inicio)
        expandidos += 1
        sucesores = problema.sucesores(estado)
        generados += len(sucesores)
        for accion, sucesor, costo in sucesores:
            if sucesor not in padres:
                padres[sucesor] = (estado, accion, costo)
                frontera.append(sucesor)
        max_frontera = max(max_frontera, len(frontera))
    return _resultado("BFS", padres, None, expandidos, generados, max_frontera, inicio)


def dfs(problema: ProblemaNavegacion) -> Resultado:
    """
    Purpose: Búsqueda en profundidad (frontera LIFO) que sigue el orden de direcciones.
    Preconditions: problema es un ProblemaNavegacion válido.
    Postconditions: Devuelve un Resultado; el camino no es necesariamente el más corto ni el
        más barato. Los sucesores se apilan en orden inverso para explorar primero la primera
        dirección; un estado se marca como visitado (y se fija su padre) al sacarlo. Nunca
        lanza si no hay solución.
    Complexity: tiempo O(b^m) acotado por O(V), espacio O(V) por los visitados (frontera
        O(b·m)), con b ≤ 4, m la profundidad máxima y V los estados
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida mediante tests/test_no_informada.py
    """
    inicio = perf_counter()
    frontera: list[tuple[EstadoNavegacion, tuple[EstadoNavegacion, str, float] | None]] = [
        (problema.inicial(), None)
    ]
    padres: Padres = {}
    expandidos, generados, max_frontera = 0, 1, 1
    while frontera:
        estado, paso = frontera.pop()
        if estado in padres:
            continue
        padres[estado] = paso
        if problema.es_objetivo(estado):
            return _resultado("DFS", padres, estado, expandidos, generados, max_frontera, inicio)
        expandidos += 1
        sucesores = problema.sucesores(estado)
        generados += len(sucesores)
        for accion, sucesor, costo in reversed(sucesores):
            if sucesor not in padres:
                frontera.append((sucesor, (estado, accion, costo)))
        max_frontera = max(max_frontera, len(frontera))
    return _resultado("DFS", padres, None, expandidos, generados, max_frontera, inicio)


def ucs(problema: ProblemaNavegacion) -> Resultado:
    """
    Purpose: Búsqueda de costo uniforme (cola de prioridad por costo acumulado g).
    Preconditions: problema es un ProblemaNavegacion válido con costos positivos.
    Postconditions: Devuelve un Resultado; si hay solución, es de costo mínimo. Los empates
        en g se resuelven por orden de generación. Si se encuentra un g menor para un estado
        en la frontera se inserta de nuevo y la entrada vieja se descarta al sacarla
        (eliminación perezosa). Nunca lanza si no hay solución.
    Complexity: tiempo O(V·b·log(V·b)), espacio O(V·b) por las entradas viejas del heap,
        con b ≤ 4 el factor de ramificación y V los estados
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida mediante tests/test_no_informada.py
    """
    inicio = perf_counter()
    inicial = problema.inicial()
    contador = itertools.count(1)
    frontera: list[tuple[float, int, EstadoNavegacion]] = [(0.0, 0, inicial)]
    mejor_g: dict[EstadoNavegacion, float] = {inicial: 0.0}
    padres: Padres = {inicial: None}
    cerrados: set[EstadoNavegacion] = set()
    expandidos, generados, max_frontera = 0, 1, 1
    while frontera:
        g, _, estado = heapq.heappop(frontera)
        if estado in cerrados or g > mejor_g[estado]:
            continue
        if problema.es_objetivo(estado):
            return _resultado("UCS", padres, estado, expandidos, generados, max_frontera, inicio)
        cerrados.add(estado)
        expandidos += 1
        sucesores = problema.sucesores(estado)
        generados += len(sucesores)
        for accion, sucesor, costo in sucesores:
            nuevo_g = g + costo
            if sucesor in cerrados:
                continue
            if sucesor not in mejor_g or nuevo_g < mejor_g[sucesor]:
                mejor_g[sucesor] = nuevo_g
                padres[sucesor] = (estado, accion, costo)
                heapq.heappush(frontera, (nuevo_g, next(contador), sucesor))
        max_frontera = max(max_frontera, len(frontera))
    return _resultado("UCS", padres, None, expandidos, generados, max_frontera, inicio)
