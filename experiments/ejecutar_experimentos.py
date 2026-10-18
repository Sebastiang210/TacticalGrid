"""Experimentos reproducibles de TacticalGrid.

Uso: .venv\\Scripts\\python experiments\\ejecutar_experimentos.py

Usa las mismas funciones que la interfaz (tacticalgrid/ui/servicio.py), repite cada ejecución,
verifica cada resultado y escribe CSV, gráficas y resumen.txt en experiments/resultados/.
"""

import csv
import json
import platform
import statistics
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

from tacticalgrid.carga.cargador import DatosEscenario, cargar_escenario, leer_json
from tacticalgrid.config import ORDEN_DIRECCIONES_POR_DEFECTO
from tacticalgrid.ui.servicio import (
    ORDENES_DISPONIBLES,
    ejecutar_busqueda,
    ejecutar_decision,
    ejecutar_partida,
    verificar,
)

RAIZ = Path(__file__).resolve().parents[1]
SALIDA_POR_DEFECTO = RAIZ / "experiments" / "resultados"
REPETICIONES = 5

RUTAS = {
    "E4x4": RAIZ / "scenarios" / "dev" / "enunciado_4x4.json",
    "MURO": RAIZ / "scenarios" / "casos" / "caso3_muro.json",
    "MISION": RAIZ / "scenarios" / "casos" / "caso6_mision.json",
    "GRANDE": RAIZ / "scenarios" / "casos" / "caso6_mision_grande.json",
    "ADV": RAIZ / "scenarios" / "casos" / "caso7_8_10_adversarial.json",
    "ORDEN": RAIZ / "scenarios" / "casos" / "caso9_orden.json",
}
ORDEN_DFS_ALTERNATIVO = ("abajo", "izquierda", "arriba", "derecha")
BUSQUEDAS = (("BFS", ""), ("DFS", ""), ("UCS", ""), ("A*", "h1"), ("A*", "h2"))
DECISORES = ("Minimax", "Alfa-beta")
KS_BEAM = (1, 2, 4, 8)

COLUMNAS_BUSQUEDA = [
    "escenario", "algoritmo", "heuristica", "exito", "costo", "movimientos",
    "estados_generados", "estados_expandidos", "maximo_frontera", "tiempo_ms", "camino",
    "verificado",
]  # fmt: skip
COLUMNAS_DECISION = [
    "escenario", "algoritmo", "profundidad", "accion", "valor", "nodos_generados",
    "nodos_evaluados", "nodos_podados", "tiempo_ms", "verificado",
    "misma_decision_que_minimax",
]  # fmt: skip


class ErrorReproducibilidad(RuntimeError):
    """Las métricas de conteo difieren entre repeticiones de una misma ejecución."""


@dataclass
class Contexto:
    """Estado compartido de una corrida de experimentos."""

    salida: Path
    rapido: bool
    repeticiones: int
    datos: dict[str, DatosEscenario]
    fallos: list[str] = field(default_factory=list)
    archivos: list[Path] = field(default_factory=list)
    comprobaciones: list[tuple[bool, str]] = field(default_factory=list)
    comparaciones: list[bool] = field(default_factory=list)  # alfa-beta == minimax por fila
    res: dict[tuple, dict] = field(default_factory=dict)


# ---------------------------------------------------------------------- utilidades


def _num(valor: float) -> int | float:
    """Entero si el valor es entero (14.0 → 14); si no, redondeado a 3 decimales."""
    return int(valor) if float(valor).is_integer() else round(valor, 3)


def _camino(resultado) -> str:
    return ">".join(f"({e.fila},{e.columna})" for e in resultado.estados)


def _huella_busqueda(r) -> tuple:
    return (r.exito, r.costo, r.movimientos, r.nodos_generados, r.nodos_expandidos,
            r.max_frontera, _camino(r))  # fmt: skip


def _huella_decision(d) -> tuple:
    return (str(d.jugada), d.valor, d.nodos_generados, d.nodos_evaluados, d.podas)


