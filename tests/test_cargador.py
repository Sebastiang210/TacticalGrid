"""Pruebas del cargador de escenarios (paso 1)."""

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from tacticalgrid.carga.cargador import ErrorCarga, cargar_escenario, leer_json
from tacticalgrid.core.escenario import TipoTerreno

RUTA_ENUNCIADO = (
    Path(__file__).resolve().parent.parent / "scenarios" / "dev" / "enunciado_4x4.json"
)


@pytest.fixture
def datos():
    return cargar_escenario(RUTA_ENUNCIADO)


def escribir_json(tmp_path: Path, contenido: dict, nombre: str = "escenario.json") -> Path:
    ruta = tmp_path / nombre
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return ruta


def json_base() -> dict:
    return json.loads(RUTA_ENUNCIADO.read_text(encoding="utf-8"))


def test_dimensiones(datos):
    assert datos.escenario.filas == 4
    assert datos.escenario.columnas == 4
    


def test_muro_y_limites(datos):
    esc = datos.escenario
    assert esc.tipo_en((1, 1)).nombre == "muro"
    assert not esc.es_transitable((1, 1))
    assert not esc.dentro((4, 0))
    assert not esc.es_transitable((4, 0))


def test_coordenadas_negativas_no_dan_la_vuelta(datos):
    esc = datos.escenario
    assert not esc.dentro((-1, 0))
    assert not esc.dentro((0, -1))
    assert not esc.es_transitable((-1, 0))
    with pytest.raises(ValueError):
        esc.tipo_en((-1, 0))
    with pytest.raises(ValueError):
        esc.costo((0, -1))


def test_costos(datos):
    esc = datos.escenario
    assert esc.costo((2, 2)) == 7
    assert esc.costo((0, 1)) == 1
    assert esc.costo_minimo == 1


def test_costo_de_muro_lanza_value_error(datos):
    with pytest.raises(ValueError):
        datos.escenario.costo((1, 1))


def test_costo_de_terreno_no_transitable_es_none(datos):
    assert datos.escenario.tipos_terreno["muro"].costo is None


def test_bases(datos):
    assert datos.escenario.base_de("A") == (0, 0)
    assert datos.escenario.base_de("B") == (3, 3)
    with pytest.raises(KeyError):
        datos.escenario.base_de("C")


def test_unidades(datos):
    assert len(datos.unidades) == 4
    assert [u.id for u in datos.unidades] == ["A1", "A2", "B1", "B2"]
    a1 = datos.unidades[0]
    assert a1.posicion == (0, 1)
    assert a1.bando == "A"
    assert a1.tipo == "estandar"


def test_campos_de_juego(datos):
    assert datos.version == "1.0"
    assert datos.recurso == (2, 2)
    assert datos.turno == "A"
    assert datos.portador is None
    assert datos.profundidad_maxima == 4
    assert datos.limite_turnos == 200


def test_prueba(datos):
    assert datos.prueba is not None
    assert datos.prueba.modo == "busqueda"
    assert datos.prueba.unidad_inicio == "A1"
    assert datos.prueba.objetivo == (3, 2)
    assert datos.prueba.mision is None


def test_limite_turnos_propio(tmp_path):
    contenido = json_base()
    contenido["juego"]["limite_turnos"] = 30
    assert cargar_escenario(escribir_json(tmp_path, contenido)).limite_turnos == 30


def test_normaliza_bandos_y_turno_a_mayuscula(tmp_path):
    contenido = json_base()
    contenido["turno"] = "a"
    contenido["bases"] = {"a": {"fila": 0, "columna": 0}, "b": {"fila": 3, "columna": 3}}
    for unidad in contenido["unidades"]:
        unidad["bando"] = unidad["bando"].lower()
    resultado = cargar_escenario(escribir_json(tmp_path, contenido))
    assert resultado.turno == "A"
    assert {u.bando for u in resultado.unidades} == {"A", "B"}
    assert set(resultado.escenario.bases) == {"A", "B"}
    assert resultado.unidades[0].tipo == "estandar"


def test_campos_opcionales_ausentes(tmp_path):
    contenido = json_base()
    contenido["juego"] = {}
    del contenido["prueba"]
    resultado = cargar_escenario(escribir_json(tmp_path, contenido))
    assert resultado.profundidad_maxima is None
    assert resultado.limite_turnos == 200
    assert resultado.prueba is None


def test_archivo_inexistente(tmp_path):
    with pytest.raises(ErrorCarga, match="No existe"):
        cargar_escenario(tmp_path / "no_existe.json")


def test_json_mal_formado_indica_linea_y_columna(tmp_path):
    ruta = tmp_path / "malo.json"
    ruta.write_text('{\n  "a": 1\n  "b": 2\n}', encoding="utf-8")
    with pytest.raises(ErrorCarga, match=r"línea 3.*columna 3"):
        cargar_escenario(ruta)


def test_raiz_que_no_es_objeto(tmp_path):
    ruta = tmp_path / "lista.json"
    ruta.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ErrorCarga, match="objeto"):
        leer_json(ruta)


def test_ruta_que_es_carpeta(tmp_path):
    with pytest.raises(ErrorCarga):
        leer_json(tmp_path)


def test_bytes_que_no_son_utf8(tmp_path):
    ruta = tmp_path / "latin1.json"
    ruta.write_bytes('{"a": "ñ"}'.encode("latin-1"))
    with pytest.raises(ErrorCarga, match="UTF-8"):
        leer_json(ruta)


def test_archivo_con_bom_se_carga(tmp_path):
    ruta = tmp_path / "bom.json"
    ruta.write_text(json.dumps(json_base()), encoding="utf-8-sig")
    assert cargar_escenario(ruta).escenario.filas == 4


def test_inmutabilidad(datos):
    esc = datos.escenario
    with pytest.raises(FrozenInstanceError):
        esc.filas = 10
    with pytest.raises(TypeError):
        esc.tipos_terreno["lava"] = TipoTerreno("lava", True, 9.0)
    with pytest.raises(TypeError):
        esc.bases["C"] = (0, 0)
    with pytest.raises(FrozenInstanceError):
        datos.turno = "B"
