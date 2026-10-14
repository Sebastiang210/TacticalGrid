"""Pruebas del validador de escenarios (paso 2)."""

import copy
import json
from pathlib import Path

import pytest

from tacticalgrid.carga.cargador import ErrorCarga, ErrorValidacion, cargar_escenario
from tacticalgrid.carga.validador import validar

RAIZ = Path(__file__).resolve().parent.parent
RUTA_ENUNCIADO = RAIZ / "scenarios" / "dev" / "enunciado_4x4.json"
CARPETA_INVALIDOS = RAIZ / "scenarios" / "invalidos"


def json_base() -> dict:
    return json.loads(RUTA_ENUNCIADO.read_text(encoding="utf-8"))


def escribir_json(tmp_path: Path, contenido: dict, nombre: str = "escenario.json") -> Path:
    ruta = tmp_path / nombre
    ruta.write_text(json.dumps(contenido), encoding="utf-8")
    return ruta


def poner(*ruta_y_valor):
    """Devuelve una función que asigna el valor en la ruta indicada de un dict anidado."""
    *ruta, valor = ruta_y_valor

    def mutar(datos: dict) -> None:
        destino = datos
        for clave in ruta[:-1]:
            destino = destino[clave]
        destino[ruta[-1]] = valor

    return mutar


def _rutas(nodo, prefijo=()):
    if isinstance(nodo, dict):
        hijos = nodo.items()
    elif isinstance(nodo, list):
        hijos = enumerate(nodo)
    else:
        return
    for clave, hijo in hijos:
        ruta = (*prefijo, clave)
        yield ruta
        yield from _rutas(hijo, ruta)


def _padre(datos: dict, ruta: tuple):
    destino = datos
    for clave in ruta[:-1]:
        destino = destino[clave]
    return destino


RUTAS = list(_rutas(json_base()))
VALORES_BASURA = [None, True, 0, 3.5, "texto", [], {}, [[]], {"x": 1}]


def _nombre_ruta(ruta: tuple) -> str:
    return ".".join(map(str, ruta))


# ---------- validar: casos básicos ----------


def test_enunciado_no_tiene_errores():
    assert validar(json_base()) == []


def test_no_modifica_los_datos_y_es_determinista():
    datos = json_base()
    datos["turno"] = "X"
    datos["terreno"][0][0] = "lava"
    antes = copy.deepcopy(datos)
    primera = validar(datos)
    assert datos == antes
    assert primera == validar(copy.deepcopy(datos))


def test_reporta_todos_los_errores_juntos():
    datos = json_base()
    datos["terreno"][0][0] = "lava"
    datos["unidades"][3]["fila"] = 9
    datos["turno"] = "X"
    errores = validar(datos)
    assert len(errores) == 3
    assert any("lava" in e for e in errores)
    assert any("fuera del mapa" in e for e in errores)
    assert any(e.startswith("turno") for e in errores)


def test_mensajes_con_el_formato_del_enunciado():
    datos = json_base()
    datos["unidades"][3]["fila"] = 5
    datos["unidades"][3]["columna"] = 1
    assert validar(datos) == ["unidades[3] (B2): la posición (5, 1) está fuera del mapa de 4 × 4"]

    datos = json_base()
    datos["terreno"][1][2] = "lava"
    assert validar(datos) == ["terreno[1][2]: el terreno 'lava' no existe en tipos_terreno"]

    datos = json_base()
    datos["unidades"][0].update(fila=1, columna=1)
    assert validar(datos) == ["unidades[0] (A1): está sobre 'muro', que no es transitable"]

    datos = json_base()
    datos["unidades"][3]["id"] = "A1"
    assert validar(datos) == ["unidades: el id 'A1' está repetido"]


def test_id_repetido_tres_veces_se_reporta_una_vez():
    datos = json_base()
    datos["unidades"][1]["id"] = "A1"
    datos["unidades"][2]["id"] = "A1"
    assert validar(datos) == ["unidades: el id 'A1' está repetido"]


