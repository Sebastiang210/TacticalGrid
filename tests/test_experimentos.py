"""Pruebas del script de experimentos (modo rápido, sin matplotlib)."""

import csv
import importlib.util
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
ARCHIVOS_CSV = (
    "busqueda.csv",
    "beam.csv",
    "adversarial_profundidad.csv",
    "orden_poda.csv",
    "partidas.csv",
    "costo_pantano.csv",
    "dfs_orden.csv",
)


@pytest.fixture(scope="module")
def corrida(tmp_path_factory):
    ruta = RAIZ / "experiments" / "ejecutar_experimentos.py"
    spec = importlib.util.spec_from_file_location("ejecutar_experimentos", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    salida = tmp_path_factory.mktemp("resultados")
    codigo = modulo.ejecutar_todo(salida, rapido=True)
    return codigo, salida


def leer(salida, nombre):
    with (salida / nombre).open(encoding="utf-8", newline="") as archivo:
        return list(csv.DictReader(archivo))


def test_termina_con_codigo_cero(corrida):
    assert corrida[0] == 0


def test_se_generan_los_archivos(corrida):
    _, salida = corrida
    for nombre in (*ARCHIVOS_CSV, "resumen.txt"):
        assert (salida / nombre).is_file(), nombre


def test_busqueda_trae_bfs_y_ucs_del_4x4(corrida):
    filas = leer(corrida[1], "busqueda.csv")
    por_algoritmo = {f["algoritmo"]: f for f in filas if f["escenario"] == "E4x4"}
    assert por_algoritmo["BFS"]["costo"] == "14"
    assert por_algoritmo["UCS"]["costo"] == "7"
    assert por_algoritmo["UCS"]["camino"].startswith("(0,1)>")


def test_todas_las_filas_estan_verificadas(corrida):
    _, salida = corrida
    for nombre in ARCHIVOS_CSV:
        filas = leer(salida, nombre)
        assert filas, nombre
        if "verificado" in filas[0]:
            assert all(f["verificado"] == "True" for f in filas), nombre


def test_los_csv_incluyen_python_y_sistema(corrida):
    _, salida = corrida
    for nombre in ARCHIVOS_CSV:
        fila = leer(salida, nombre)[0]
        assert fila["python"] and fila["sistema"], nombre


def test_resumen_tiene_comprobaciones(corrida):
    texto = (corrida[1] / "resumen.txt").read_text(encoding="utf-8")
    assert "✔" in texto
    assert "Total:" in texto
