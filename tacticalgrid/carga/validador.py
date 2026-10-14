"""Validación del escenario JSON: reporta todos los errores, no solo el primero."""

import math
from dataclasses import dataclass

from tacticalgrid.core.escenario import Posicion

BANDOS = ("A", "B")
MODOS_PRUEBA = ("busqueda", "partida", "adversarial")
MISIONES = ("llevar_recurso",)

Dimensiones = tuple[int, int]  # (filas, columnas)
Catalogo = dict[str, bool | None]  


@dataclass(frozen=True)
class _Contexto:
    """Lo que ya se pudo validar del mapa; None indica que esa parte está rota o falta."""

    dimensiones: Dimensiones | None
    matriz: list | None
    tipos: Catalogo | None


def _es_entero(valor: object) -> bool:
    """True si valor es int y no bool (en Python True es un int)."""
    return isinstance(valor, int) and not isinstance(valor, bool)


def _es_entero_positivo(valor: object) -> bool:
    """True si valor es un entero positivo que no es booleano."""
    return _es_entero(valor) and valor > 0


def _es_numero(valor: object) -> bool:
    """True si valor es int o float y no bool."""
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _exigir_objeto(contenedor: dict, clave: str, ruta: str, errores: list[str]) -> dict | None:
    """
    Purpose: Obtener contenedor[clave] exigiendo que exista y sea un objeto JSON (dict).
    Preconditions: contenedor es un dict; errores es la lista de errores en construcción.
    Postconditions: Devuelve el dict o None; en ese caso agrega un mensaje a errores.
    Complexity: tiempo O(1), espacio O(1)
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation:  se leyó el flujo completo y el
        orden de las fases. Probado con tests/test_validador.py: el JSON 4x4 da 0 errores,
        cada archivo de scenarios/invalidos da exactamente 1 error
    """
    if clave not in contenedor:
        errores.append(f"{ruta}: falta el campo obligatorio")
        return None
    valor = contenedor[clave]
    if not isinstance(valor, dict):
        errores.append(f"{ruta}: debe ser un objeto")
        return None
    return valor


def _exigir_texto(contenedor: dict, clave: str, ruta: str, errores: list[str]) -> str | None:
    """
    Purpose: Obtener contenedor[clave] exigiendo que exista y sea un texto.
    Preconditions: contenedor es un dict; errores es la lista de errores en construcción.
    Postconditions: Devuelve el texto o None; en ese caso agrega un mensaje a errores.
        Si ruta es el propio campo (por ejemplo "turno") el mensaje no repite el nombre.
    Complexity: tiempo O(1), espacio O(1)
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation:  se leyó el flujo completo y el
        orden de las fases. Probado con tests/test_validador.py: el JSON 4x4 da 0 errores,
        cada archivo de scenarios/invalidos da exactamente 1 error
    """
    campo = ruta if ruta == clave else f"{ruta}.{clave}"
    if clave not in contenedor:
        errores.append(f"{campo}: falta el campo obligatorio")
        return None
    valor = contenedor[clave]
    if not isinstance(valor, str):
        errores.append(f"{campo}: debe ser un texto, no {valor!r}")
        return None
    return valor


def _leer_posicion(objeto: object, ruta: str, errores: list[str]) -> Posicion | None:
    """
    Purpose: Leer {"fila": f, "columna": c} con enteros (los booleanos no valen).
    Preconditions: errores es la lista de errores en construcción.
    Postconditions: Devuelve (fila, columna) o None si algo está mal; cada problema agrega
        un mensaje. No revisa límites del mapa.
    Complexity: tiempo O(1), espacio O(1)
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation:  se leyó el flujo completo y el
        orden de las fases. Probado con tests/test_validador.py: el JSON 4x4 da 0 errores,
        cada archivo de scenarios/invalidos da exactamente 1 error
    """
    if not isinstance(objeto, dict):
        errores.append(f"{ruta}: debe ser un objeto con 'fila' y 'columna'")
        return None
    valores: list[int] = []
    for campo in ("fila", "columna"):
        if campo not in objeto:
            errores.append(f"{ruta}: falta el campo '{campo}'")
        elif not _es_entero(objeto[campo]):
            errores.append(f"{ruta}: '{campo}' debe ser un número entero, no {objeto[campo]!r}")
        else:
            valores.append(objeto[campo])
    return (valores[0], valores[1]) if len(valores) == 2 else None


