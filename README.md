# TacticalGrid

Juego táctico por turnos sobre una cuadrícula en el que dos bandos, A y B, compiten por llevar un recurso a su base. Proyecto 1 de **Sistemas Inteligentes I**, Universidad de Caldas, 2026-2.

**Integrantes:** Cristian David Gonzalez · Sebastian Garcia Hincapie
**Docente:** Jairo Iván Vélez Bedoya

## Qué hace

- **Búsqueda:** resuelve la navegación de una unidad hasta un objetivo, o la misión de recoger el recurso y llevarlo a su base, con BFS, DFS, UCS, A* (heurísticas h1 Manhattan y h2 pasos rodeando obstáculos) y Beam Search. Muestra el camino, las métricas y los estados expandidos sobre el mapa.
- **Adversarial:** recomienda una jugada con Minimax o alfa-beta a la profundidad elegida, y muestra el valor de cada jugada considerada (exacto o cota por poda).
- **Partida:** juega una partida completa entre dos IA y permite recorrerla turno a turno.
- **Verificación:** comprueba cada resultado con un verificador independiente del código de búsqueda.

Todo se configura con escenarios en JSON y se usa desde una interfaz Tkinter.

## Requisitos

- Python 3.11 o superior, con Tkinter. En Windows, al instalar Python debe quedar marcada la opción "tcl/tk and IDLE".
- La aplicación no usa bibliotecas externas. Las pruebas y los experimentos usan pytest, ruff, pandas y matplotlib, que se instalan con el grupo de desarrollo.

## Instalación

Desde la carpeta raíz del proyecto (donde está `pyproject.toml`):

```bash
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
```

En Linux o macOS se usa `.venv/bin/` en lugar de `.venv\Scripts\`.

## Uso

```bash
.venv\Scripts\python -m tacticalgrid
```

1. Pulsar **Cargar escenario** y elegir un archivo de `scenarios/`.
2. Elegir el modo (Búsqueda, Adversarial o Partida), el algoritmo y sus parámetros.
3. Pulsar **Ejecutar** y luego **Verificar**.

El detalle de cada modo, el formato del JSON y la solución de problemas comunes están en la carpeta docs/ Manual de usuario

## Escenarios incluidos

| Archivo | Para qué sirve |
|---|---|
| `scenarios/dev/enunciado_4x4.json` | Ejemplo del enunciado: búsqueda de A1 hasta (3,2) |
| `scenarios/casos/caso3_muro.json` | Muro entre la unidad y el objetivo; compara h1 y h2 |
| `scenarios/casos/caso6_mision.json` | Misión llevar_recurso en el mapa del enunciado; Beam con distintos k |
| `scenarios/casos/caso6_mision_grande.json` | Misión en un mapa de 8 × 10 con el recurso en un callejón |
| `scenarios/casos/caso7_8_10_adversarial.json` | Minimax, alfa-beta y efecto de la profundidad |
| `scenarios/casos/caso9_orden.json` | Efecto del orden de direcciones en la poda |
| `scenarios/invalidos/` | Un archivo con un error por cada regla de validación |

## Pruebas y experimentos

```bash
.venv\Scripts\python -m pytest
.venv\Scripts\ruff check .
.venv\Scripts\python experiments\ejecutar_experimentos.py
```

Los experimentos dejan las tablas (CSV), las gráficas (PNG) y `resumen.txt` en `experiments/resultados/`. La ejecución completa tarda algunos minutos.

## Estructura

```
tacticalgrid/
  core/           escenario, estado de navegación y reglas del juego
  busqueda/       problema, BFS, DFS, UCS, A*, Beam y heurísticas
  adversarial/    distancias, función de utilidad, Minimax/alfa-beta y partidas
  verificacion/   verificador independiente de caminos, decisiones y partidas
  ui/             servicio (lógica de la interfaz) y aplicación Tkinter
scenarios/        escenarios JSON
experiments/      script de experimentos y resultados
tests/            pruebas automáticas (pytest)
```

## Documentación

Tambien se pueden encontrar en docs/

- [Manual tecnico](https://docs.google.com/document/d/1gCEgItEXfT0vpu_p7P7babAeDgl4QMM8l5ookqFRMMY/edit?usp=sharing)
- [Manual de usuario](https://docs.google.com/document/d/1xBcyM05upIPf4DEnosoriLLCqWFjAKSHENCO24SP1zQ/edit?usp=sharing)