def _repetir(ctx: Contexto, llamada, huella):
    """Ejecuta `llamada` N veces; exige huella idéntica y devuelve (primero, mediana ms)."""
    primero = llamada()
    base = huella(primero)
    tiempos = [primero.tiempo_ms]
    for numero in range(2, ctx.repeticiones + 1):
        otro = llamada()
        if huella(otro) != base:
            raise ErrorReproducibilidad(
                f"Repetición {numero}: {huella(otro)} difiere de {base}"
            )
        tiempos.append(otro.tiempo_ms)
    return primero, statistics.median(tiempos)


def _verificar(ctx: Contexto, etiqueta: str, datos, resultado, orden) -> bool:
    reporte = verificar(datos, resultado, orden)
    if not reporte.valido:
        ctx.fallos.append(f"{etiqueta}: {'; '.join(reporte.errores)}")
    return reporte.valido


def _escribir_csv(ctx: Contexto, nombre: str, columnas: list[str], filas: list[dict]) -> None:
    ruta = ctx.salida / nombre
    extra = {"python": platform.python_version(), "sistema": platform.platform()}
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=[*columnas, *extra], extrasaction="raise")
        escritor.writeheader()
        for fila in filas:
            escritor.writerow({c: fila.get(c, "") for c in columnas} | extra)
    ctx.archivos.append(ruta)


def _fila_busqueda(ctx, escenario, datos, algoritmo, heuristica="", k=None,
                   orden=ORDEN_DIRECCIONES_POR_DEFECTO) -> dict:  # fmt: skip
    resultado, mediana = _repetir(
        ctx,
        lambda: ejecutar_busqueda(datos, algoritmo, heuristica or "h2", k or 4, orden),
        _huella_busqueda,
    )
    etiqueta = " ".join(str(p) for p in (escenario, algoritmo, heuristica, k) if p)
    return {
        "escenario": escenario,
        "algoritmo": algoritmo,
        "heuristica": heuristica,
        "exito": resultado.exito,
        "costo": _num(resultado.costo),
        "movimientos": resultado.movimientos,
        "estados_generados": resultado.nodos_generados,
        "estados_expandidos": resultado.nodos_expandidos,
        "maximo_frontera": resultado.max_frontera,
        "tiempo_ms": round(mediana, 3),
        "camino": _camino(resultado),
        "verificado": _verificar(ctx, etiqueta, datos, resultado, orden),
    }


def _fila_decision(ctx, escenario, datos, algoritmo, profundidad,
                   orden=ORDEN_DIRECCIONES_POR_DEFECTO) -> dict:  # fmt: skip
    decision, mediana = _repetir(
        ctx, lambda: ejecutar_decision(datos, algoritmo, profundidad, orden), _huella_decision
    )
    etiqueta = f"{escenario} {algoritmo} p={profundidad} orden={', '.join(orden)}"
    return {
        "escenario": escenario,
        "algoritmo": algoritmo,
        "profundidad": profundidad,
        "accion": str(decision.jugada),
        "valor": _num(decision.valor),
        "nodos_generados": decision.nodos_generados,
        "nodos_evaluados": decision.nodos_evaluados,
        "nodos_podados": decision.podas,
        "tiempo_ms": round(mediana, 3),
        "verificado": _verificar(ctx, etiqueta, datos, decision, orden),
    }


# ---------------------------------------------------------------------- experimentos


def _exp_busqueda(ctx: Contexto) -> list[dict]:
    filas = []
    for escenario in ("E4x4", "MURO", "MISION", "GRANDE"):
        for algoritmo, heuristica in BUSQUEDAS:
            fila = _fila_busqueda(ctx, escenario, ctx.datos[escenario], algoritmo, heuristica)
            ctx.res[("busqueda", escenario, algoritmo, heuristica)] = fila
            filas.append(fila)
    return filas


