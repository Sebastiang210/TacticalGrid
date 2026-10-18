"""Pruebas de la capa de servicio de la interfaz (sin abrir ventanas)."""

import json
from dataclasses import replace

import pytest
from conftest import datos_mision

from tacticalgrid.config import ORDEN_DIRECCIONES_POR_DEFECTO
from tacticalgrid.core.juego import Jugada
from tacticalgrid.ui.servicio import (
    ORDENES_DISPONIBLES,
    dividir_camino,
    ejecutar_busqueda,
    ejecutar_decision,
    ejecutar_partida,
    formatear_busqueda,
    formatear_decision,
    formatear_partida,
    profundidad_inicial,
    resumir_busqueda,
    resumir_decision,
    resumir_partida,
    resumir_verificacion,
    verificar,
)
from tacticalgrid.verificacion.verificador import ReporteVerificacion

ORDEN_ALTERNATIVO = ("abajo", "izquierda", "arriba", "derecha")


@pytest.mark.parametrize(
    ("algoritmo", "heuristica", "k", "costo"),
    [
        ("BFS", "h2", 4, 14),
        ("DFS", "h2", 4, 10),
        ("UCS", "h2", 4, 7),
        ("A*", "h1", 4, 7),
        ("A*", "h2", 4, 7),
        ("Beam", "h1", 1, 12),
        ("Beam", "h2", 1, 12),
    ],
)
def test_costos_conocidos_en_el_4x4(datos, algoritmo, heuristica, k, costo):
    resultado = ejecutar_busqueda(datos, algoritmo, heuristica, k)
    assert resultado.exito
    assert resultado.costo == costo


def test_dfs_con_otro_orden(datos):
    por_defecto = ejecutar_busqueda(datos, "DFS")
    otro = ejecutar_busqueda(datos, "DFS", orden=ORDEN_ALTERNATIVO)
    assert otro.costo == 16
    assert otro.estados != por_defecto.estados


@pytest.mark.parametrize("algoritmo", ["Minimax", "Alfa-beta"])
def test_decision_profundidad_2(datos, algoritmo):
    decision = ejecutar_decision(datos, algoritmo, 2)
    assert decision.algoritmo == algoritmo
    assert str(decision.jugada) == "A2 abajo"
    assert decision.valor == -114


@pytest.mark.parametrize("profundidad", [1, 2, 3])
def test_alfa_beta_igual_a_minimax_con_orden_alternativo(datos, profundidad):
    mm = ejecutar_decision(datos, "Minimax", profundidad, ORDEN_ALTERNATIVO)
    ab = ejecutar_decision(datos, "Alfa-beta", profundidad, ORDEN_ALTERNATIVO)
    assert ab.valor == mm.valor
    assert ab.jugada == mm.jugada


def test_partida_profundidad_2_gana_b(datos):
    assert ejecutar_partida(datos, "Alfa-beta", 2).ganador == "B"


def test_verificar_busqueda(datos):
    for orden in (ORDEN_DIRECCIONES_POR_DEFECTO, ORDEN_ALTERNATIVO):
        resultado = ejecutar_busqueda(datos, "DFS", orden=orden)
        reporte = verificar(datos, resultado, orden)
        assert reporte.valido, reporte.errores


@pytest.mark.parametrize("orden", [ORDEN_DIRECCIONES_POR_DEFECTO, ORDEN_ALTERNATIVO])
def test_verificar_decision(datos, orden):
    decision = ejecutar_decision(datos, "Alfa-beta", 2, orden)
    reporte = verificar(datos, decision, orden)
    assert reporte.valido, reporte.errores
    assert reporte.costo_recalculado is None


def test_verificar_decision_ilegal(datos):
    decision = replace(ejecutar_decision(datos, "Minimax", 1), jugada=Jugada("B1", "arriba"))
    reporte = verificar(datos, decision)
    assert not reporte.valido
    assert len(reporte.errores) == 1


