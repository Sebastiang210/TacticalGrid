"""Pruebas del problema de navegación (paso 3)."""

from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from tacticalgrid.busqueda.problema import ProblemaNavegacion
from tacticalgrid.carga.cargador import Prueba, cargar_escenario
from tacticalgrid.core.navegacion import EstadoNavegacion

RUTA_ENUNCIADO = (
    Path(__file__).resolve().parent.parent / "scenarios" / "dev" / "enunciado_4x4.json"
)


@pytest.fixture
def datos():
    return cargar_escenario(RUTA_ENUNCIADO)


@pytest.fixture
def problema(datos):
    return ProblemaNavegacion(datos)


def datos_mision(datos, objetivo=None):
    prueba = Prueba(modo="busqueda", unidad_inicio="A1", objetivo=objetivo, mision="llevar_recurso")
    return replace(datos, prueba=prueba)


def test_inicial(problema):
    assert problema.inicial() == EstadoNavegacion(0, 1, False)


def test_expone_escenario_unidad_y_objetivo(problema, datos):
    assert problema.escenario is datos.escenario
    assert problema.unidad == "A1"
    assert problema.objetivo == (3, 2)
    assert problema.es_mision is False


def test_expone_base_y_recurso_disponible(problema):
    assert problema.base == (0, 0)
    assert problema.recurso_disponible == (2, 2)


def test_recurso_con_portador_no_esta_disponible(datos):
    problema = ProblemaNavegacion(replace(datos, portador="B1"))
    assert problema.recurso_disponible is None
    assert problema.base == (0, 0)


def test_sucesores_del_estado_inicial_en_orden(problema):
    assert problema.sucesores(EstadoNavegacion(0, 1, False)) == [
        ("derecha", EstadoNavegacion(0, 2, False), 2),
        ("izquierda", EstadoNavegacion(0, 0, False), 1),
    ]


def test_entrar_al_recurso_lo_recoge(problema):
    sucesores = {a: s for a, s, _ in problema.sucesores(EstadoNavegacion(2, 1, False))}
    assert sucesores["derecha"] == EstadoNavegacion(2, 2, True)


def test_una_vez_recogido_nunca_se_suelta(problema):
    for fila in range(4):
        for columna in range(4):
            estado = EstadoNavegacion(fila, columna, True)
            if problema.escenario.es_transitable(estado.posicion):
                assert all(s.lleva_recurso for _, s, _ in problema.sucesores(estado))


def test_no_hay_sucesores_sobre_muro_ni_fuera_del_mapa(problema):
    esc = problema.escenario
    for fila in range(esc.filas):
        for columna in range(esc.columnas):
            for lleva in (False, True):
                estado = EstadoNavegacion(fila, columna, lleva)
                if not esc.es_transitable(estado.posicion):
                    continue
                for _, sucesor, _ in problema.sucesores(estado):
                    assert esc.dentro(sucesor.posicion)
                    assert esc.es_transitable(sucesor.posicion)


def test_otras_unidades_no_bloquean(problema, datos):
    ocupada = {u.posicion for u in datos.unidades if u.id != "A1"}
    assert (3, 2) in ocupada
    destinos = [s.posicion for _, s, _ in problema.sucesores(EstadoNavegacion(3, 1, False))]
    assert (3, 2) in destinos


def test_costo_es_el_del_terreno_destino(problema):
    inicio = EstadoNavegacion(0, 1, False)
    for _, sucesor, costo_sucesor in problema.sucesores(inicio):
        assert problema.costo(inicio, sucesor) == costo_sucesor
        assert costo_sucesor == problema.escenario.costo(sucesor.posicion)


def test_es_objetivo_en_prueba_normal(problema):
    assert problema.es_objetivo(EstadoNavegacion(3, 2, False))
    assert problema.es_objetivo(EstadoNavegacion(3, 2, True))
    assert not problema.es_objetivo(EstadoNavegacion(0, 0, True))