def _exp_dfs_orden(ctx: Contexto) -> list[dict]:
    filas = []
    for orden in ORDENES_DISPONIBLES:
        fila = _fila_busqueda(ctx, "E4x4", ctx.datos["E4x4"], "DFS", orden=orden)
        ctx.res[("dfs_orden", orden)] = fila
        filas.append({
            "orden": ", ".join(orden),
            "costo": fila["costo"],
            "movimientos": fila["movimientos"],
            "estados_expandidos": fila["estados_expandidos"],
        })  # fmt: skip
    return filas


def _exp_beam(ctx: Contexto) -> list[dict]:
    filas = []
    for escenario in ("MISION", "MURO", "E4x4"):
        for heuristica in ("h1", "h2"):
            referencia = ctx.res.get(("busqueda", escenario, "A*", heuristica))
            if referencia is None:
                referencia = _fila_busqueda(ctx, escenario, ctx.datos[escenario], "A*", heuristica)
            filas.append(referencia | {"k": ""})
            ctx.res[("beam_a*", escenario, heuristica)] = referencia
            for k in KS_BEAM:
                fila = _fila_busqueda(ctx, escenario, ctx.datos[escenario], "Beam", heuristica, k)
                fila["k"] = k
                ctx.res[("beam", escenario, heuristica, k)] = fila
                filas.append(fila)
    return filas


def _exp_adversarial(ctx: Contexto) -> list[dict]:
    profundidades = (1, 2) if ctx.rapido else (1, 2, 3, 4, 5)
    filas = []
    for escenario in ("ADV", "ORDEN"):
        for profundidad in profundidades:
            minimax = _fila_decision(ctx, escenario, ctx.datos[escenario], "Minimax", profundidad)
            poda = _fila_decision(ctx, escenario, ctx.datos[escenario], "Alfa-beta", profundidad)
            igual = (poda["accion"], poda["valor"]) == (minimax["accion"], minimax["valor"])
            poda["misma_decision_que_minimax"] = igual
            ctx.comparaciones.append(igual)
            for fila in (minimax, poda):
                ctx.res[("adv", escenario, profundidad, fila["algoritmo"])] = fila
                filas.append(fila)
    return filas


def _exp_orden_poda(ctx: Contexto) -> list[dict]:
    configuraciones = (("ORDEN", 2), ("ADV", 2)) if ctx.rapido else (("ORDEN", 5), ("ADV", 4))
    filas = []
    for escenario, profundidad in configuraciones:
        datos = ctx.datos[escenario]
        for orden in ORDENES_DISPONIBLES:
            poda = _fila_decision(ctx, escenario, datos, "Alfa-beta", profundidad, orden)
            minimax = _fila_decision(ctx, escenario, datos, "Minimax", profundidad, orden)
            ctx.comparaciones.append(
                (poda["accion"], poda["valor"]) == (minimax["accion"], minimax["valor"])
            )
            fila = {
                "escenario": escenario,
                "profundidad": profundidad,
                "orden": ", ".join(orden),
                "accion": poda["accion"],
                "valor": poda["valor"],
                "nodos_generados": poda["nodos_generados"],
                "nodos_evaluados": poda["nodos_evaluados"],
                "nodos_podados": poda["nodos_podados"],
                "tiempo_ms": poda["tiempo_ms"],
                "valor_igual_minimax": poda["valor"] == minimax["valor"],
            }
            ctx.res[("orden_poda", escenario, orden)] = fila
            filas.append(fila)
    return filas


def _exp_partidas(ctx: Contexto) -> list[dict]:
    profundidades = (2,) if ctx.rapido else (2, 3, 4)
    filas = []
    for escenario in ("ADV", "ORDEN"):
        datos = ctx.datos[escenario]
        for profundidad in profundidades:
            inicio = time.perf_counter()
            partida = ejecutar_partida(datos, "Alfa-beta", profundidad)
            tiempo = (time.perf_counter() - inicio) * 1000
            verificado = _verificar(
                ctx, f"partida {escenario} p={profundidad}", datos, partida,
                ORDEN_DIRECCIONES_POR_DEFECTO,
            )  # fmt: skip
            fila = {
                "escenario": escenario,
                "profundidad": profundidad,
                "ganador": partida.ganador or "empate",
                "turnos": partida.turnos,
                "tiempo_total_ms": round(tiempo, 3),
                "verificado": verificado,
            }
            ctx.res[("partida", escenario, profundidad)] = fila
            filas.append(fila)
    return filas