@pytest.mark.parametrize("orden", [ORDEN_DIRECCIONES_POR_DEFECTO, ORDEN_ALTERNATIVO])
def test_verificar_partida(datos, orden):
    partida = ejecutar_partida(datos, "Alfa-beta", 2, orden)
    reporte = verificar(datos, partida, orden)
    assert reporte.valido, reporte.errores


def test_verificar_tipo_desconocido(datos):
    with pytest.raises(TypeError):
        verificar(datos, "no es un resultado")


def test_ordenes_disponibles():
    assert len(ORDENES_DISPONIBLES) == 24
    assert len(set(ORDENES_DISPONIBLES)) == 24
    assert ORDENES_DISPONIBLES[0] == ORDEN_DIRECCIONES_POR_DEFECTO


def test_profundidad_inicial(datos):
    assert profundidad_inicial(datos) == 4
    assert profundidad_inicial(replace(datos, profundidad_maxima=2)) == 2
    assert profundidad_inicial(replace(datos, profundidad_maxima=None)) == 4


def test_formatear_busqueda(datos):
    resultado = ejecutar_busqueda(datos, "UCS")
    contenido = json.loads(formatear_busqueda(resultado, ORDEN_DIRECCIONES_POR_DEFECTO))
    assert set(contenido) == {
        "algoritmo", "exito", "camino", "costo", "estados_generados", "estados_expandidos",
        "maximo_frontera", "tiempo_ms", "orden",
    }
    assert contenido["camino"][0] == [0, 1]
    assert contenido["camino"][-1] == [3, 2]
    assert contenido["costo"] == 7
    assert contenido["orden"] == list(ORDEN_DIRECCIONES_POR_DEFECTO)


def test_formatear_decision(datos):
    decision = ejecutar_decision(datos, "Alfa-beta", 2)
    contenido = json.loads(formatear_decision(decision, ORDEN_ALTERNATIVO))
    assert contenido["accion_seleccionada"] == "A2 abajo"
    assert contenido["nodos_podados"] == decision.podas
    assert contenido["orden"] == list(ORDEN_ALTERNATIVO)


def test_formatear_partida(datos):
    partida = ejecutar_partida(datos, "Alfa-beta", 2)
    contenido = json.loads(formatear_partida(partida, ORDEN_DIRECCIONES_POR_DEFECTO))
    assert contenido["ganador"] == "B"
    assert contenido["turnos"] == len(contenido["jugadas"]) == partida.turnos
    empate = ejecutar_partida(replace(datos, limite_turnos=4), "Minimax", 2)
    assert json.loads(formatear_partida(empate, ORDEN_DIRECCIONES_POR_DEFECTO))["ganador"] == (
        "empate por límite"
    )


@pytest.mark.parametrize(
    "llamada",
    [
        lambda d: ejecutar_busqueda(d, "IDS"),
        lambda d: ejecutar_busqueda(d, "A*", heuristica="h9"),
        lambda d: ejecutar_busqueda(d, "BFS", orden=("arriba", "arriba", "abajo", "izquierda")),
        lambda d: ejecutar_decision(d, "Expectimax", 2),
        lambda d: ejecutar_decision(d, "Minimax", 2, orden=("arriba", "derecha")),
        lambda d: ejecutar_partida(d, "mcts", 2),
        lambda d: ejecutar_busqueda(replace(d, prueba=None), "BFS"),
    ],
)
def test_entradas_invalidas_lanzan_valueerror(datos, llamada):
    with pytest.raises(ValueError):
        llamada(datos)


def test_resumir_busqueda_con_exito(datos):
    texto = resumir_busqueda(ejecutar_busqueda(datos, "BFS"), ORDEN_DIRECCIONES_POR_DEFECTO, 1)
    assert texto.startswith("━━━━ #1 · Búsqueda · BFS · orden: arriba, derecha, abajo, izquierda")
    assert "✔ Camino encontrado" in texto
    assert "(0,1) → (0,2) → (1,2) → (2,2) → (3,2)" in texto
    linea_costo = next(linea for linea in texto.splitlines() if "Costo" in linea)
    assert "14" in linea_costo
    assert "14.0" not in texto


