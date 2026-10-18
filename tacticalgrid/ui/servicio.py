"""Capa de servicio de la interfaz: ejecuta algoritmos, verifica y formatea resultados.

No importa tkinter, para poder probarse con pytest sin abrir ventanas.
"""

import itertools
import json
import math
import re
from collections.abc import Iterable, Sequence

from tacticalgrid.adversarial.minimax import ResultadoDecision, alfa_beta, minimax
from tacticalgrid.adversarial.partida import Partida, jugar_partida
from tacticalgrid.adversarial.utilidad import Evaluador
from tacticalgrid.busqueda.heuristicas import h_manhattan, h_pasos
from tacticalgrid.busqueda.informada import a_estrella, beam
from tacticalgrid.busqueda.no_informada import bfs, dfs, ucs
from tacticalgrid.busqueda.problema import ProblemaNavegacion
from tacticalgrid.busqueda.resultado import Resultado
from tacticalgrid.carga.cargador import DatosEscenario
from tacticalgrid.config import ORDEN_DIRECCIONES_POR_DEFECTO, PROFUNDIDAD_POR_DEFECTO
from tacticalgrid.core.escenario import Posicion
from tacticalgrid.core.juego import ReglasJuego
from tacticalgrid.verificacion.verificador import (
    ReporteVerificacion,
    verificar_camino,
    verificar_partida,
)

Orden = tuple[str, ...]


ORDENES_DISPONIBLES: tuple[Orden, ...] = tuple(
    itertools.permutations(ORDEN_DIRECCIONES_POR_DEFECTO)
)
ALGORITMOS_BUSQUEDA = ("BFS", "DFS", "UCS", "A*", "Beam")
ALGORITMOS_DECISION = ("Minimax", "Alfa-beta")
HEURISTICAS = {"h1": h_manhattan, "h2": h_pasos}

_NO_INFORMADAS = {"BFS": bfs, "DFS": dfs, "UCS": ucs}
_DECISORES = {"Minimax": minimax, "Alfa-beta": alfa_beta}
_CLAVES_PARTIDA = {"Minimax": "minimax", "Alfa-beta": "alfa_beta"}


def _orden(orden: Iterable[str]) -> Orden:
    """Convierte orden en tupla; ValueError si no es una de ORDENES_DISPONIBLES."""
    tupla = tuple(orden)
    if tupla not in ORDENES_DISPONIBLES:
        raise ValueError(
            f"Orden de direcciones desconocido {tupla!r}; debe ser una permutación de "
            f"{ORDEN_DIRECCIONES_POR_DEFECTO}"
        )
    return tupla


def _validar_decision(algoritmo: str) -> None:
    """ValueError si algoritmo no es uno de ALGORITMOS_DECISION."""
    if algoritmo not in ALGORITMOS_DECISION:
        raise ValueError(
            f"Algoritmo adversarial desconocido {algoritmo!r}; opciones: {ALGORITMOS_DECISION}"
        )


def ejecutar_busqueda(
    datos: DatosEscenario,
    algoritmo: str,
    heuristica: str = "h2",
    k: int = 4,
    orden: Iterable[str] = ORDEN_DIRECCIONES_POR_DEFECTO,
) -> Resultado:
    """
    Purpose: Ejecutar un algoritmo de búsqueda sobre la prueba de navegación del escenario.
    Preconditions: algoritmo en ALGORITMOS_BUSQUEDA; heuristica en HEURISTICAS (solo se usa
        en A* y Beam); k solo se usa en Beam; orden está en ORDENES_DISPONIBLES.
    Postconditions: Devuelve el Resultado del algoritmo. ValueError si algoritmo, heurística u
        orden son desconocidos, si k < 1 en Beam o si datos no trae una prueba 'busqueda'
        válida (mensaje de ProblemaNavegacion).
    Complexity: la del algoritmo elegido (más O(F·C) al crear h2)
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida en tests/test_servicio.py
    """
    if algoritmo not in ALGORITMOS_BUSQUEDA:
        raise ValueError(
            f"Algoritmo de búsqueda desconocido {algoritmo!r}; opciones: {ALGORITMOS_BUSQUEDA}"
        )
    if heuristica not in HEURISTICAS:
        raise ValueError(f"Heurística desconocida {heuristica!r}; opciones: {tuple(HEURISTICAS)}")
    problema = ProblemaNavegacion(datos, _orden(orden))
    if algoritmo in _NO_INFORMADAS:
        return _NO_INFORMADAS[algoritmo](problema)
    h = HEURISTICAS[heuristica](problema)
    if algoritmo == "A*":
        return a_estrella(problema, h, heuristica)
    return beam(problema, h, heuristica, k)