def _nombre_en(matriz: list | None, pos: Posicion) -> str | None:
    """
    Purpose: Nombre del terreno en pos, tolerando matrices irregulares.
    Preconditions: pos tiene coordenadas no negativas.
    Postconditions: Devuelve el nombre o None si la matriz es nula, la celda no existe o no
        es un texto. Nunca lanza.
    Complexity: tiempo O(1), espacio O(1)
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation:  se leyó el flujo completo y el
        orden de las fases. Probado con tests/test_validador.py: el JSON 4x4 da 0 errores,
        cada archivo de scenarios/invalidos da exactamente 1 error
    """
    if matriz is None:
        return None
    fila, columna = pos
    if fila >= len(matriz) or not isinstance(matriz[fila], list):
        return None
    if columna >= len(matriz[fila]):
        return None
    celda = matriz[fila][columna]
    return celda if isinstance(celda, str) else None


def _revisar_celda(
    pos: Posicion, ruta: str, ctx: _Contexto, errores: list[str], exigir_transitable: bool
) -> None:
    """
    Purpose: Revisar que pos esté dentro del mapa y, si se pide, sobre terreno transitable.
    Preconditions: pos es una posición de enteros; ctx trae lo ya validado del mapa.
    Postconditions: Agrega a errores "fuera del mapa" o "no es transitable"; no hace nada si
        las dimensiones, la matriz o el catálogo están rotos (evita cascadas).
    Complexity: tiempo O(1), espacio O(1)
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation:  se leyó el flujo completo y el
        orden de las fases. Probado con tests/test_validador.py: el JSON 4x4 da 0 errores,
        cada archivo de scenarios/invalidos da exactamente 1 error
    """
    if ctx.dimensiones is None:
        return
    filas, columnas = ctx.dimensiones
    fila, columna = pos
    if not (0 <= fila < filas and 0 <= columna < columnas):
        errores.append(
            f"{ruta}: la posición ({fila}, {columna}) está fuera del mapa de {filas} × {columnas}"
        )
        return
    if not exigir_transitable or ctx.tipos is None:
        return
    nombre = _nombre_en(ctx.matriz, pos)
    if nombre is not None and ctx.tipos.get(nombre) is False:
        errores.append(f"{ruta}: está sobre '{nombre}', que no es transitable")


def _validar_mapa(datos: dict, errores: list[str]) -> Dimensiones | None:
    """
    Purpose: Validar mapa.filas y mapa.columnas (R1, parte de los enteros positivos).
    Preconditions: datos es un dict.
    Postconditions: Devuelve (filas, columnas) o None si falta o está mal alguno.
    Complexity: tiempo O(1), espacio O(1)
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation:  se leyó el flujo completo y el
        orden de las fases. Probado con tests/test_validador.py: el JSON 4x4 da 0 errores,
        cada archivo de scenarios/invalidos da exactamente 1 error
    """
    mapa = _exigir_objeto(datos, "mapa", "mapa", errores)
    if mapa is None:
        return None
    valores: dict[str, int] = {}
    for campo in ("filas", "columnas"):
        ruta = f"mapa.{campo}"
        if campo not in mapa:
            errores.append(f"{ruta}: falta el campo obligatorio")
        elif not _es_entero_positivo(mapa[campo]):
            errores.append(f"{ruta}: debe ser un entero positivo, no {mapa[campo]!r}")
        else:
            valores[campo] = mapa[campo]
    if len(valores) == 2:
        return (valores["filas"], valores["columnas"])
    return None


def _costo_valido(costo: object) -> bool:
    """True si costo es un número finito mayor que cero (los booleanos no valen)."""
    if not _es_numero(costo) or costo <= 0:
        return False
    return not (isinstance(costo, float) and not math.isfinite(costo))


