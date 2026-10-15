"""Constantes globales del proyecto."""

LIMITE_TURNOS_POR_DEFECTO = 200

ORDEN_DIRECCIONES_POR_DEFECTO = ("arriba", "derecha", "abajo", "izquierda")
DESPLAZAMIENTOS = {"arriba": (-1, 0), "derecha": (0, 1), "abajo": (1, 0), "izquierda": (0, -1)}

PESO_POSESION = 100
PESO_AVANCE = 5
PESO_CARRERA = 2
PESO_PERSECUCION = 3
UTILIDAD_VICTORIA = 10_000
DISTANCIA_INALCANZABLE = 1_000
PROFUNDIDAD_POR_DEFECTO = 4