def test_resumir_busqueda_sin_exito(datos):
    resultado = ejecutar_busqueda(datos_mision(datos), "Beam", "h2", 1)
    assert not resultado.exito
    texto = resumir_busqueda(resultado, ORDEN_DIRECCIONES_POR_DEFECTO, 2)
    assert "✘ No existe camino" in texto
    assert "Beam (h2) · k=1" in texto
    assert "Expandidos" in texto


def test_resumir_busqueda_parte_caminos_largos(datos):
    resultado = ejecutar_busqueda(datos, "BFS")
    largo = replace(resultado, estados=resultado.estados * 3)
    texto = resumir_busqueda(largo, ORDEN_DIRECCIONES_POR_DEFECTO, 1)
    lineas_camino = [linea for linea in texto.splitlines() if linea.lstrip().startswith(("(", "→"))]
    assert len(lineas_camino) == 2
    assert lineas_camino[0].count("(") == 12
    assert lineas_camino[1].startswith("    → ")


def test_resumir_decision(datos):
    decision = ejecutar_decision(datos, "Alfa-beta", 2)
    texto = resumir_decision(decision, ORDEN_ALTERNATIVO, 2, 3)
    assert "Alfa-beta · profundidad 2 · orden: abajo, izquierda, arriba, derecha" in texto
    assert "A2 abajo" in texto
    assert "−114" in texto
    assert "-114" not in texto
    assert "Podados" in texto


def test_resumir_partida(datos):
    partida = ejecutar_partida(datos, "Alfa-beta", 2)
    texto = resumir_partida(partida, ORDEN_DIRECCIONES_POR_DEFECTO, 2, "Alfa-beta", 4)
    assert "Ganador: B" in texto
    assert "18" in texto
    assert "1. A2 abajo" in texto
    empate = ejecutar_partida(replace(datos, limite_turnos=4), "Minimax", 2)
    texto = resumir_partida(empate, ORDEN_DIRECCIONES_POR_DEFECTO, 2, "Minimax", 5)
    assert "Empate por límite de turnos" in texto


def test_dividir_camino_en_mision(datos):
    mision = datos_mision(datos)
    ida, vuelta = dividir_camino(ejecutar_busqueda(mision, "UCS"))
    assert ida == [(0, 1), (0, 0), (1, 0), (2, 0), (2, 1), (2, 2)]
    assert vuelta == [(2, 2), (2, 1), (2, 0), (1, 0), (0, 0)]
    assert ida[-1] == vuelta[0] == mision.recurso


def test_dividir_camino_en_prueba_normal(datos):
    # UCS: su camino no pasa por el recurso (BFS sí pasa por (2, 2) y lo recoge).
    resultado = ejecutar_busqueda(datos, "UCS")
    ida, vuelta = dividir_camino(resultado)
    assert vuelta == []
    assert ida == [e.posicion for e in resultado.estados]


def test_dividir_camino_con_unidad_portadora(datos):
    resultado = ejecutar_busqueda(replace(datos, portador="A1"), "UCS")
    ida, vuelta = dividir_camino(resultado)
    assert ida == []
    assert vuelta == [e.posicion for e in resultado.estados]


def test_dividir_camino_sin_exito(datos):
    resultado = ejecutar_busqueda(datos_mision(datos), "Beam", "h2", 1)
    assert not resultado.exito
    assert dividir_camino(resultado) == ([], [])


def test_resumir_verificacion():
    assert resumir_verificacion(ReporteVerificacion(True, (), 14.0)) == "✔ Verificado"
    reporte = ReporteVerificacion(False, ("error uno", "error dos"), None)
    texto = resumir_verificacion(reporte)
    assert texto.startswith("✘ 2 error(es)")
    assert texto.splitlines()[1:] == ["  - error uno", "  - error dos"]