def _validar_tipos_terreno(datos: dict, errores: list[str]) -> Catalogo | None:
    """
    Purpose: Validar el catálogo (R3) y que haya al menos un terreno transitable.
    Preconditions: datos es un dict.
    Postconditions: Devuelve nombre -> transitable (None si la definición está rota) o None
        si el catálogo falta o no es objeto. Costo: número finito > 0 en los transitables.
    Complexity: tiempo O(T), espacio O(T) con T = tipos de terreno
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation:  se leyó el flujo completo y el
        orden de las fases. Probado con tests/test_validador.py: el JSON 4x4 da 0 errores,
        cada archivo de scenarios/invalidos da exactamente 1 error
    """
    catalogo = _exigir_objeto(datos, "tipos_terreno", "tipos_terreno", errores)
    if catalogo is None:
        return None
    tipos: Catalogo = {}
    for nombre, definicion in catalogo.items():
        ruta = f"tipos_terreno['{nombre}']"
        tipos[nombre] = None
        if not isinstance(definicion, dict):
            errores.append(f"{ruta}: debe ser un objeto")
            continue
        transitable = definicion.get("transitable")
        if not isinstance(transitable, bool):
            errores.append(f"{ruta}: 'transitable' es obligatorio y debe ser true o false")
            continue
        tipos[nombre] = transitable
        if not transitable:
            continue
        if "costo" not in definicion:
            errores.append(f"{ruta}: falta el campo 'costo' (obligatorio si es transitable)")
        elif not _costo_valido(definicion["costo"]):
            errores.append(f"{ruta}: el costo debe ser un número positivo, no {definicion['costo']!r}")
    if not any(valor is not False for valor in tipos.values()):
        errores.append("tipos_terreno: debe haber al menos un terreno transitable")
    return tipos


def _validar_terreno(
    datos: dict, dimensiones: Dimensiones | None, tipos: Catalogo | None, errores: list[str]
) -> list | None:
    """
    Purpose: Validar la matriz terreno: forma (R1) y nombres existentes en el catálogo (R2).
    Preconditions: dimensiones y tipos vienen de _validar_mapa y _validar_tipos_terreno.
    Postconditions: Devuelve la matriz tal cual (aunque sea irregular) o None si no es lista.
        Sin dimensiones no compara tamaños; sin catálogo no compara nombres.
    Complexity: tiempo O(F*C), espacio O(1) adicional con F filas, C columnas
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation:  se leyó el flujo completo y el
        orden de las fases. Probado con tests/test_validador.py: el JSON 4x4 da 0 errores,
        cada archivo de scenarios/invalidos da exactamente 1 error
    """
    if "terreno" not in datos:
        errores.append("terreno: falta el campo obligatorio")
        return None
    matriz = datos["terreno"]
    if not isinstance(matriz, list):
        errores.append("terreno: debe ser una lista de filas")
        return None
    if dimensiones is not None and len(matriz) != dimensiones[0]:
        errores.append(f"terreno: tiene {len(matriz)} filas pero mapa.filas es {dimensiones[0]}")
    for i, fila in enumerate(matriz):
        if not isinstance(fila, list):
            errores.append(f"terreno[{i}]: debe ser una lista de nombres de terreno")
            continue
        if dimensiones is not None and len(fila) != dimensiones[1]:
            errores.append(
                f"terreno[{i}]: tiene {len(fila)} columnas pero mapa.columnas es {dimensiones[1]}"
            )
        for j, celda in enumerate(fila):
            if not isinstance(celda, str):
                errores.append(
                    f"terreno[{i}][{j}]: debe ser un texto con el nombre del terreno, no {celda!r}"
                )
            elif tipos is not None and celda not in tipos:
                errores.append(
                    f"terreno[{i}][{j}]: el terreno '{celda}' no existe en tipos_terreno"
                )
    return matriz


def _validar_bases(datos: dict, ctx: _Contexto, errores: list[str]) -> None:
    """
    Purpose: Validar bases.A y bases.B (R4 y regla propia: sobre terreno transitable).
    Preconditions: ctx trae lo ya validado del mapa.
    Postconditions: Agrega errores; las claves se comparan sin distinguir mayúsculas
        (construir_datos las pasa a mayúscula).
    Complexity: tiempo O(B), espacio O(B) con B = claves de bases
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation:  se leyó el flujo completo y el
        orden de las fases. Probado con tests/test_validador.py: el JSON 4x4 da 0 errores,
        cada archivo de scenarios/invalidos da exactamente 1 error
    """
    bases = _exigir_objeto(datos, "bases", "bases", errores)
    if bases is None:
        return
    normalizadas = {str(clave).upper(): valor for clave, valor in bases.items()}
    for bando in BANDOS:
        ruta = f"bases.{bando}"
        if bando not in normalizadas:
            errores.append(f"{ruta}: falta el campo obligatorio")
            continue
        pos = _leer_posicion(normalizadas[bando], ruta, errores)
        if pos is not None:
            _revisar_celda(pos, ruta, ctx, errores, exigir_transitable=True)