def _cargar_con_pantano(escenario: str, costo: float) -> DatosEscenario:
    """Copia del JSON con el costo del pantano cambiado, pasada por un archivo temporal."""
    contenido = leer_json(RUTAS[escenario])
    contenido["tipos_terreno"]["pantano"]["costo"] = costo
    with tempfile.TemporaryDirectory() as carpeta:
        ruta = Path(carpeta) / f"{escenario}_pantano{costo}.json"
        ruta.write_text(json.dumps(contenido), encoding="utf-8")
        return cargar_escenario(ruta)


def _exp_costo_pantano(ctx: Contexto) -> list[dict]:
    filas = []
    for escenario in ("E4x4", "MISION"):
        for costo_pantano in (7, 15):
            datos = (
                ctx.datos[escenario]
                if costo_pantano == 7
                else _cargar_con_pantano(escenario, costo_pantano)
            )
            for algoritmo, heuristica, etiqueta in (("UCS", "", "UCS"), ("A*", "h2", "A*(h2)")):
                fila = _fila_busqueda(ctx, escenario, datos, algoritmo, heuristica)
                ctx.res[("pantano", escenario, costo_pantano, etiqueta)] = fila
                filas.append({
                    "escenario": escenario,
                    "costo_pantano": costo_pantano,
                    "algoritmo": etiqueta,
                    "costo": fila["costo"],
                    "movimientos": fila["movimientos"],
                    "camino": fila["camino"],
                })  # fmt: skip
    return filas


# ---------------------------------------------------------------------- resumen


def _comprobar(ctx: Contexto, descripcion: str, esperado, obtenido) -> None:
    """Registra una comprobación; se omite si el dato no se produjo (obtenido None)."""
    if obtenido is None:
        return
    if obtenido == esperado:
        ctx.comprobaciones.append((True, f"✔ {descripcion}: {obtenido}"))
    else:
        ctx.comprobaciones.append(
            (False, f"DIFERENCIA {descripcion}: esperado {esperado}, obtenido {obtenido}")
        )


def _campo(ctx: Contexto, clave: tuple, campo: str):
    fila = ctx.res.get(clave)
    return None if fila is None else fila[campo]