def ejecutar_decision(
    datos: DatosEscenario,
    algoritmo: str,
    profundidad: int,
    orden: Iterable[str] = ORDEN_DIRECCIONES_POR_DEFECTO,
) -> ResultadoDecision:
    """
    Purpose: Decidir la jugada del bando en turno desde el estado inicial del escenario.
    Preconditions: algoritmo en ALGORITMOS_DECISION; profundidad >= 1; orden está en
        ORDENES_DISPONIBLES.
    Postconditions: Devuelve el ResultadoDecision de Minimax o Alfa-beta con
        ReglasJuego(datos, orden). ValueError si algoritmo u orden son desconocidos, si la
        profundidad es inválida o si el estado inicial es terminal.
    Complexity: tiempo O(b^d) (mejor caso O(b^(d/2)) con Alfa-beta), espacio O(d)
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida en tests/test_servicio.py
    """
    _validar_decision(algoritmo)
    reglas = ReglasJuego(datos, _orden(orden))
    return _DECISORES[algoritmo](reglas, Evaluador(reglas), reglas.estado_inicial(), profundidad)


def ejecutar_partida(
    datos: DatosEscenario,
    algoritmo: str,
    profundidad: int,
    orden: Iterable[str] = ORDEN_DIRECCIONES_POR_DEFECTO,
) -> Partida:
    """
    Purpose: Jugar una partida completa IA contra IA desde el estado inicial del escenario.
    Preconditions: algoritmo en ALGORITMOS_DECISION; profundidad >= 1; orden está en
        ORDENES_DISPONIBLES.
    Postconditions: Devuelve la Partida de jugar_partida con ReglasJuego(datos, orden).
        ValueError si algoritmo u orden son desconocidos o la profundidad es inválida.
    Complexity: tiempo O(T·b^d), espacio O(T) con T = turnos jugados
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida en tests/test_servicio.py
    """
    _validar_decision(algoritmo)
    reglas = ReglasJuego(datos, _orden(orden))
    return jugar_partida(reglas, Evaluador(reglas), profundidad, _CLAVES_PARTIDA[algoritmo])


def verificar(
    datos: DatosEscenario,
    resultado: Resultado | ResultadoDecision | Partida,
    orden: Iterable[str] = ORDEN_DIRECCIONES_POR_DEFECTO,
) -> ReporteVerificacion:
    """
    Purpose: Verificar de forma independiente el último resultado obtenido en la interfaz.
    Preconditions: resultado se obtuvo con datos y con el orden indicado.
    Postconditions: Resultado → verificar_camino; Partida → verificar_partida con ese orden;
        ResultadoDecision → reporte que comprueba que la jugada está en las jugadas legales
        del estado inicial con ese orden. TypeError si resultado es de otro tipo; ValueError
        si el orden es desconocido.
    Complexity: tiempo O(L) para caminos, O(T·U) para partidas y O(U) para decisiones
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida en tests/test_servicio.py
    """
    orden = _orden(orden)
    if isinstance(resultado, Resultado):
        return verificar_camino(datos, resultado)
    if isinstance(resultado, Partida):
        return verificar_partida(datos, resultado, orden)
    if isinstance(resultado, ResultadoDecision):
        reglas = ReglasJuego(datos, orden)
        errores = []
        if resultado.jugada not in reglas.jugadas_legales(reglas.estado_inicial()):
            errores.append(f"La jugada '{resultado.jugada}' no es legal en el estado inicial")
        return ReporteVerificacion(
            valido=not errores, errores=tuple(errores), costo_recalculado=None
        )
    raise TypeError(f"No se puede verificar un objeto de tipo {type(resultado).__name__}")


