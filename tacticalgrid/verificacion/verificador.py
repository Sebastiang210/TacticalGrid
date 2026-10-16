"""Verificación independiente de caminos de búsqueda y de partidas completas."""

import math
from collections.abc import Iterable
from dataclasses import dataclass

from tacticalgrid.adversarial.partida import Partida
from tacticalgrid.busqueda.resultado import Resultado
from tacticalgrid.carga.cargador import DatosEscenario
from tacticalgrid.config import DESPLAZAMIENTOS, ORDEN_DIRECCIONES_POR_DEFECTO
from tacticalgrid.core.juego import ReglasJuego


@dataclass(frozen=True)
class ReporteVerificacion:
    """Resultado de una verificación; valido es True si y solo si no hay errores."""

    valido: bool
    errores: tuple[str, ...]
    costo_recalculado: float | None


def _reporte(errores: list[str], costo: float | None = None) -> ReporteVerificacion:
    return ReporteVerificacion(not errores, tuple(errores), costo)


def verificar_camino(datos: DatosEscenario, resultado: Resultado) -> ReporteVerificacion:
    """
    Purpose: Comprobar, sin usar ProblemaNavegacion ni los algoritmos, que un Resultado de
        búsqueda cumple las reglas de movimiento, el costo y la meta de la prueba.
    Preconditions: datos.prueba existe y su modo es "busqueda".
    Postconditions: Devuelve un ReporteVerificacion con TODOS los errores encontrados (con el
        número de paso) y el costo recalculado (None si algún destino no es transitable);
        ValueError si no se cumple la precondición.
    Complexity: tiempo O(L), espacio O(L) con L = largo del camino
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida mediante tests/test_verificador.py
    """
    prueba = datos.prueba
    if prueba is None or prueba.modo != "busqueda":
        modo = "ausente" if prueba is None else repr(prueba.modo)
        raise ValueError(f"La verificación de caminos requiere una prueba 'busqueda' ({modo})")
    escenario = datos.escenario
    errores: list[str] = []

    if not resultado.exito:
        if resultado.estados:
            errores.append("Sin éxito, pero el resultado trae estados")
        if resultado.acciones:
            errores.append("Sin éxito, pero el resultado trae acciones")
        if resultado.costo != 0:
            errores.append(f"Sin éxito, pero el costo es {resultado.costo} (debe ser 0)")
        return _reporte(errores, 0.0)

    estados, acciones = resultado.estados, resultado.acciones
    if len(estados) != len(acciones) + 1:
        errores.append(
            f"Hay {len(estados)} estados y {len(acciones)} acciones "
            "(deben ser estados = acciones + 1)"
        )
    if not estados:
        errores.append("El resultado con éxito no tiene estados")
        return _reporte(errores, None)

    unidad = next((u for u in datos.unidades if u.id == prueba.unidad_inicio), None)
    if unidad is None:
        errores.append(f"La unidad de inicio {prueba.unidad_inicio!r} no existe")
    else:
        if estados[0].posicion != unidad.posicion:
            errores.append(
                f"Paso 0: el inicio es {estados[0].posicion}, debía ser {unidad.posicion}"
            )
        lleva_inicial = datos.portador == unidad.id
        if estados[0].lleva_recurso != lleva_inicial:
            errores.append(
                f"Paso 0: lleva_recurso es {estados[0].lleva_recurso}, debía ser {lleva_inicial}"
            )

    costo = 0.0
    costo_definido = True
    for i in range(min(len(acciones), len(estados) - 1)):
        paso = i + 1
        anterior, actual, accion = estados[i], estados[i + 1], acciones[i]
        destino = actual.posicion
        if accion not in DESPLAZAMIENTOS:
            errores.append(f"Paso {paso}: acción desconocida {accion!r}")
        else:
            d_fila, d_columna = DESPLAZAMIENTOS[accion]
            esperado = (anterior.fila + d_fila, anterior.columna + d_columna)
            if destino != esperado:
                errores.append(
                    f"Paso {paso}: la acción {accion!r} desde {anterior.posicion} lleva a "
                    f"{esperado}, pero el estado dice {destino}"
                )
        if not escenario.dentro(destino):
            errores.append(f"Paso {paso}: el destino {destino} está fuera del mapa")
            costo_definido = False
        elif not escenario.es_transitable(destino):
            errores.append(f"Paso {paso}: el destino {destino} no es transitable")
            costo_definido = False
        else:
            costo += escenario.costo(destino)
        lleva = anterior.lleva_recurso or (datos.portador is None and destino == datos.recurso)
        if actual.lleva_recurso != lleva:
            errores.append(
                f"Paso {paso}: lleva_recurso es {actual.lleva_recurso}, debía ser {lleva}"
            )

    costo_recalculado = costo if costo_definido else None
    if costo_recalculado is not None and not math.isclose(
        costo_recalculado, resultado.costo, abs_tol=1e-9
    ):
        errores.append(
            f"El costo declarado {resultado.costo} no coincide con el recalculado "
            f"{costo_recalculado}"
        )

    final = estados[-1]
    if prueba.mision == "llevar_recurso":
        if unidad is not None:
            base = escenario.base_de(unidad.bando)
            if final.posicion != base or not final.lleva_recurso:
                errores.append(
                    f"El último estado ({final.posicion}, lleva_recurso={final.lleva_recurso}) "
                    f"no está en la base {base} llevando el recurso"
                )
    elif final.posicion != prueba.objetivo:
        errores.append(f"El último estado {final.posicion} no es el objetivo {prueba.objetivo}")
    return _reporte(errores, costo_recalculado)