def _comprobaciones(ctx: Contexto) -> None:
    def busq(escenario, algoritmo, heuristica=""):
        return ("busqueda", escenario, algoritmo, heuristica)

    for algoritmo, costo in (("BFS", 14), ("DFS", 10), ("UCS", 7)):
        _comprobar(ctx, f"E4x4 {algoritmo} costo", costo,
                   _campo(ctx, busq("E4x4", algoritmo), "costo"))  # fmt: skip
    _comprobar(ctx, "E4x4 BFS movimientos", 4, _campo(ctx, busq("E4x4", "BFS"), "movimientos"))
    _comprobar(ctx, "E4x4 UCS movimientos", 6, _campo(ctx, busq("E4x4", "UCS"), "movimientos"))
    for h in ("h1", "h2"):
        _comprobar(ctx, f"E4x4 A*({h}) costo", 7, _campo(ctx, busq("E4x4", "A*", h), "costo"))
    _comprobar(ctx, "E4x4 DFS orden (abajo, izquierda, arriba, derecha) costo", 16,
               _campo(ctx, ("dfs_orden", ORDEN_DFS_ALTERNATIVO), "costo"))  # fmt: skip

    for h in ("h1", "h2"):
        _comprobar(ctx, f"MURO A*({h}) costo", 10, _campo(ctx, busq("MURO", "A*", h), "costo"))
    h1 = _campo(ctx, busq("MURO", "A*", "h1"), "estados_expandidos")
    h2 = _campo(ctx, busq("MURO", "A*", "h2"), "estados_expandidos")
    if h1 is not None and h2 is not None:
        _comprobar(ctx, f"MURO expandidos h2 ({h2}) < h1 ({h1})", True, h2 < h1)

    _comprobar(ctx, "MISION UCS costo", 15, _campo(ctx, busq("MISION", "UCS"), "costo"))
    _comprobar(ctx, "MISION Beam h2 k=1 con solución", False,
               _campo(ctx, ("beam", "MISION", "h2", 1), "exito"))  # fmt: skip
    for k, costo in ((2, 21), (4, 18), (8, 15)):
        _comprobar(ctx, f"MISION Beam h2 k={k} costo", costo,
                   _campo(ctx, ("beam", "MISION", "h2", k), "costo"))  # fmt: skip
    _comprobar(ctx, "GRANDE UCS costo", 21, _campo(ctx, busq("GRANDE", "UCS"), "costo"))

    esperado_adv = {
        1: ("A2 abajo", -2, 5, 5),
        2: ("A2 abajo", -114, 40, 22),
        3: ("A1 derecha", 0, 201, 62),
        4: ("A1 derecha", -111, 1136, 234),
    }
    for profundidad, (accion, valor, nodos_mm, nodos_ab) in esperado_adv.items():
        for algoritmo, nodos in (("Minimax", nodos_mm), ("Alfa-beta", nodos_ab)):
            clave = ("adv", "ADV", profundidad, algoritmo)
            texto = f"ADV p={profundidad} {algoritmo}"
            _comprobar(ctx, f"{texto} acción", accion, _campo(ctx, clave, "accion"))
            _comprobar(ctx, f"{texto} valor", valor, _campo(ctx, clave, "valor"))
            _comprobar(ctx, f"{texto} nodos generados", nodos,
                       _campo(ctx, clave, "nodos_generados"))  # fmt: skip
    if ctx.comparaciones:
        distintas = ctx.comparaciones.count(False)
        _comprobar(ctx, f"Alfa-beta == Minimax (acción y valor) en {len(ctx.comparaciones)} "
                   "comparaciones, distintas", 0, distintas)  # fmt: skip

    filas_orden = [f for (n, e, *_), f in ctx.res.items() if n == "orden_poda" and e == "ORDEN"]
    if filas_orden and filas_orden[0]["profundidad"] == 5:
        _comprobar(ctx, "ORDEN valor de Alfa-beta en las 24 órdenes", {-6},
                   {f["valor"] for f in filas_orden})  # fmt: skip
        nodos = {f["nodos_generados"] for f in filas_orden}
        _comprobar(ctx, f"ORDEN nodos generados varían entre órdenes ({len(nodos)} valores)",
                   True, len(nodos) > 1)  # fmt: skip

    fila = ctx.res.get(("partida", "ADV", 2))
    if fila is not None:
        _comprobar(ctx, "Partida ADV p=2 ganador", "B", fila["ganador"])
        _comprobar(ctx, "Partida ADV p=2 turnos", 18, fila["turnos"])
    fila = ctx.res.get(("partida", "ADV", 3))
    if fila is not None:
        _comprobar(ctx, "Partida ADV p=3 ganador", "empate", fila["ganador"])
        _comprobar(ctx, "Partida ADV p=3 turnos", 200, fila["turnos"])

    for algoritmo in ("UCS", "A*(h2)"):
        _comprobar(ctx, f"Pantano 15: E4x4 {algoritmo} sigue en costo",
                   7, _campo(ctx, ("pantano", "E4x4", 15, algoritmo), "costo"))  # fmt: skip


def _escribir_resumen(ctx: Contexto) -> None:
    _comprobaciones(ctx)
    correctas = sum(1 for ok, _ in ctx.comprobaciones if ok)
    total = len(ctx.comprobaciones)
    lineas = [texto for _, texto in ctx.comprobaciones]
    lineas.append(f"Total: {correctas} ✔, {total - correctas} DIFERENCIA, de {total} comprobaciones")
    ruta = ctx.salida / "resumen.txt"
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    ctx.archivos.append(ruta)