def test_es_objetivo_en_mision(datos):
    problema = ProblemaNavegacion(datos_mision(datos))
    assert problema.es_mision is True
    assert problema.objetivo is None
    assert problema.es_objetivo(EstadoNavegacion(0, 0, True))
    assert not problema.es_objetivo(EstadoNavegacion(0, 0, False))
    assert not problema.es_objetivo(EstadoNavegacion(3, 3, True))


def test_mision_tiene_prioridad_sobre_objetivo(datos):
    problema = ProblemaNavegacion(datos_mision(datos, objetivo=(3, 2)))
    assert not problema.es_objetivo(EstadoNavegacion(3, 2, False))
    assert problema.es_objetivo(EstadoNavegacion(0, 0, True))


def test_portador_ajeno_no_cambia_indicador(datos):
    problema = ProblemaNavegacion(replace(datos, portador="B1"))
    assert problema.inicial().lleva_recurso is False
    sucesores = {a: s for a, s, _ in problema.sucesores(EstadoNavegacion(2, 1, False))}
    assert sucesores["derecha"] == EstadoNavegacion(2, 2, False)


def test_unidad_de_inicio_portadora_arranca_con_recurso(datos):
    problema = ProblemaNavegacion(replace(datos, portador="A1"))
    assert problema.inicial() == EstadoNavegacion(0, 1, True)
    sucesores = {a: s for a, s, _ in problema.sucesores(problema.inicial())}
    assert all(s.lleva_recurso for s in sucesores.values())


def test_orden_alternativo_cambia_el_orden_de_sucesores(datos):
    problema = ProblemaNavegacion(
        datos, orden_direcciones=("izquierda", "abajo", "derecha", "arriba")
    )
    acciones = [a for a, _, _ in problema.sucesores(EstadoNavegacion(0, 1, False))]
    assert acciones == ["izquierda", "derecha"]


def test_orden_como_lista_es_valido(datos):
    orden = ["abajo", "arriba", "izquierda", "derecha"]
    problema = ProblemaNavegacion(datos, orden_direcciones=orden)
    acciones = [a for a, _, _ in problema.sucesores(EstadoNavegacion(0, 1, False))]
    assert acciones == ["izquierda", "derecha"]


@pytest.mark.parametrize(
    "orden",
    [
        ("arriba", "arriba", "abajo", "izquierda"),
        ("arriba", "derecha", "abajo"),
        ("arriba", "derecha", "abajo", "izquierda", "arriba"),
        ("arriba", "derecha", "abajo", "diagonal"),
        "arriba",
        (),
    ],
)
def test_orden_invalido_lanza_value_error(datos, orden):
    with pytest.raises(ValueError, match="direcciones"):
        ProblemaNavegacion(datos, orden_direcciones=orden)


def test_prueba_ausente_lanza_value_error(datos):
    with pytest.raises(ValueError, match="busqueda"):
        ProblemaNavegacion(replace(datos, prueba=None))


def test_modo_partida_lanza_value_error(datos):
    prueba = Prueba(modo="partida", unidad_inicio=None, objetivo=None, mision=None)
    with pytest.raises(ValueError, match="busqueda"):
        ProblemaNavegacion(replace(datos, prueba=prueba))


@pytest.mark.parametrize("inicio", [None, "Z9"])
def test_unidad_inicio_inexistente_lanza_value_error(datos, inicio):
    prueba = Prueba(modo="busqueda", unidad_inicio=inicio, objetivo=(3, 2), mision=None)
    with pytest.raises(ValueError, match="unidad"):
        ProblemaNavegacion(replace(datos, prueba=prueba))


def test_estado_es_inmutable_y_usable_en_sets():
    estado = EstadoNavegacion(1, 2, False)
    with pytest.raises(FrozenInstanceError):
        estado.fila = 5
    assert estado.posicion == (1, 2)
    assert len({estado, EstadoNavegacion(1, 2, False), EstadoNavegacion(1, 2, True)}) == 2