def _distancia_manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def verificar_partida(
    datos: DatosEscenario,
    partida: Partida,
    orden_direcciones: Iterable[str] = ORDEN_DIRECCIONES_POR_DEFECTO,
) -> ReporteVerificacion:
    """
    Purpose: Comprobar que una Partida es legal de principio a fin, revisando además de forma
        independiente las invariantes de cada turno.
    Preconditions: datos es el escenario con el que se jugó la partida; orden_direcciones es
        el orden de direcciones con el que se construyeron sus reglas.
    Postconditions: Devuelve un ReporteVerificacion (costo_recalculado None) con TODOS los
        errores, indicando el turno. Las comprobaciones de celda no transitable, base rival y
        casilla compartida se aplican solo al destino de la unidad movida (un escenario inicial
        puede traer unidades compartiendo casilla o sobre la base rival).
    Complexity: tiempo O(T * U), espacio O(U) con T = turnos y U = unidades
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida mediante tests/test_verificador.py
    """
    reglas = ReglasJuego(datos, orden_direcciones)
    escenario = datos.escenario
    estados, jugadas = partida.estados, partida.jugadas
    errores: list[str] = []

    if len(estados) != len(jugadas) + 1:
        errores.append(f"Hay {len(estados)} estados y {len(jugadas)} jugadas")
    if len(partida.decisiones) != len(jugadas):
        errores.append(f"Hay {len(partida.decisiones)} decisiones y {len(jugadas)} jugadas")
    if partida.turnos != len(jugadas):
        errores.append(f"turnos es {partida.turnos}, pero hay {len(jugadas)} jugadas")
    if not estados:
        errores.append("La partida no tiene estados")
        return _reporte(errores)
    if estados[0] != reglas.estado_inicial():
        errores.append("Turno 0: el primer estado no es el estado inicial del escenario")

    for i in range(min(len(jugadas), len(estados) - 1)):
        turno = i + 1
        antes, despues, jugada = estados[i], estados[i + 1], jugadas[i]
        legales = reglas.jugadas_legales(antes)
        if jugada not in legales:
            errores.append(f"Turno {turno}: la jugada '{jugada}' no es legal")
        elif reglas.aplicar(antes, jugada) != despues:
            errores.append(f"Turno {turno}: aplicar '{jugada}' no produce el estado siguiente")

        pos_antes, pos_despues = dict(antes.posiciones), dict(despues.posiciones)
        if set(pos_antes) != set(pos_despues):
            errores.append(f"Turno {turno}: cambia el conjunto de unidades")
        elif jugada.es_pasar:
            if pos_antes != pos_despues:
                errores.append(f"Turno {turno}: pasar no debe mover ninguna unidad")
        elif jugada.unidad not in pos_antes:
            errores.append(f"Turno {turno}: la unidad {jugada.unidad!r} no existe")
        else:
            movidas = {u for u in pos_antes if pos_antes[u] != pos_despues[u]}
            if movidas != {jugada.unidad}:
                errores.append(
                    f"Turno {turno}: cambian las posiciones de {sorted(movidas)} y solo debía "
                    f"moverse {jugada.unidad}"
                )
            else:
                destino = pos_despues[jugada.unidad]
                if _distancia_manhattan(pos_antes[jugada.unidad], destino) != 1:
                    errores.append(f"Turno {turno}: {jugada.unidad} no se movió una casilla")
                if not escenario.es_transitable(destino):
                    errores.append(f"Turno {turno}: {jugada.unidad} termina en {destino}, "
                                   "una celda no transitable")
                bando = reglas.bando_de(jugada.unidad)
                rival = "B" if bando == "A" else "A"
                if destino == escenario.base_de(rival):
                    errores.append(
                        f"Turno {turno}: {jugada.unidad} entra a la base rival {destino}"
                    )
                otras = [u for u, p in pos_despues.items() if p == destino and u != jugada.unidad]
                if otras:
                    errores.append(
                        f"Turno {turno}: {jugada.unidad} comparte la casilla {destino} con {otras}"
                    )

        if (despues.recurso is None) == (despues.portador is None):
            errores.append(f"Turno {turno}: debe haber exactamente uno de recurso y portador")
        if despues.turno == antes.turno:
            errores.append(f"Turno {turno}: el turno no alterna ({despues.turno})")
        if despues.turnos_jugados != antes.turnos_jugados + 1:
            errores.append(
                f"Turno {turno}: turnos_jugados pasa de {antes.turnos_jugados} a "
                f"{despues.turnos_jugados}"
            )

    for i, estado in enumerate(estados[:-1]):
        if reglas.es_terminal(estado):
            errores.append(f"Turno {i}: el estado intermedio ya es terminal")
    if not reglas.es_terminal(estados[-1]):
        errores.append("El último estado no es terminal")
    if partida.ganador != reglas.ganador(estados[-1]):
        errores.append(
            f"ganador declarado {partida.ganador!r}, pero el estado final da "
            f"{reglas.ganador(estados[-1])!r}"
        )
    return _reporte(errores)