# ---------- estructura: sin excepciones y sin cascada ----------

# (identificador, mutador, cantidad exacta de errores): un solo error, sin cascada
CASOS_ESTRUCTURA = [
    ("sin_mapa", lambda d: d.pop("mapa"), 1),
    ("unidades_no_es_lista", poner("unidades", "A1"), 1),
    ("fila_de_unidad_es_texto", poner("unidades", 0, "fila", "2"), 1),
    ("filas_es_booleano", poner("mapa", "filas", True), 1),
    ("columnas_es_booleano", poner("mapa", "columnas", True), 1),
    ("fila_de_recurso_es_booleano", poner("recurso", "fila", True), 1),
    ("costo_booleano", poner("tipos_terreno", "camino", "costo", True), 1),
    ("costo_nan", poner("tipos_terreno", "camino", "costo", float("nan")), 1),
    ("costo_infinito", poner("tipos_terreno", "camino", "costo", float("inf")), 1),
    ("limite_turnos_booleano", poner("juego", "limite_turnos", True), 1),
    ("limite_turnos_null", poner("juego", "limite_turnos", None), 1),
]


@pytest.mark.parametrize(
    ("mutador", "cantidad"),
    [pytest.param(m, c, id=i) for i, m, c in CASOS_ESTRUCTURA],
)
def test_errores_de_estructura_sin_excepcion_ni_cascada(mutador, cantidad):
    datos = json_base()
    mutador(datos)
    errores = validar(datos)
    assert len(errores) == cantidad, errores
    assert all(isinstance(e, str) for e in errores)


def test_terreno_irregular_no_lanza_ni_hace_cascada():
    datos = json_base()
    datos["terreno"][0] = datos["terreno"][0][:3]
    datos["recurso"] = {"fila": 0, "columna": 3}
    assert validar(datos) == ["terreno[0]: tiene 3 columnas pero mapa.columnas es 4"]


@pytest.mark.parametrize("ruta", RUTAS, ids=_nombre_ruta)
def test_valor_basura_en_cualquier_ruta_no_lanza(ruta):
    for basura in VALORES_BASURA:
        datos = json_base()
        _padre(datos, ruta)[ruta[-1]] = basura
        errores = validar(datos)
        assert isinstance(errores, list)
        assert all(isinstance(e, str) for e in errores)


@pytest.mark.parametrize("ruta", RUTAS, ids=_nombre_ruta)
def test_campo_borrado_en_cualquier_ruta_no_lanza(ruta):
    datos = json_base()
    padre = _padre(datos, ruta)
    if isinstance(padre, dict):
        del padre[ruta[-1]]
    else:
        padre.pop(ruta[-1])
    errores = validar(datos)
    assert isinstance(errores, list)
    assert all(isinstance(e, str) for e in errores)


# ---------- mayúsculas y minúsculas ----------


def test_bandos_y_turno_en_minuscula_son_validos():
    datos = json_base()
    datos["turno"] = "b"
    datos["bases"] = {"a": {"fila": 0, "columna": 0}, "b": {"fila": 3, "columna": 3}}
    for unidad in datos["unidades"]:
        unidad["bando"] = unidad["bando"].lower()
    assert validar(datos) == []


def test_minusculas_se_cargan_normalizadas(tmp_path):
    datos = json_base()
    datos["turno"] = "b"
    for unidad in datos["unidades"]:
        unidad["bando"] = unidad["bando"].lower()
    resultado = cargar_escenario(escribir_json(tmp_path, datos))
    assert resultado.turno == "B"
    assert {u.bando for u in resultado.unidades} == {"A", "B"}


# ---------- reglas propias del equipo ----------


def _todo_intransitable(datos: dict) -> None:
    for definicion in datos["tipos_terreno"].values():
        definicion["transitable"] = False