def profundidad_inicial(datos: DatosEscenario) -> int:
    """
    Purpose: Profundidad con la que se inicializa la interfaz al cargar un escenario.
    Preconditions: Ninguna.
    Postconditions: datos.profundidad_maxima si viene en el JSON; si no,
        PROFUNDIDAD_POR_DEFECTO.
    Complexity: tiempo O(1), espacio O(1)
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida en tests/test_servicio.py
    """
    return datos.profundidad_maxima or PROFUNDIDAD_POR_DEFECTO


def dividir_camino(resultado: Resultado) -> tuple[list[Posicion], list[Posicion]]:
    """
    Purpose: Separar el camino de una búsqueda en el tramo sin recurso (ida) y el tramo con
        recurso (vuelta), para dibujarlos por separado.
    Preconditions: resultado proviene de ejecutar_busqueda.
    Postconditions: Sin éxito → ([], []). Si ningún estado lleva el recurso → (todas las
        posiciones, []). Si el primer estado ya lo lleva → ([], todas las posiciones). Si no,
        con i = primer índice con lleva_recurso, ida = posiciones[0..i] y vuelta =
        posiciones[i..fin]; ambas comparten la casilla del recurso.
    Complexity: tiempo O(L), espacio O(L) con L = largo del camino
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida en tests/test_servicio.py
    """
    if not resultado.exito:
        return [], []
    posiciones = [e.posicion for e in resultado.estados]
    indice = next((i for i, e in enumerate(resultado.estados) if e.lleva_recurso), None)
    if indice is None:
        return posiciones, []
    if indice == 0:
        return [], posiciones
    return posiciones[: indice + 1], posiciones[indice:]


def _json(contenido: dict) -> str:
    return json.dumps(contenido, indent=2, ensure_ascii=False)


def formatear_busqueda(resultado: Resultado, orden: Iterable[str]) -> str:
    """
    Purpose: Texto JSON legible de un resultado de búsqueda con la estructura del enunciado.
    Preconditions: resultado proviene de ejecutar_busqueda con ese orden.
    Postconditions: JSON con algoritmo, exito, camino [[f, c], ...], costo, estados_generados,
        estados_expandidos, maximo_frontera, tiempo_ms y orden.
    Complexity: tiempo O(L), espacio O(L) con L = largo del camino
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida en tests/test_servicio.py
    """
    return _json(
        {
            "algoritmo": resultado.algoritmo,
            "exito": resultado.exito,
            "camino": [[e.fila, e.columna] for e in resultado.estados],
            "costo": resultado.costo,
            "estados_generados": resultado.nodos_generados,
            "estados_expandidos": resultado.nodos_expandidos,
            "maximo_frontera": resultado.max_frontera,
            "tiempo_ms": round(resultado.tiempo_ms, 3),
            "orden": list(orden),
        }
    )


def formatear_decision(decision: ResultadoDecision, orden: Iterable[str]) -> str:
    """
    Purpose: Texto JSON legible de una decisión adversarial.
    Preconditions: decision proviene de ejecutar_decision con ese orden.
    Postconditions: JSON con algoritmo, accion_seleccionada, valor, profundidad,
        nodos_generados, nodos_evaluados, nodos_podados, tiempo_ms y orden.
    Complexity: tiempo O(1), espacio O(1)
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida en tests/test_servicio.py
    """
    return _json(
        {
            "algoritmo": decision.algoritmo,
            "accion_seleccionada": str(decision.jugada),
            "valor": decision.valor,
            "profundidad": decision.profundidad,
            "nodos_generados": decision.nodos_generados,
            "nodos_evaluados": decision.nodos_evaluados,
            "nodos_podados": decision.podas,
            "tiempo_ms": round(decision.tiempo_ms, 3),
            "orden": list(orden),
        }
    )


