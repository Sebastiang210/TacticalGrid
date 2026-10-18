"""Búsquedas informadas en grafo: A* y Beam Search.

Siguen las mismas reglas de métricas que no_informada.py:
- La prueba de objetivo se hace al sacar un estado de la frontera.
- nodos_expandidos cuenta los estados a los que se les pidieron sucesores.
- nodos_generados empieza en 1 (el inicial) y suma los sucesores devueltos.
- max_frontera es el tamaño máximo que alcanzó la frontera.
"""

import heapq
import itertools
import math
from time import perf_counter

from tacticalgrid.busqueda.heuristicas import Heuristica
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
    orden_expansion: list[EstadoNavegacion],
) -> Resultado:
    """
    Purpose: Armar el Resultado de una búsqueda terminada, con o sin éxito.
    Preconditions: Si final no es None, está en padres; inicio viene de perf_counter().
    Postconditions: Con final, el camino reconstruido y exito True; sin final, exito False,
        camino vacío y costo 0. Las métricas se copian tal cual y orden_expansion
        queda como tupla.
    Complexity: tiempo O(L), espacio O(L) con L = largo del camino
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.   
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
        orden_expansion=tuple(orden_expansion),
    )


def a_estrella(
    problema: ProblemaNavegacion, heuristica: Heuristica, nombre_heuristica: str
) -> Resultado:
    """
    Purpose: Búsqueda A* (cola de prioridad por f = g + h).
    Preconditions: problema tiene costos positivos; heuristica es consistente.
    Postconditions: Devuelve un Resultado con algoritmo "A* (<nombre_heuristica>)"; si hay
        solución, es de costo mínimo. Empates en f se resuelven por menor h y luego por orden
        de generación. Un g menor se reinserta y la entrada vieja se descarta al sacarla
        (eliminación perezosa). Un sucesor con h infinita cuenta como generado pero no entra a
        la frontera. Nunca lanza si no hay solución.
    Complexity: tiempo O(V·b·log(V·b)), espacio O(V·b) por las entradas viejas del heap,
        con b ≤ 4 el factor de ramificación y V los estados
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida mediante tests/informada/test_informada.py::test_a_estrella
    """
    algoritmo = f"A* ({nombre_heuristica})"
    inicio = perf_counter()
    inicial = problema.inicial()
    h_inicial = heuristica(inicial)
    contador = itertools.count(1)
    frontera: list[tuple[float, float, int, EstadoNavegacion]] = [
        (h_inicial, h_inicial, 0, inicial)
    ]
    mejor_g: dict[EstadoNavegacion, float] = {inicial: 0.0}
    padres: Padres = {inicial: None}
    cerrados: set[EstadoNavegacion] = set()
    expandidos, generados, max_frontera = 0, 1, 1
    orden: list[EstadoNavegacion] = []  
    while frontera:
        f, h, _, estado = heapq.heappop(frontera)
        if estado in cerrados or f > mejor_g[estado] + h:
            continue
        if problema.es_objetivo(estado):
            return _resultado(
                algoritmo, padres, estado, expandidos, generados, max_frontera, inicio, orden
            )
        cerrados.add(estado)
        orden.append(estado)
        expandidos += 1
        g = mejor_g[estado]
        sucesores = problema.sucesores(estado)
        generados += len(sucesores)
        for accion, sucesor, costo in sucesores:
            if sucesor in cerrados:
                continue
            h_sucesor = heuristica(sucesor)
            if h_sucesor == math.inf:
                continue
            nuevo_g = g + costo
            if sucesor not in mejor_g or nuevo_g < mejor_g[sucesor]:
                mejor_g[sucesor] = nuevo_g
                padres[sucesor] = (estado, accion, costo)
                heapq.heappush(
                    frontera, (nuevo_g + h_sucesor, h_sucesor, next(contador), sucesor)
                )
        max_frontera = max(max_frontera, len(frontera))
    return _resultado(algoritmo, padres, None, expandidos, generados, max_frontera, inicio, orden)


def beam(
    problema: ProblemaNavegacion, heuristica: Heuristica, nombre_heuristica: str, k: int
) -> Resultado:
    """
    Purpose: Beam Search: A* con la frontera limitada a los k mejores estados (R&N 4.ª ed.).
    Preconditions: problema tiene costos positivos; k >= 1 (si no, ValueError).
    Postconditions: Devuelve un Resultado con algoritmo "Beam k=<k> (<nombre_heuristica>)".
        No es completa ni óptima: tras cada expansión se conservan solo los k mejores por
        (f, h, contador) y el resto se descarta (puede volver a generarse después). Un sucesor
        se descarta si ya fue expandido, si su h es infinita o si ya está en la frontera con
        g menor o igual. Nunca lanza si no hay solución.
    Complexity: tiempo O(V·(k+b)·log(k+b)), espacio O(V) para g, padres y expandidos más
        O(k+b) para la frontera, con b ≤ 4 el factor de ramificación y V los estados
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida mediante tests/informada/test_informada.py::test_beam
    """
    if k < 1:
        raise ValueError(f"k debe ser al menos 1, no {k!r}")
    algoritmo = f"Beam k={k} ({nombre_heuristica})"
    inicio = perf_counter()
    inicial = problema.inicial()
    h_inicial = heuristica(inicial)
    contador = itertools.count(1)
    frontera: dict[EstadoNavegacion, tuple[float, float, int]] = {
        inicial: (h_inicial, h_inicial, 0)
    }
    g: dict[EstadoNavegacion, float] = {inicial: 0.0}
    padres: Padres = {inicial: None}
    cerrados: set[EstadoNavegacion] = set()
    expandidos, generados, max_frontera = 0, 1, 1
    orden: list[EstadoNavegacion] = []  
    while frontera:
        estado = min(frontera, key=frontera.__getitem__)
        del frontera[estado]
        if problema.es_objetivo(estado):
            return _resultado(
                algoritmo, padres, estado, expandidos, generados, max_frontera, inicio, orden
            )
        cerrados.add(estado)
        orden.append(estado)
        expandidos += 1
        sucesores = problema.sucesores(estado)
        generados += len(sucesores)
        for accion, sucesor, costo in sucesores:
            if sucesor in cerrados:
                continue
            h_sucesor = heuristica(sucesor)
            if h_sucesor == math.inf:
                continue
            nuevo_g = g[estado] + costo
            if sucesor in frontera and g[sucesor] <= nuevo_g:
                continue
            g[sucesor] = nuevo_g
            padres[sucesor] = (estado, accion, costo)
            frontera[sucesor] = (nuevo_g + h_sucesor, h_sucesor, next(contador))
        max_frontera = max(max_frontera, len(frontera))
        if len(frontera) > k:
            frontera = dict(heapq.nsmallest(k, frontera.items(), key=lambda par: par[1]))
    return _resultado(algoritmo, padres, None, expandidos, generados, max_frontera, inicio, orden)