# ---------------------------------------------------------------------- gráficas


def _graficas(ctx: Contexto) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("Aviso: matplotlib no está instalado; se omiten las gráficas.")
        return

    def guardar(figura, nombre: str) -> None:
        ruta = ctx.salida / nombre
        figura.tight_layout()
        figura.savefig(ruta, dpi=120)
        plt.close(figura)
        ctx.archivos.append(ruta)

    # expandidos_busqueda.png
    escenarios = ("E4x4", "MURO", "MISION", "GRANDE")
    figura, eje = plt.subplots(figsize=(9, 4.5))
    ancho = 0.16
    for i, (algoritmo, heuristica) in enumerate(BUSQUEDAS):
        valores = [
            ctx.res[("busqueda", e, algoritmo, heuristica)]["estados_expandidos"]
            for e in escenarios
        ]
        posiciones = [j + (i - 2) * ancho for j in range(len(escenarios))]
        eje.bar(posiciones, valores, ancho, label=f"{algoritmo}({heuristica})" if heuristica
                else algoritmo)  # fmt: skip
    eje.set_xticks(range(len(escenarios)), escenarios)
    eje.set_ylabel("estados expandidos")
    eje.set_title("Estados expandidos por algoritmo")
    eje.legend()
    guardar(figura, "expandidos_busqueda.png")

    # beam_k.png
    figura, ejes = plt.subplots(1, 3, figsize=(12, 4))
    for eje, escenario in zip(ejes, ("MISION", "MURO", "E4x4"), strict=True):
        referencia = ctx.res[("beam_a*", escenario, "h2")]["costo"]
        filas = [ctx.res[("beam", escenario, "h2", k)] for k in KS_BEAM]
        finitos = [f["costo"] for f in filas if f["exito"]]
        techo = max([*finitos, referencia]) * 1.15
        indices = range(len(KS_BEAM))
        eje.plot([i for i, f in zip(indices, filas, strict=True) if f["exito"]], finitos,
                 "o-", label="Beam (h2)")  # fmt: skip
        fallos = [i for i, f in zip(indices, filas, strict=True) if not f["exito"]]
        if fallos:
            eje.plot(fallos, [techo] * len(fallos), "rX", markersize=10, label="sin solución")
        eje.axhline(referencia, color="gray", linestyle="--", label="A* (h2)")
        eje.set_xticks(list(indices), [str(k) for k in KS_BEAM])
        eje.set_ylim(0, techo * 1.1)
        eje.set_xlabel("k")
        eje.set_ylabel("costo")
        eje.set_title(escenario)
        eje.legend()
    guardar(figura, "beam_k.png")

    # nodos_profundidad.png
    figura, ejes = plt.subplots(1, 2, figsize=(11, 4))
    for eje, escenario in zip(ejes, ("ADV", "ORDEN"), strict=True):
        for algoritmo in DECISORES:
            filas = sorted(
                (clave[2], fila["nodos_generados"])
                for clave, fila in ctx.res.items()
                if clave[:2] == ("adv", escenario) and clave[3] == algoritmo
            )
            eje.semilogy([p for p, _ in filas], [n for _, n in filas], "o-", label=algoritmo)
        eje.set_xlabel("profundidad")
        eje.set_ylabel("nodos generados")
        eje.set_title(escenario)
        eje.legend()
    guardar(figura, "nodos_profundidad.png")

    # orden_poda.png
    filas = sorted(
        (fila["nodos_generados"], fila["orden"])
        for clave, fila in ctx.res.items()
        if clave[:2] == ("orden_poda", "ORDEN")
    )
    figura, eje = plt.subplots(figsize=(8, 8))
    etiquetas = ["·".join(d[:2] for d in orden.split(", ")) for _, orden in filas]
    eje.barh(range(len(filas)), [n for n, _ in filas])
    eje.set_yticks(range(len(filas)), etiquetas, fontsize=7)
    eje.set_xlabel("nodos generados (Alfa-beta)")
    eje.set_title("Poda según el orden de direcciones (ORDEN)")
    guardar(figura, "orden_poda.png")