def formatear_partida(partida: Partida, orden: Iterable[str]) -> str:
    """
    Purpose: Texto JSON legible del resumen de una partida.
    Preconditions: partida proviene de ejecutar_partida con ese orden.
    Postconditions: JSON con ganador ("A", "B" o "empate por límite"), turnos, orden y la
        lista de jugadas como texto.
    Complexity: tiempo O(T), espacio O(T) con T = turnos jugados
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida en tests/test_servicio.py
    """
    return _json(
        {
            "ganador": partida.ganador if partida.ganador is not None else "empate por límite",
            "turnos": partida.turnos,
            "orden": list(orden),
            "jugadas": [str(j) for j in partida.jugadas],
        }
    )


# ---------------------------------------------------------------------- resúmenes legibles

_ANCHO_ETIQUETA = 20
_ANCHO_VALOR = 14
_CASILLAS_POR_LINEA = 12
_JUGADAS_POR_LINEA = 4
_ANCHO_JUGADA = 18


def _numero(valor: float) -> str:
    """Entero sin ".0", si no con 2 decimales; ±inf como ∞; signo menos tipográfico (−)."""
    if math.isinf(valor):
        texto = "-∞" if valor < 0 else "∞"
    elif float(valor).is_integer():
        texto = str(int(valor))
    else:
        texto = f"{valor:.2f}"
    return texto.replace("-", "−")


def _cabecera(
    numero: int, modo: str, algoritmo: str, orden: Iterable[str], profundidad: int | None = None
) -> str:
    """Línea "━━━━ #n · Modo · algoritmo · [profundidad p · ]orden: ... ━━━━"."""
    partes = [f"#{numero}", modo, algoritmo]
    if profundidad is not None:
        partes.append(f"profundidad {profundidad}")
    partes.append(f"orden: {', '.join(orden)}")
    return f"━━━━ {' · '.join(partes)} ━━━━"


def _algoritmo_busqueda(nombre: str) -> str:
    """Pasa "Beam k=3 (h2)" a "Beam (h2) · k=3"; los demás nombres quedan igual."""
    coincidencia = re.fullmatch(r"Beam k=(\d+) \((.+)\)", nombre)
    if coincidencia is None:
        return nombre
    k, heuristica = coincidencia.groups()
    return f"Beam ({heuristica}) · k={k}"


def _fila(etiqueta: str, valor: str) -> str:
    return f"  {etiqueta:<{_ANCHO_ETIQUETA}}{valor}"


def _columnas(pares: Sequence[tuple[str, str]]) -> list[str]:
    """Pares (etiqueta, valor) de dos en dos por línea, alineados con espacios."""
    celdas = [f"{e:<{_ANCHO_ETIQUETA}}{v:<{_ANCHO_VALOR}}" for e, v in pares]
    return [
        "  " + "".join(celdas[i : i + 2]).rstrip() for i in range(0, len(celdas), 2)
    ]


def _tiempo(ms: float) -> str:
    return f"{ms:.2f} ms"


def resumir_busqueda(resultado: Resultado, orden: Iterable[str], numero: int) -> str:
    """
    Purpose: Resumen legible (texto plano) de un resultado de búsqueda para el panel.
    Preconditions: resultado proviene de ejecutar_busqueda con ese orden; numero >= 1.
    Postconditions: Cabecera con número, algoritmo (heurística y k si aplican) y orden. Con
        éxito: "✔ Camino encontrado", el camino "(f,c) → ..." partido cada 12 casillas y en
        dos columnas Movimientos, Costo, Expandidos, Generados, Frontera máx. y Tiempo. Sin
        éxito: "✘ No existe camino" y las métricas de búsqueda.
    Complexity: tiempo O(L), espacio O(L) con L = largo del camino
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida en tests/test_servicio.py
    """
    lineas = [_cabecera(numero, "Búsqueda", _algoritmo_busqueda(resultado.algoritmo), orden)]
    metricas = [
        ("Expandidos", str(resultado.nodos_expandidos)),
        ("Generados", str(resultado.nodos_generados)),
        ("Frontera máx.", str(resultado.max_frontera)),
        ("Tiempo", _tiempo(resultado.tiempo_ms)),
    ]
    if resultado.exito:
        casillas = [f"({e.fila},{e.columna})" for e in resultado.estados]
        lineas.append("✔ Camino encontrado")
        for i in range(0, len(casillas), _CASILLAS_POR_LINEA):
            trozo = " → ".join(casillas[i : i + _CASILLAS_POR_LINEA])
            lineas.append(f"  {trozo}" if i == 0 else f"    → {trozo}")
        metricas = [
            ("Movimientos", str(resultado.movimientos)),
            ("Costo", _numero(resultado.costo)),
            *metricas,
        ]
    else:
        lineas.append("✘ No existe camino")
    lineas += _columnas(metricas)
    return "\n".join(lineas)


