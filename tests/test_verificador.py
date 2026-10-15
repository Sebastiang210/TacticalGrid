"""Pruebas del verificador de caminos de búsqueda."""

from dataclasses import replace

import pytest
from conftest import RUTA_MURO, datos_mision

from tacticalgrid.busqueda.heuristicas import h_manhattan, h_pasos
from tacticalgrid.busqueda.informada import a_estrella, beam
from tacticalgrid.busqueda.no_informada import bfs, dfs, ucs
from tacticalgrid.busqueda.problema import ProblemaNavegacion
from tacticalgrid.carga.cargador import cargar_escenario
from tacticalgrid.core.navegacion import EstadoNavegacion
from tacticalgrid.verificacion.verificador import verificar_camino


def datos_del_caso(nombre, datos):
    if nombre == "enunciado":
        return datos
    if nombre == "mision":
        return datos_mision(datos)
    return cargar_escenario(RUTA_MURO)


ALGORITMOS = {
    "bfs": bfs,
    "dfs": dfs,
    "ucs": ucs,
    "a_estrella_h1": lambda p: a_estrella(p, h_manhattan(p), "manhattan"),
    "a_estrella_h2": lambda p: a_estrella(p, h_pasos(p), "pasos"),
    "beam_1": lambda p: beam(p, h_manhattan(p), "manhattan", 1),
    "beam_2": lambda p: beam(p, h_manhattan(p), "manhattan", 2),
    "beam_8": lambda p: beam(p, h_manhattan(p), "manhattan", 8),
}


@pytest.mark.parametrize("caso", ["enunciado", "mision", "muro"])
@pytest.mark.parametrize("algoritmo", list(ALGORITMOS))
def test_resultados_de_los_algoritmos_son_validos(datos, caso, algoritmo):
    datos_caso = datos_del_caso(caso, datos)
    resultado = ALGORITMOS[algoritmo](ProblemaNavegacion(datos_caso))
    reporte = verificar_camino(datos_caso, resultado)
    assert reporte.valido, reporte.errores
    assert reporte.errores == ()
    if resultado.exito:
        assert reporte.costo_recalculado == resultado.costo


def test_resultado_sin_exito_es_valido(problema_inalcanzable, datos):
    resultado = bfs(problema_inalcanzable)
    assert not resultado.exito
    assert verificar_camino(datos, resultado).valido


@pytest.fixture
def base(datos):
    resultado = ucs(ProblemaNavegacion(datos))
    assert resultado.exito and len(resultado.estados) >= 4
    return resultado


def con_estado(resultado, indice, estado):
    estados = list(resultado.estados)
    estados[indice] = estado
    return replace(resultado, estados=tuple(estados))


def textos(reporte):
    return " | ".join(reporte.errores)


def test_detecta_costo_cambiado(datos, base):
    reporte = verificar_camino(datos, replace(base, costo=base.costo + 1))
    assert not reporte.valido
    assert "costo" in textos(reporte)
    assert reporte.costo_recalculado == base.costo


def test_detecta_salto_de_dos_casillas(datos, base):
    e0, e1 = base.estados[0], base.estados[1]
    salto = EstadoNavegacion(
        e0.fila + 2 * (e1.fila - e0.fila), e0.columna + 2 * (e1.columna - e0.columna), False
    )
    reporte = verificar_camino(datos, con_estado(base, 1, salto))
    assert not reporte.valido
    assert "Paso 1" in textos(reporte)


def test_detecta_paso_sobre_muro(datos, base):
    reporte = verificar_camino(datos, con_estado(base, 1, EstadoNavegacion(1, 1, False)))
    assert not reporte.valido
    assert "no es transitable" in textos(reporte)


def test_detecta_accion_que_no_coincide(datos, base):
    opuesta = {"arriba": "abajo", "abajo": "arriba", "izquierda": "derecha", "derecha": "izquierda"}
    acciones = (opuesta[base.acciones[0]], *base.acciones[1:])
    reporte = verificar_camino(datos, replace(base, acciones=acciones))
    assert not reporte.valido
    assert "Paso 1" in textos(reporte)


def test_detecta_accion_desconocida(datos, base):
    reporte = verificar_camino(datos, replace(base, acciones=("saltar", *base.acciones[1:])))
    assert not reporte.valido
    assert "desconocida" in textos(reporte)


def test_detecta_ultimo_estado_que_no_es_objetivo(datos, base):
    reporte = verificar_camino(
        datos, replace(base, estados=base.estados[:-1], acciones=base.acciones[:-1])
    )
    assert not reporte.valido
    assert "objetivo" in textos(reporte)


def test_detecta_lleva_recurso_sin_pasar_por_el_recurso(datos, base):
    e = base.estados[2]
    reporte = verificar_camino(datos, con_estado(base, 2, replace(e, lleva_recurso=True)))
    assert not reporte.valido
    assert "lleva_recurso" in textos(reporte)


def test_detecta_inicio_equivocado(datos, base):
    reporte = verificar_camino(datos, con_estado(base, 0, EstadoNavegacion(3, 3, False)))
    assert not reporte.valido
    assert "Paso 0" in textos(reporte)


def test_detecta_longitudes_inconsistentes(datos, base):
    reporte = verificar_camino(datos, replace(base, acciones=base.acciones[:-1]))
    assert not reporte.valido


def test_detecta_exito_falso_con_datos(datos, base):
    reporte = verificar_camino(datos, replace(base, exito=False))
    assert not reporte.valido


def test_dos_defectos_reportan_al_menos_dos_errores(datos, base):
    alterado = con_estado(
        replace(base, costo=base.costo + 5), 2, replace(base.estados[2], lleva_recurso=True)
    )
    reporte = verificar_camino(datos, alterado)
    assert len(reporte.errores) >= 2
    assert not reporte.valido


def test_exige_prueba_de_busqueda(datos, base):
    with pytest.raises(ValueError):
        verificar_camino(replace(datos, prueba=None), base)
    prueba = replace(datos.prueba, modo="juego")
    with pytest.raises(ValueError):
        verificar_camino(replace(datos, prueba=prueba), base)