# (identificador, mutador, texto esperado en algún error)
CASOS_PROPIOS = [
    ("base_sobre_muro", poner("bases", "A", {"fila": 1, "columna": 1}), "bases.A"),
    ("recurso_sobre_muro", poner("recurso", {"fila": 1, "columna": 1}), "recurso"),
    ("sin_terrenos_transitables", _todo_intransitable, "al menos un terreno transitable"),
    ("limite_turnos_cero", poner("juego", "limite_turnos", 0), "juego.limite_turnos"),
    (
        "profundidad_negativa",
        poner("juego", "profundidad_maxima_minimax", -1),
        "juego.profundidad_maxima_minimax",
    ),
    ("modo_desconocido", poner("prueba", "modo", "duelo"), "prueba.modo"),
    (
        "unidad_inicio_inexistente",
        poner("prueba", "unidad_inicio", "Z9"),
        "prueba.unidad_inicio",
    ),
    (
        "busqueda_sin_objetivo_ni_mision",
        lambda d: d["prueba"].pop("objetivo"),
        "'objetivo' o 'mision'",
    ),
    ("mision_desconocida", poner("prueba", "mision", "huir"), "prueba.mision"),
    (
        "objetivo_fuera_del_mapa",
        poner("prueba", "objetivo", {"fila": 9, "columna": 9}),
        "prueba.objetivo",
    ),
]


@pytest.mark.parametrize(
    ("mutador", "texto"),
    [pytest.param(m, t, id=i) for i, m, t in CASOS_PROPIOS],
)
def test_reglas_propias_del_equipo(mutador, texto):
    datos = json_base()
    mutador(datos)
    errores = validar(datos)
    assert any(texto in e for e in errores), errores


def test_busqueda_con_mision_y_sin_objetivo_es_valida():
    datos = json_base()
    del datos["prueba"]["objetivo"]
    datos["prueba"]["mision"] = "llevar_recurso"
    assert validar(datos) == []


def test_sin_prueba_y_con_juego_vacio_es_valido():
    datos = json_base()
    del datos["prueba"]
    datos["juego"] = {}
    assert validar(datos) == []


# ---------- integración con cargar_escenario ----------

# (archivo, texto clave que debe aparecer en el mensaje)
CASOS_INVALIDOS = [
    ("r1_dimensiones.json", "mapa.filas"),
    ("r2_terreno_inexistente.json", "lava"),
    ("r3_costo_no_positivo.json", "costo"),
    ("r4_fuera_del_mapa.json", "fuera del mapa"),
    ("r5_unidad_sobre_muro.json", "no es transitable"),
    ("r6_id_repetido.json", "repetido"),
    ("r7_bando_invalido.json", "bando"),
    ("r8_turno_invalido.json", "turno"),
    ("r9_portador_inexistente.json", "Z9"),
]


@pytest.mark.parametrize(("archivo", "texto"), CASOS_INVALIDOS)
def test_archivo_invalido_da_exactamente_un_error(archivo, texto):
    with pytest.raises(ErrorValidacion) as info:
        cargar_escenario(CARPETA_INVALIDOS / archivo)
    assert len(info.value.errores) == 1
    assert texto in str(info.value)


def test_error_validacion_es_error_carga_y_conserva_los_errores(tmp_path):
    datos = json_base()
    datos["turno"] = "X"
    datos["terreno"][0][0] = "lava"
    esperados = validar(datos)
    assert issubclass(ErrorValidacion, ErrorCarga)
    with pytest.raises(ErrorCarga) as info:
        cargar_escenario(escribir_json(tmp_path, datos))
    assert isinstance(info.value, ErrorValidacion)
    assert info.value.errores == tuple(esperados)
    lineas = str(info.value).splitlines()
    assert "2 errores" in lineas[0]
    assert lineas[1:] == [f"- {e}" for e in esperados]


def test_un_solo_error_usa_singular(tmp_path):
    datos = json_base()
    datos["turno"] = "X"
    with pytest.raises(ErrorValidacion) as info:
        cargar_escenario(escribir_json(tmp_path, datos))
    primera_linea = str(info.value).splitlines()[0]
    assert "1 error" in primera_linea
    assert "errores" not in primera_linea
