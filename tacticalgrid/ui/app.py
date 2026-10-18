"""Ventana Tkinter de TacticalGrid: carga escenarios y ejecuta los algoritmos IA contra IA."""

import colorsys
import hashlib
import tkinter as tk
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from tacticalgrid.carga.cargador import DatosEscenario, ErrorCarga, cargar_escenario
from tacticalgrid.config import DESPLAZAMIENTOS
from tacticalgrid.core.escenario import Posicion
from tacticalgrid.core.juego import EstadoJuego, ReglasJuego
from tacticalgrid.ui.servicio import (
    ALGORITMOS_BUSQUEDA,
    ALGORITMOS_DECISION,
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

MODOS = {"busqueda": "Búsqueda", "adversarial": "Adversarial", "partida": "Partida"}
FORMATEADORES_JSON = {
    "busqueda": formatear_busqueda,
    "adversarial": formatear_decision,
    "partida": formatear_partida,
}
ALGORITMOS_POR_MODO = {
    "busqueda": ALGORITMOS_BUSQUEDA,
    "adversarial": ALGORITMOS_DECISION,
    "partida": ALGORITMOS_DECISION,
}
PALETA_TERRENOS = {
    "camino": "#e0cf9f",
    "pasto": "#9ccc65",
    "bosque": "#388e3c",
    "pantano": "#7b8d5a",
    "agua": "#64b5f6",
    "arena": "#f5e1a4",
    "montaña": "#a1887f",
    "montana": "#a1887f",
}
COLOR_NO_TRANSITABLE = "#333333"
COLOR_BANDO = {"A": "#1e63c9", "B": "#d32f2f"}
COLOR_PORTADOR = "#ffc107"
COLOR_RESALTADO = "#ff6f00"
COLOR_CAMINO_IDA = "#6a1b9a"
COLOR_CAMINO_VUELTA = "#F28C28"
COLOR_EXPANDIDO_SIN = "#29b6f6"
COLOR_EXPANDIDO_CON = "#F28C28"
LADO_MAXIMO_PX = 600
RAIZ_ESCENARIOS = Path(__file__).resolve().parents[2] / "scenarios"


def color_terreno(nombre: str, transitable: bool) -> str:
    """
    Purpose: Color de relleno de una celda según su tipo de terreno.
    Preconditions: Ninguna.
    Postconditions: COLOR_NO_TRANSITABLE si no es transitable; el de PALETA_TERRENOS si el
        nombre es conocido; si no, un color claro derivado del nombre con md5 (estable entre
        ejecuciones, a diferencia de hash()).
    Complexity: tiempo O(len(nombre)), espacio O(1)
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: Se valida y se hace seguimiento
    """
    if not transitable:
        return COLOR_NO_TRANSITABLE
    if nombre in PALETA_TERRENOS:
        return PALETA_TERRENOS[nombre]
    tono = int(hashlib.md5(nombre.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF
    rojo, verde, azul = colorsys.hls_to_rgb(tono, 0.7, 0.5)
    return f"#{int(rojo * 255):02x}{int(verde * 255):02x}{int(azul * 255):02x}"


def _entero(variable: tk.StringVar, nombre: str) -> int:
    """Valor entero de un spinbox; ValueError con un mensaje legible si no lo es."""
    texto = variable.get().strip()
    try:
        return int(texto)
    except ValueError:
        raise ValueError(f"{nombre} debe ser un número entero, no {texto!r}") from None


class AplicacionTacticalGrid:
    """Ventana principal: mapa, panel de control, resultados acumulados y navegación."""

    def __init__(self, raiz: tk.Tk) -> None:
        """
        Purpose: Construir todos los widgets de la ventana sin escenario cargado.
        Preconditions: raiz es la ventana Tk principal.
        Postconditions: Ventana lista; Ejecutar y Verificar avisan mientras no haya escenario.
        Complexity: tiempo O(1), espacio O(1)
        AI usage: Yes
        AI intervention: Código generado por IA a partir de la especificación del equipo.
        Student validation: Se valida y se hace seguimiento
        """
        self.raiz = raiz
        self.datos: DatosEscenario | None = None
        self.estado: EstadoJuego | None = None
        self.ida: list[Posicion] = []
        self.vuelta: list[Posicion] = []
        self.expandidos: list[tuple[int, int, bool]] = []  # (fila, columna, lleva_recurso)
        self.meta: Posicion | None = None
        self.resaltado: tuple[str, Posicion | None] | None = None
        self.partida = None
        self.indice = 0
        self.ultimo = None  
        self.ejecuciones = 0
        self.celda = 40

        raiz.title("TacticalGrid")
        raiz.columnconfigure(0, weight=1)
        raiz.rowconfigure(1, weight=1)
        self._crear_mapa()
        self._crear_controles()
        self._crear_resultados()
        self._cambiar_modo()
        self._dibujar()

    # ------------------------------------------------------------------ construcción

    def _crear_mapa(self) -> None:
        marco = ttk.Frame(self.raiz, padding=8)
        marco.grid(row=0, column=0, sticky="nw")
        self.etiqueta_archivo = ttk.Label(marco, text="Sin escenario cargado")
        self.etiqueta_archivo.grid(row=0, column=0, sticky="w")
        self.lienzo = tk.Canvas(marco, width=320, height=320, bg="white", highlightthickness=0)
        self.lienzo.grid(row=1, column=0, sticky="nw", pady=4)
        self.leyenda_camino = ttk.Frame(marco)
        self.leyenda_camino.grid(row=2, column=0, sticky="w")
        fuente = ("", 9, "bold")
        self.etiquetas_leyenda = {
            "ida": tk.Label(
                self.leyenda_camino, text="▬ ida (sin recurso)", fg=COLOR_CAMINO_IDA, font=fuente
            ),
            "vuelta": tk.Label(
                self.leyenda_camino, text="▬ vuelta (con recurso)", fg=COLOR_CAMINO_VUELTA,
                font=fuente,
            ),
            "exp_sin": tk.Label(
                self.leyenda_camino, text="• expandido sin recurso", fg=COLOR_EXPANDIDO_SIN,
                font=fuente,
            ),
            "exp_con": tk.Label(
                self.leyenda_camino, text="• expandido con recurso", fg=COLOR_EXPANDIDO_CON,
                font=fuente,
            ),
        }
        posiciones = {"ida": (0, 0), "vuelta": (0, 1), "exp_sin": (1, 0), "exp_con": (1, 1)}
        for clave, etiqueta in self.etiquetas_leyenda.items():
            fila, columna = posiciones[clave]
            etiqueta.grid(row=fila, column=columna, padx=(0, 12), sticky="w")
        self.leyenda_camino.grid_remove()
        self.leyenda = ttk.Frame(marco)
        self.leyenda.grid(row=3, column=0, sticky="w")
        self.etiqueta_estado = ttk.Label(marco, text="")
        self.etiqueta_estado.grid(row=4, column=0, sticky="w", pady=(4, 0))

        navegacion = ttk.Frame(marco)
        navegacion.grid(row=5, column=0, sticky="w", pady=(4, 0))
        self.boton_anterior = ttk.Button(
            navegacion, text="◀ Anterior", command=lambda: self._navegar(-1)
        )
        self.boton_anterior.grid(row=0, column=0)
        self.boton_siguiente = ttk.Button(
            navegacion, text="Siguiente ▶", command=lambda: self._navegar(1)
        )
        self.boton_siguiente.grid(row=0, column=1, padx=4)
        self.etiqueta_turno = ttk.Label(navegacion, text="")
        self.etiqueta_turno.grid(row=0, column=2, padx=4)

    def _crear_controles(self) -> None:
        panel = ttk.Frame(self.raiz, padding=8)
        panel.grid(row=0, column=1, sticky="ne")

        ttk.Button(panel, text="Cargar escenario", command=self._cargar).grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8)
        )

        ttk.Label(panel, text="Modo").grid(row=1, column=0, sticky="w")
        self.var_modo = tk.StringVar(value="busqueda")
        modos = ttk.Frame(panel)
        modos.grid(row=1, column=1, sticky="w")
        for i, (valor, texto) in enumerate(MODOS.items()):
            ttk.Radiobutton(
                modos, text=texto, value=valor, variable=self.var_modo, command=self._cambiar_modo
            ).grid(row=0, column=i, sticky="w")

        ttk.Label(panel, text="Algoritmo").grid(row=2, column=0, sticky="w")
        self.var_algoritmo = tk.StringVar()
        self.combo_algoritmo = ttk.Combobox(
            panel, textvariable=self.var_algoritmo, state="readonly", width=12
        )
        self.combo_algoritmo.grid(row=2, column=1, sticky="w", pady=2)
        self.combo_algoritmo.bind("<<ComboboxSelected>>", lambda _: self._actualizar_controles())

        ttk.Label(panel, text="Heurística").grid(row=3, column=0, sticky="w")
        self.var_heuristica = tk.StringVar(value="h2")
        self.combo_heuristica = ttk.Combobox(
            panel, textvariable=self.var_heuristica, values=("h1", "h2"), width=12
        )
        self.combo_heuristica.grid(row=3, column=1, sticky="w", pady=2)

        ttk.Label(panel, text="k (Beam)").grid(row=4, column=0, sticky="w")
        self.var_k = tk.StringVar(value="4")
        self.spin_k = ttk.Spinbox(panel, from_=1, to=50, textvariable=self.var_k, width=6)
        self.spin_k.grid(row=4, column=1, sticky="w", pady=2)

        ttk.Label(panel, text="Profundidad").grid(row=5, column=0, sticky="w")
        self.var_profundidad = tk.StringVar(value="4")
        self.spin_profundidad = ttk.Spinbox(
            panel, from_=1, to=20, textvariable=self.var_profundidad, width=6
        )
        self.spin_profundidad.grid(row=5, column=1, sticky="w", pady=2)

        ttk.Label(panel, text="Orden de direcciones").grid(row=6, column=0, sticky="w")
        self.combo_orden = ttk.Combobox(
            panel, values=[", ".join(o) for o in ORDENES_DISPONIBLES], state="readonly", width=32
        )
        self.combo_orden.current(0)
        self.combo_orden.grid(row=6, column=1, sticky="w", pady=2)

        botones = ttk.Frame(panel)
        botones.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(botones, text="Ejecutar", command=self._ejecutar).grid(row=0, column=0)
        ttk.Button(botones, text="Verificar", command=self._verificar).grid(
            row=0, column=1, padx=4
        )

    def _crear_resultados(self) -> None:
        marco = ttk.Frame(self.raiz, padding=8)
        marco.grid(row=1, column=0, columnspan=2, sticky="nsew")
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(1, weight=1)
        cabecera = ttk.Frame(marco)
        cabecera.grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(cabecera, text="Resultados").pack(side="left")
        ttk.Button(cabecera, text="Limpiar resultados", command=self._limpiar_resultados).pack(
            side="right"
        )
        ttk.Button(cabecera, text="Copiar JSON", command=self._copiar_json).pack(
            side="right", padx=4
        )
        self.etiqueta_aviso = ttk.Label(cabecera, text="")
        self.etiqueta_aviso.pack(side="right", padx=4)
        self.texto = tk.Text(
            marco, height=16, wrap="none", state="disabled", font=("Consolas", 10)
        )
        self.texto.grid(row=1, column=0, sticky="nsew")
        barra = ttk.Scrollbar(marco, orient="vertical", command=self.texto.yview)
        barra.grid(row=1, column=1, sticky="ns")
        self.texto.configure(yscrollcommand=barra.set)

    # ------------------------------------------------------------------ controles

    def _cambiar_modo(self) -> None:
        """Ajusta la lista de algoritmos al modo y borra lo dibujado de la ejecución previa."""
        valores = ALGORITMOS_POR_MODO[self.var_modo.get()]
        self.combo_algoritmo.configure(values=valores)
        if self.var_algoritmo.get() not in valores:
            self.var_algoritmo.set(valores[0])
        self._limpiar_vista()
        self._actualizar_controles()
        self._dibujar()

    def _actualizar_controles(self) -> None:
        """Habilita heurística (A*/Beam), k (Beam) y profundidad (adversarial/partida)."""
        modo, algoritmo = self.var_modo.get(), self.var_algoritmo.get()
        informada = modo == "busqueda" and algoritmo in ("A*", "Beam")
        self.combo_heuristica.configure(state="readonly" if informada else "disabled")
        self.spin_k.configure(state="normal" if algoritmo == "Beam" else "disabled")
        self.spin_profundidad.configure(state="disabled" if modo == "busqueda" else "normal")
        hay_partida = self.partida is not None
        self.boton_anterior.configure(state="normal" if hay_partida else "disabled")
        self.boton_siguiente.configure(state="normal" if hay_partida else "disabled")

    def _limpiar_vista(self) -> None:
        """Quita camino, resaltado y partida, y vuelve a mostrar el estado inicial."""
        self.ida, self.vuelta, self.expandidos = [], [], []
        self.meta, self.resaltado = None, None
        self.partida, self.indice = None, 0
        self.etiqueta_turno.configure(text="")
        self.estado = ReglasJuego(self.datos).estado_inicial() if self.datos else None

    @contextmanager
    def _cursor_espera(self) -> Iterator[None]:
        self.raiz.configure(cursor="watch")
        self.raiz.update_idletasks()
        try:
            yield
        finally:
            self.raiz.configure(cursor="")

    # ------------------------------------------------------------------ acciones

    def _cargar(self) -> None:
        """Carga un JSON; si falla, muestra todos los errores y conserva el escenario anterior."""
        inicial = RAIZ_ESCENARIOS if RAIZ_ESCENARIOS.is_dir() else Path.cwd()
        ruta = filedialog.askopenfilename(
            title="Cargar escenario",
            initialdir=inicial,
            filetypes=[("Escenarios JSON", "*.json"), ("Todos los archivos", "*.*")],
        )
        if not ruta:
            return
        try:
            datos = cargar_escenario(ruta)
        except ErrorCarga as error:
            messagebox.showerror("No se pudo cargar el escenario", str(error))
            return
        self.datos = datos
        self.ultimo = None
        self.etiqueta_archivo.configure(text=f"Escenario: {Path(ruta).name}")
        self.var_profundidad.set(str(profundidad_inicial(datos)))
        if datos.prueba is not None and datos.prueba.modo in MODOS:
            self.var_modo.set(datos.prueba.modo)
        self._construir_leyenda()
        self._cambiar_modo()

    def _ejecutar(self) -> None:
        """Ejecuta el algoritmo elegido y añade su resultado al panel de texto."""
        if self.datos is None:
            messagebox.showwarning("Sin escenario", "Primero carga un escenario.")
            return
        modo, algoritmo = self.var_modo.get(), self.var_algoritmo.get()
        orden = ORDENES_DISPONIBLES[self.combo_orden.current()]
        heuristica = self.var_heuristica.get()
        numero = self.ejecuciones + 1
        try:
            with self._cursor_espera():
                if modo == "busqueda":
                    k = _entero(self.var_k, "k") if algoritmo == "Beam" else 4
                    obtenido = ejecutar_busqueda(self.datos, algoritmo, heuristica, k, orden)
                    texto = resumir_busqueda(obtenido, orden, numero)
                else:
                    profundidad = _entero(self.var_profundidad, "La profundidad")
                    if modo == "adversarial":
                        obtenido = ejecutar_decision(self.datos, algoritmo, profundidad, orden)
                        texto = resumir_decision(obtenido, orden, profundidad, numero)
                    else:
                        obtenido = ejecutar_partida(self.datos, algoritmo, profundidad, orden)
                        texto = resumir_partida(obtenido, orden, profundidad, algoritmo, numero)
        except ValueError as error:
            messagebox.showerror("Error de ejecución", str(error))
            return

        self._limpiar_vista()
        self.ejecuciones = numero
        self.ultimo = (obtenido, orden, numero, modo)
        if modo == "busqueda":
            self._mostrar_busqueda(obtenido)
        elif modo == "adversarial":
            self._mostrar_decision(obtenido)
        else:
            self.partida = obtenido
            self._mostrar_turno()
        self._agregar_texto(texto)
        self._actualizar_controles()
        self._dibujar()

    def _mostrar_busqueda(self, resultado) -> None:
        prueba = self.datos.prueba
        self.expandidos = [(e.fila, e.columna, e.lleva_recurso) for e in resultado.orden_expansion]
        if prueba.mision == "llevar_recurso":
            self.ida, self.vuelta = dividir_camino(resultado)
            unidad = next(u for u in self.datos.unidades if u.id == prueba.unidad_inicio)
            self.meta = self.datos.escenario.base_de(unidad.bando)
        else:
            self.ida = [e.posicion for e in resultado.estados]  # prueba normal: un solo tramo
            self.meta = prueba.objetivo

    def _mostrar_decision(self, decision) -> None:
        jugada = decision.jugada
        if jugada.es_pasar:
            self.etiqueta_turno.configure(text="Acción recomendada: pasar")
            return
        fila, columna = self.estado.posicion_de(jugada.unidad)
        d_fila, d_columna = DESPLAZAMIENTOS[jugada.direccion]
        self.resaltado = (jugada.unidad, (fila + d_fila, columna + d_columna))
        self.etiqueta_turno.configure(text=f"Acción recomendada: {jugada}")

    def _mostrar_turno(self) -> None:
        partida, i = self.partida, self.indice
        self.estado = partida.estados[i]
        jugada = "inicio" if i == 0 else str(partida.jugadas[i - 1])
        texto = f"turno {i} / {partida.turnos} · jugada: {jugada}"
        if i == partida.turnos:
            final = f"gana {partida.ganador}" if partida.ganador else "empate por límite"
            texto += f" · {final}"
        self.etiqueta_turno.configure(text=texto)

    def _navegar(self, paso: int) -> None:
        if self.partida is None:
            return
        self.indice = max(0, min(self.partida.turnos, self.indice + paso))
        self._mostrar_turno()
        self._dibujar()

    def _verificar(self) -> None:
        """Verifica el último resultado con el orden con que se obtuvo y anota el reporte."""
        if self.datos is None or self.ultimo is None:
            messagebox.showinfo("Verificar", "No hay ningún resultado para verificar.")
            return
        obtenido, orden, _, _ = self.ultimo
        try:
            with self._cursor_espera():
                reporte = verificar(self.datos, obtenido, orden)
        except ValueError as error:
            messagebox.showerror("Error de verificación", str(error))
            return
        self._agregar_texto(resumir_verificacion(reporte), separar=False)

    def _copiar_json(self) -> None:
        """Copia al portapapeles el JSON de la última ejecución y lo avisa brevemente."""
        if self.ultimo is None:
            messagebox.showinfo("Copiar JSON", "No hay ninguna ejecución para copiar.")
            return
        obtenido, orden, _, modo = self.ultimo
        self.raiz.clipboard_clear()
        self.raiz.clipboard_append(FORMATEADORES_JSON[modo](obtenido, orden))
        self.etiqueta_aviso.configure(text="JSON copiado")
        self.raiz.after(2000, lambda: self.etiqueta_aviso.configure(text=""))

    def _agregar_texto(self, contenido: str, separar: bool = True) -> None:
        self.texto.configure(state="normal")
        if self.texto.get("1.0", "end-1c"):
            self.texto.insert("end", "\n\n" if separar else "\n")
        self.texto.insert("end", contenido)
        self.texto.configure(state="disabled")
        self.texto.see("end")

    def _limpiar_resultados(self) -> None:
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        self.texto.configure(state="disabled")
        self.ejecuciones = 0
        self.expandidos = []
        self._dibujar()

    # ------------------------------------------------------------------ dibujo

    def _construir_leyenda(self) -> None:
        for widget in self.leyenda.winfo_children():
            widget.destroy()
        for i, tipo in enumerate(self.datos.escenario.tipos_terreno.values()):
            color = color_terreno(tipo.nombre, tipo.transitable)
            costo = "no transitable" if tipo.costo is None else f"costo {tipo.costo:g}"
            tk.Label(self.leyenda, bg=color, width=2, relief="solid", bd=1).grid(
                row=i // 3, column=2 * (i % 3), padx=(0, 2), pady=1
            )
            ttk.Label(self.leyenda, text=f"{tipo.nombre} ({costo})").grid(
                row=i // 3, column=2 * (i % 3) + 1, sticky="w", padx=(0, 10)
            )

    def _centro(self, pos: Posicion, desplazamiento: float = 0) -> tuple[float, float]:
        """Centro de la celda, corrido `desplazamiento` píxeles en x e y."""
        return (
            (pos[1] + 0.5) * self.celda + desplazamiento,
            (pos[0] + 0.5) * self.celda + desplazamiento,
        )

    def _trazar(self, tramo: list[Posicion], color: str, desplazamiento: float) -> None:
        """Polilínea con flecha al final por el centro de las celdas del tramo, desplazada."""
        if len(tramo) < 2:
            return
        puntos = [c for pos in tramo for c in self._centro(pos, desplazamiento)]
        self.lienzo.create_line(*puntos, fill=color, width=3, arrow=tk.LAST, capstyle="round")

    def _dibujar_expandidos(self) -> None:
        """Punto azul (arriba a la izquierda) si se expandió sin recurso; naranja (arriba a la
        derecha) si con recurso. Se dibuja antes que el camino y las unidades."""
        radio = max(2, self.celda * 0.07)
        margen = self.celda * 0.15
        for fila, columna, lleva in set(self.expandidos):
            x = columna * self.celda + (self.celda - margen if lleva else margen)
            y = fila * self.celda + margen
            self.lienzo.create_oval(
                x - radio, y - radio, x + radio, y + radio,
                fill=COLOR_EXPANDIDO_CON if lleva else COLOR_EXPANDIDO_SIN,
                outline="#37474f", width=1,
            )

    def _actualizar_leyenda_camino(self, dos_tramos: bool) -> None:
        """Muestra solo las entradas de leyenda que aparecen en el mapa."""
        visibles = {
            "ida": dos_tramos,
            "vuelta": dos_tramos,
            "exp_sin": any(not lleva for _, _, lleva in self.expandidos),
            "exp_con": any(lleva for _, _, lleva in self.expandidos),
        }
        for clave, etiqueta in self.etiquetas_leyenda.items():
            if visibles[clave]:
                etiqueta.grid()
            else:
                etiqueta.grid_remove()
        if any(visibles.values()):
            self.leyenda_camino.grid()
        else:
            self.leyenda_camino.grid_remove()

    def _rectangulo(self, pos: Posicion, margen: float = 0, **opciones) -> None:
        x0, y0 = pos[1] * self.celda + margen, pos[0] * self.celda + margen
        x1, y1 = x0 + self.celda - 2 * margen, y0 + self.celda - 2 * margen
        self.lienzo.create_rectangle(x0, y0, x1, y1, **opciones)

    def _dibujar(self) -> None:
        """Redibuja el mapa completo con el estado mostrado y las marcas de la ejecución."""
        lienzo = self.lienzo
        lienzo.delete("all")
        if self.datos is None:
            lienzo.configure(width=320, height=320)
            lienzo.create_text(160, 160, text="Carga un escenario para empezar", fill="#666")
            self.etiqueta_estado.configure(text="")
            self.leyenda_camino.grid_remove()
            return
        escenario = self.datos.escenario
        self.celda = max(16, min(48, LADO_MAXIMO_PX // max(escenario.filas, escenario.columnas)))
        lienzo.configure(width=escenario.columnas * self.celda, height=escenario.filas * self.celda)

        for fila in range(escenario.filas):
            for columna in range(escenario.columnas):
                tipo = escenario.tipo_en((fila, columna))
                color = color_terreno(tipo.nombre, tipo.transitable)
                self._rectangulo((fila, columna), fill=color, outline="#777")

        fuente_chica = ("TkDefaultFont", max(6, self.celda // 6))
        for bando, base in escenario.bases.items():
            self._rectangulo(base, margen=2, outline=COLOR_BANDO.get(bando, "black"), width=4)
            x, y = self._centro(base)
            lienzo.create_text(
                x, y - self.celda * 0.32, text=f"Base {bando}", font=fuente_chica,
                fill=COLOR_BANDO.get(bando, "black"),
            )

        self._dibujar_expandidos()
        if self.meta is not None:
            self._rectangulo(self.meta, margen=5, outline="#6a1b9a", width=3, dash=(4, 2))
        dos_tramos = bool(self.ida) and bool(self.vuelta)
        if dos_tramos:
            d = self.celda / 8
            self._trazar(self.ida, COLOR_CAMINO_IDA, -d)
            self._trazar(self.vuelta, COLOR_CAMINO_VUELTA, d)
            x, y = self._centro(self.ida[-1])
            r = self.celda * 0.09
            lienzo.create_oval(
                x - r, y - r, x + r, y + r, fill=COLOR_CAMINO_VUELTA, outline=COLOR_CAMINO_IDA,
                width=2,
            )
        elif self.vuelta:  
            self._trazar(self.vuelta, COLOR_CAMINO_VUELTA, 0)
        else:
            self._trazar(self.ida, COLOR_CAMINO_IDA, 0)
        self._actualizar_leyenda_camino(dos_tramos)
        if self.resaltado is not None and self.resaltado[1] is not None:
            self._rectangulo(self.resaltado[1], margen=3, outline=COLOR_RESALTADO, width=4)

        estado = self.estado
        if estado.recurso is not None:
            x, y = self._centro(estado.recurso)
            r = self.celda * 0.22
            lienzo.create_polygon(
                x, y - r, x + r, y, x, y + r, x - r, y, fill=COLOR_PORTADOR, outline="#8d6e00"
            )

        reglas = ReglasJuego(self.datos)
        vistas: dict[Posicion, int] = {}
        radio = self.celda * 0.3
        for unidad, pos in estado.posiciones:
            repetida = vistas.get(pos, 0)
            vistas[pos] = repetida + 1
            x, y = self._centro(pos)
            x, y = x + repetida * radio * 0.6, y + repetida * radio * 0.6
            bando = reglas.bando_de(unidad)
            if self.resaltado is not None and self.resaltado[0] == unidad:
                lienzo.create_oval(
                    x - radio - 5, y - radio - 5, x + radio + 5, y + radio + 5,
                    outline=COLOR_RESALTADO, width=3,
                )
            es_portador = estado.portador == unidad
            lienzo.create_oval(
                x - radio, y - radio, x + radio, y + radio,
                fill=COLOR_BANDO.get(bando, "gray"),
                outline=COLOR_PORTADOR if es_portador else "white",
                width=4 if es_portador else 1,
            )
            lienzo.create_text(
                x, y, text=unidad, fill="white",
                font=("TkDefaultFont", max(7, self.celda // 5), "bold"),
            )

        portador = estado.portador or "—"
        self.etiqueta_estado.configure(
            text=f"Turno: {estado.turno} · Portador: {portador} · "
            f"Turnos jugados: {estado.turnos_jugados}"
        )


def main() -> None:
    """
    Purpose: Abrir la ventana de TacticalGrid (python -m tacticalgrid).
    Preconditions: Hay un entorno gráfico disponible para Tk.
    Postconditions: Bloquea en el bucle de eventos hasta que se cierra la ventana.
    Complexity: tiempo O(1) más lo que pida el usuario, espacio O(1)
    AI usage: Yes
    AI intervention: Código generado por IA a partir de la especificación del equipo.
    Student validation: OK
    """
    raiz = tk.Tk()
    AplicacionTacticalGrid(raiz)
    raiz.mainloop()