# ---------------------------------------------------------------------- principal


def ejecutar_todo(salida: Path, rapido: bool = False) -> int:
    """
    Purpose: Ejecutar todos los experimentos y escribir CSV, gráficas y resumen.txt.
    Preconditions: salida es una ruta escribible; los escenarios de RUTAS existen. rapido=True
        usa 1 repetición, profundidades 1-2, partidas solo de profundidad 2 y no grafica.
    Postconditions: Sobrescribe los archivos en salida (se crea si no existe). Lanza
        ErrorReproducibilidad si las métricas de conteo difieren entre repeticiones. Devuelve 1
        si alguna verificación falló (los demás archivos se escriben igual), si no 0.
    Complexity: tiempo dominado por Minimax (O(b^d)) repetido por orden y escenario
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
   
    """
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)
    ctx = Contexto(
        salida=salida,
        rapido=rapido,
        repeticiones=1 if rapido else REPETICIONES,
        datos={nombre: cargar_escenario(ruta) for nombre, ruta in RUTAS.items()},
    )
    columnas_orden = [
        "escenario", "profundidad", "orden", "accion", "valor", "nodos_generados",
        "nodos_evaluados", "nodos_podados", "tiempo_ms", "valor_igual_minimax",
    ]  # fmt: skip
    experimentos = [
        ("busqueda.csv", COLUMNAS_BUSQUEDA, _exp_busqueda),
        ("dfs_orden.csv", ["orden", "costo", "movimientos", "estados_expandidos"],
         _exp_dfs_orden),
        ("beam.csv", [*COLUMNAS_BUSQUEDA, "k"], _exp_beam),
        ("adversarial_profundidad.csv", COLUMNAS_DECISION, _exp_adversarial),
        ("orden_poda.csv", columnas_orden, _exp_orden_poda),
        ("partidas.csv", ["escenario", "profundidad", "ganador", "turnos", "tiempo_total_ms",
                          "verificado"], _exp_partidas),
        ("costo_pantano.csv", ["escenario", "costo_pantano", "algoritmo", "costo", "movimientos",
                               "camino"], _exp_costo_pantano),
    ]  # fmt: skip
    for nombre, columnas, experimento in experimentos:
        _escribir_csv(ctx, nombre, columnas, experimento(ctx))
    _escribir_resumen(ctx)
    if not rapido:
        _graficas(ctx)

    correctas = sum(1 for ok, _ in ctx.comprobaciones if ok)
    diferencias = [texto for ok, texto in ctx.comprobaciones if not ok]
    print(f"Archivos generados en {salida}:")
    for archivo in ctx.archivos:
        print(f"  - {archivo.name}")
    print(f"Verificaciones fallidas: {len(ctx.fallos)}")
    for fallo in ctx.fallos:
        print(f"  ✘ {fallo}")
    print(f"Comprobaciones: {correctas} ✔ / {len(diferencias)} DIFERENCIA")
    for texto in diferencias:
        print(f"  {texto}")
    return 1 if ctx.fallos else 0


def main() -> None:
    """
    Purpose: Punto de entrada del script; ejecuta todos los experimentos completos.
    Preconditions: Ninguna.
    Postconditions: Escribe en experiments/resultados/, imprime el tiempo total y termina con
        código 1 si alguna verificación falló.
    Complexity: ver ejecutar_todo
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.

    """
    sys.stdout.reconfigure(encoding="utf-8")
    inicio = time.perf_counter()
    codigo = ejecutar_todo(SALIDA_POR_DEFECTO)
    print(f"Tiempo total: {time.perf_counter() - inicio:.1f} s")
    sys.exit(codigo)


if __name__ == "__main__":
    main()