def _validar_unidades(datos: dict, ctx: _Contexto, errores: list[str]) -> set[str] | None:
    """
    Purpose: Validar las unidades: estructura, R4, R5, R6 y R7.
    Preconditions: ctx trae lo ya validado del mapa.
    Postconditions: Devuelve el conjunto de ids, o None si la lista está rota o algún id es
        inválido (así R9 y unidad_inicio no generan errores en cascada). Cada id repetido se
        reporta una sola vez, al final, en orden de primera repetición.
    Complexity: tiempo O(U), espacio O(U) con U = unidades
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation:  se leyó el flujo completo y el
        orden de las fases. Probado con tests/test_validador.py: el JSON 4x4 da 0 errores,
        cada archivo de scenarios/invalidos da exactamente 1 error
    """
    if "unidades" not in datos:
        errores.append("unidades: falta el campo obligatorio")
        return None
    lista = datos["unidades"]
    if not isinstance(lista, list):
        errores.append("unidades: debe ser una lista")
        return None
    ids: set[str] = set()
    repetidos: list[str] = []
    ids_completos = True
    for i, unidad in enumerate(lista):
        if not isinstance(unidad, dict):
            errores.append(f"unidades[{i}]: debe ser un objeto")
            ids_completos = False
            continue
        id_unidad = _exigir_texto(unidad, "id", f"unidades[{i}]", errores)
        if id_unidad is None:
            ids_completos = False
            ruta = f"unidades[{i}]"
        else:
            ruta = f"unidades[{i}] ({id_unidad})"
            if id_unidad not in ids:
                ids.add(id_unidad)
            elif id_unidad not in repetidos:
                repetidos.append(id_unidad)
        bando = _exigir_texto(unidad, "bando", ruta, errores)
        if bando is not None and bando.upper() not in BANDOS:
            errores.append(f"{ruta}: el bando '{bando}' no es válido (debe ser A o B)")
        _exigir_texto(unidad, "tipo", ruta, errores)
        pos = _leer_posicion(unidad, ruta, errores)
        if pos is not None:
            _revisar_celda(pos, ruta, ctx, errores, exigir_transitable=True)
    for id_unidad in repetidos:
        errores.append(f"unidades: el id '{id_unidad}' está repetido")
    return ids if ids_completos else None


def _validar_juego(datos: dict, ids: set[str] | None, errores: list[str]) -> None:
    """
    Purpose: Validar el bloque opcional juego: R9 y los enteros positivos propios.
    Preconditions: ids es el conjunto de ids de unidades o None si no se pudo determinar.
    Postconditions: Agrega errores. limite_turnos presente (aunque sea null) debe ser entero
        positivo; profundidad_maxima_minimax acepta null.
    Complexity: tiempo O(1), espacio O(1)
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: se leyó el flujo completo y el
        orden de las fases. Probado con tests/test_validador.py: el JSON 4x4 da 0 errores,
        cada archivo de scenarios/invalidos da exactamente 1 error
    """
    if "juego" not in datos:
        return
    juego = datos["juego"]
    if not isinstance(juego, dict):
        errores.append("juego: debe ser un objeto")
        return
    portador = juego.get("portador_recurso")
    if portador is not None:
        if not isinstance(portador, str):
            errores.append(
                f"juego.portador_recurso: debe ser el id de una unidad o null, no {portador!r}"
            )
        elif ids is not None and portador not in ids:
            errores.append(f"juego.portador_recurso: la unidad '{portador}' no existe")
    profundidad = juego.get("profundidad_maxima_minimax")
    if profundidad is not None and not _es_entero_positivo(profundidad):
        errores.append(
            f"juego.profundidad_maxima_minimax: debe ser un entero positivo, no {profundidad!r}"
        )
    if "limite_turnos" in juego and not _es_entero_positivo(juego["limite_turnos"]):
        errores.append(
            f"juego.limite_turnos: debe ser un entero positivo, no {juego['limite_turnos']!r}"
        )