def resumir_decision(
    decision: ResultadoDecision, orden: Iterable[str], profundidad: int, numero: int
) -> str:
    """
    Purpose: Resumen legible (texto plano) de una decisión adversarial para el panel.
    Preconditions: decision proviene de ejecutar_decision con ese orden y profundidad.
    Postconditions: Cabecera con número, algoritmo, profundidad y orden; Acción recomendada,
        Valor y en dos columnas Nodos generados, Evaluados, Podados y Tiempo.
    Complexity: tiempo O(1), espacio O(1)
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida en tests/test_servicio.py
    """
    lineas = [
        _cabecera(numero, "Adversarial", decision.algoritmo, orden, profundidad),
        _fila("Acción recomendada", str(decision.jugada)),
        _fila("Valor", _numero(decision.valor)),
        *_columnas(
            [
                ("Nodos generados", str(decision.nodos_generados)),
                ("Evaluados", str(decision.nodos_evaluados)),
                ("Podados", str(decision.podas)),
                ("Tiempo", _tiempo(decision.tiempo_ms)),
            ]
        ),
    ]
    return "\n".join(lineas)


def resumir_partida(
    partida: Partida, orden: Iterable[str], profundidad: int, algoritmo: str, numero: int
) -> str:
    """
    Purpose: Resumen legible (texto plano) de una partida IA contra IA para el panel.
    Preconditions: partida proviene de ejecutar_partida con ese algoritmo, orden y profundidad.
    Postconditions: Cabecera con número, algoritmo, profundidad y orden; "Ganador: X" o
        "Empate por límite de turnos"; número de turnos y las jugadas numeradas, 4 por línea.
    Complexity: tiempo O(T), espacio O(T) con T = turnos jugados
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida en tests/test_servicio.py
    """
    final = (
        f"Ganador: {partida.ganador}"
        if partida.ganador is not None
        else "Empate por límite de turnos"
    )
    lineas = [
        _cabecera(numero, "Partida", algoritmo, orden, profundidad),
        final,
        _fila("Turnos", str(partida.turnos)),
        "  Jugadas:",
    ]
    jugadas = [
        f"{i:>3}. {jugada}".ljust(_ANCHO_JUGADA) for i, jugada in enumerate(partida.jugadas, 1)
    ]
    for i in range(0, len(jugadas), _JUGADAS_POR_LINEA):
        lineas.append("  " + "".join(jugadas[i : i + _JUGADAS_POR_LINEA]).rstrip())
    return "\n".join(lineas)


def resumir_verificacion(reporte: ReporteVerificacion) -> str:
    """
    Purpose: Resumen legible de un reporte de verificación para el panel.
    Preconditions: Ninguna.
    Postconditions: "✔ Verificado" si el reporte es válido; si no, "✘ N error(es):" seguido
        de una línea "  - <error>" por error.
    Complexity: tiempo O(E), espacio O(E) con E = cantidad de errores
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida en tests/test_servicio.py
    """
    if reporte.valido:
        return "✔ Verificado"
    return "\n".join(
        [f"✘ {len(reporte.errores)} error(es):", *(f"  - {e}" for e in reporte.errores)]
    )