def _validar_prueba(datos: dict, ids: set[str] | None, ctx: _Contexto, errores: list[str]) -> None:
    """
    Purpose: Validar el bloque opcional prueba (reglas propias del equipo).
    Preconditions: ids es el conjunto de ids de unidades o None si no se pudo determinar.
    Postconditions: Agrega errores. objetivo y mision se validan siempre que estén presentes
        (construir_datos los convierte en cualquier modo); unidad_inicio y la exigencia de
        objetivo o mision solo aplican al modo "busqueda". null cuenta como ausente.
    Complexity: tiempo O(1), espacio O(1)
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: se leyó el flujo completo y el
        orden de las fases. Probado con tests/test_validador.py: el JSON 4x4 da 0 errores,
        cada archivo de scenarios/invalidos da exactamente 1 error
    """
    if "prueba" not in datos:
        return
    prueba = datos["prueba"]
    if not isinstance(prueba, dict):
        errores.append("prueba: debe ser un objeto")
        return
    modo = _exigir_texto(prueba, "modo", "prueba", errores)
    if modo is not None and modo not in MODOS_PRUEBA:
        errores.append(
            f"prueba.modo: el valor '{modo}' no es válido (debe ser busqueda, partida o adversarial)"
        )
    objetivo = prueba.get("objetivo")
    mision = prueba.get("mision")
    if objetivo is not None:
        pos = _leer_posicion(objetivo, "prueba.objetivo", errores)
        if pos is not None:
            _revisar_celda(pos, "prueba.objetivo", ctx, errores, exigir_transitable=False)
    if mision is not None and mision not in MISIONES:
        errores.append(
            f"prueba.mision: el valor {mision!r} no es válido (debe ser 'llevar_recurso')"
        )
    if modo != "busqueda":
        return
    inicio = prueba.get("unidad_inicio")
    if inicio is None:
        errores.append("prueba.unidad_inicio: es obligatorio en modo 'busqueda'")
    elif not isinstance(inicio, str):
        errores.append(f"prueba.unidad_inicio: debe ser el id de una unidad, no {inicio!r}")
    elif ids is not None and inicio not in ids:
        errores.append(f"prueba.unidad_inicio: la unidad '{inicio}' no existe")
    if objetivo is None and mision is None:
        errores.append("prueba: en modo 'busqueda' debe venir 'objetivo' o 'mision'")


def validar(datos: dict) -> list[str]:
    """
    Purpose: Revisar el dict de un escenario y devolver TODOS los errores encontrados.
    Preconditions: datos es lo que devuelve json.loads (puede estar mal formado).
    Postconditions: Devuelve la lista de errores (vacía si es válido) en orden determinista;
        nunca lanza por datos mal formados y no modifica datos. Si una parte de la
        estructura está rota se reporta y se omiten las reglas que dependen de ella.
    Complexity: tiempo O(F*C + U + T), espacio O(F*C + U + E) con E = errores
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se hizo el seguimiento de cada uno de los metodos de validación, comprobando sus resultados
    """
    if not isinstance(datos, dict):
        return ["El escenario debe ser un objeto JSON"]
    errores: list[str] = []
    _exigir_texto(datos, "version", "version", errores)
    dimensiones = _validar_mapa(datos, errores)
    tipos = _validar_tipos_terreno(datos, errores)
    matriz = _validar_terreno(datos, dimensiones, tipos, errores)
    ctx = _Contexto(dimensiones=dimensiones, matriz=matriz, tipos=tipos)
    _validar_bases(datos, ctx, errores)
    if "recurso" not in datos:
        errores.append("recurso: falta el campo obligatorio")
    else:
        pos = _leer_posicion(datos["recurso"], "recurso", errores)
        if pos is not None:
            _revisar_celda(pos, "recurso", ctx, errores, exigir_transitable=True)
    ids = _validar_unidades(datos, ctx, errores)
    turno = _exigir_texto(datos, "turno", "turno", errores)
    if turno is not None and turno.upper() not in BANDOS:
        errores.append(f"turno: el valor '{turno}' no es válido (debe ser A o B)")
    _validar_juego(datos, ids, errores)
    _validar_prueba(datos, ids, ctx, errores)
    return errores
