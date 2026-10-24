"""
gui/main_window.py
==================

Ventana principal elegante del simulador de zona de Fresnel.
"""

import os
import threading
import tkinter as tk
from dataclasses import replace
from tkinter import ttk, messagebox, filedialog

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from visualization_engine import VisualizationEngine
from models.obstacle import Obstacle
from obstacle_repository import ObstacleRepository
from link_engine import LinkEngine
from link_budget import compute_link_budget
from export_service import ExportService


class ToolTip:
    """Tooltip simple para widgets."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind('<Enter>', self.enter)
        widget.bind('<Leave>', self.leave)

    def enter(self, event=None):
        bbox = self.widget.bbox("insert")
        if bbox is None:
            x = self.widget.winfo_rootx() + 25
            y = self.widget.winfo_rooty() + 25
        else:
            x, y, _, _ = bbox
            x += self.widget.winfo_rootx() + 25
            y += self.widget.winfo_rooty() + 25

        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("Segoe UI", 10))
        label.pack()

    def leave(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


class MainWindow:

    DEFAULT_REFLECTIVITY = 0.8

    def _resize_left_panel(self, event):
        self.left_canvas.itemconfig(self.left_window, width=event.width)

    def __init__(self, config: dict):
        self.config = config
        self.theme = config.get("theme", "dark")
        self.obstacles = []
        self.selected_obstacle_index = None
        self.last_data = None
        self.current_csv_path = None      # None -> ruta por defecto del repositorio
        self._busy = False                # hay un cálculo en curso
        self.tooltip_annot = None
        self._tip_key = None              # obstáculo cuyo tooltip está visible
        self.repo = ObstacleRepository()
        self.engine = LinkEngine(self.config)

        self.root = tk.Tk()
        self.root.title("ETN-913 · Analizador de Zona de Fresnel")
        self.root.geometry("1450x820")
        self.root.configure(bg="#0f1117")
        self.root.minsize(1200, 700)

        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._configure_styles()

        # Variables definidas ANTES de construir la interfaz
        self.include_reflections_var = tk.BooleanVar(value=False)

        self._build_layout()
        self._load_initial_obstacles()
        self.refresh_obstacle_list()

        self._bind_mousewheel()
        self.root.bind_all('<Return>', lambda e: self.calculate_link())
        self.root.bind_all('<Control-o>', lambda e: self.select_csv())
        self.root.bind_all('<Control-s>', lambda e: self._save_obstacles("Obstáculos guardados"))
        self.root.bind_all('<F5>', lambda e: self.calculate_link())
        self.root.bind_all('<Control-e>', lambda e: self.clear_results())

        self._setup_validation()

    def _load_initial_obstacles(self):
        try:
            self.obstacles = self.repo.load()
        except ValueError as e:
            self.obstacles = []
            messagebox.showerror(
                "Error al cargar obstáculos",
                f"{e}\n\nLa aplicación inicia sin obstáculos. Corrija el archivo "
                f"{self.repo.default_path} antes de agregar nuevos: al guardar se sobrescribiría.")

    # ---------------------- Métodos auxiliares (tarjetas, botones) ----------------------
    def _create_rounded_card(self, parent, bg_color="#1e293b", radius=6, **kwargs):
        canvas = tk.Canvas(parent, bg="#0f1722", highlightthickness=0, **kwargs)
        canvas.bind("<Configure>", lambda e: self._redraw_rounded_card(canvas, radius, bg_color))
        self._redraw_rounded_card(canvas, radius, bg_color)
        return canvas

    def _redraw_rounded_card(self, canvas, radius, color):
        w = canvas.winfo_width()
        h = canvas.winfo_height()
        if w <= 1 or h <= 1:
            return
        canvas.delete("rounded_bg")
        r = min(radius, w // 2, h // 2)
        canvas.create_rectangle(0, 0, w, h, fill=color, outline=color, tags="rounded_bg")
        bg = "#0f1722"
        canvas.create_polygon(0, 0, r, 0, 0, r, fill=bg, outline=bg, tags="rounded_bg")
        canvas.create_polygon(w, 0, w - r, 0, w, r, fill=bg, outline=bg, tags="rounded_bg")
        canvas.create_polygon(0, h, 0, h - r, r, h, fill=bg, outline=bg, tags="rounded_bg")
        canvas.create_polygon(w, h, w - r, h, w, h - r, fill=bg, outline=bg, tags="rounded_bg")
        if r > 0:
            canvas.create_arc(0, 0, 2*r, 2*r, start=90, extent=90, fill=color, outline=color, tags="rounded_bg")
            canvas.create_arc(w-2*r, 0, w, 2*r, start=0, extent=90, fill=color, outline=color, tags="rounded_bg")
            canvas.create_arc(0, h-2*r, 2*r, h, start=180, extent=90, fill=color, outline=color, tags="rounded_bg")
            canvas.create_arc(w-2*r, h-2*r, w, h, start=270, extent=90, fill=color, outline=color, tags="rounded_bg")

    def _create_rounded_button(self, parent, text, command, bg_color="#2563eb", radius=6, **kwargs):
        canvas = tk.Canvas(parent, bg="#0f1722", highlightthickness=0, height=kwargs.get("height", 36))
        canvas.pack_propagate(False)
        self._redraw_rounded_card(canvas, radius, bg_color)
        label = tk.Label(canvas, text=text, bg=bg_color, fg="white",
                         font=("Segoe UI Semibold", 10), cursor="hand2")
        label.place(relx=0.5, rely=0.5, anchor="center")
        hover_colors = {
            "#dc2626": "#ef4444",
            "#16a34a": "#22c55e",
            "#2563eb": "#3b82f6",
            "#4b5563": "#6b7280",
            "#8b5cf6": "#a78bfa",
        }
        hover_color = hover_colors.get(bg_color, "#3b82f6")

        def on_enter(e):
            self._redraw_rounded_card(canvas, radius, hover_color)
            label.config(bg=hover_color)

        def on_leave(e):
            self._redraw_rounded_card(canvas, radius, bg_color)
            label.config(bg=bg_color)

        def on_click(e):
            command()
        canvas.bind("<Button-1>", on_click)
        label.bind("<Button-1>", on_click)
        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)
        canvas.bind("<Configure>", lambda e: self._redraw_rounded_card(canvas, radius, bg_color))
        return canvas

    def _bind_mousewheel(self):
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)
        self.root.bind_all("<Button-4>", self._on_mousewheel)
        self.root.bind_all("<Button-5>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        if event.num == 4:
            delta = -1
        elif event.num == 5:
            delta = 1
        else:
            delta = -1 * (event.delta // 120)
        widget = event.widget
        is_treeview = False
        while widget:
            if widget == self.obstacle_tree:
                is_treeview = True
                break
            widget = widget.master
        if is_treeview:
            return
        mouse_x = self.root.winfo_pointerx()
        mouse_y = self.root.winfo_pointery()
        canvas_x = self.left_canvas.winfo_rootx()
        canvas_y = self.left_canvas.winfo_rooty()
        canvas_w = self.left_canvas.winfo_width()
        canvas_h = self.left_canvas.winfo_height()
        if (canvas_x <= mouse_x <= canvas_x + canvas_w and
                canvas_y <= mouse_y <= canvas_y + canvas_h):
            self.left_canvas.yview_scroll(delta, "units")

    def _configure_styles(self):
        self.style.configure("Panel.TFrame", background="#0f1722")
        self.style.configure("Card.TFrame", background="#1e293b", relief="flat", borderwidth=0)
        self.style.configure("Inner.TFrame", background="#1e293b")
        self.style.configure("Title.TLabel", background="#1e293b", foreground="#60a5fa",
                             font=("Segoe UI Semibold", 14), padding=(0, 0, 0, 8))
        self.style.configure("Section.TLabel", background="#1e293b", foreground="#cbd5e1",
                             font=("Segoe UI", 9, "bold"))
        self.style.configure("Modern.TEntry", padding=10, fieldbackground="#1e293b",
                             foreground="#ffffff", borderwidth=1, relief="solid", insertcolor="white")
        self.style.map("Modern.TEntry", bordercolor=[("focus", "#3b82f6"), ("!focus", "#334155")])
        self.style.configure("Error.TEntry", padding=10, fieldbackground="#450a0a",
                             foreground="#ffaaaa", borderwidth=1, relief="solid",
                             bordercolor="#ff4444", insertcolor="white")
        self.style.configure("Action.TButton", font=("Segoe UI Semibold", 10), padding=(16, 10),
                             background="#2563eb", foreground="white", borderwidth=0, relief="flat")
        self.style.map("Action.TButton", background=[("active", "#3b82f6"), ("pressed", "#1d4ed8")])
        self.style.configure("Treeview", background="#0f1722", foreground="#e2e8f0",
                             fieldbackground="#0f1722", rowheight=32, borderwidth=0, font=("Segoe UI", 10))
        self.style.configure("Treeview.Heading", background="#1e293b", foreground="#94a3b8",
                             font=("Segoe UI Semibold", 10), relief="flat", padding=6)
        self.style.map("Treeview", background=[("selected", "#2563eb")])
        self.style.map("Treeview.Heading", background=[("active", "#334155")])
        self.style.configure("Vertical.TScrollbar", background="#1e293b", troughcolor="#0f1722",
                             bordercolor="#0f1722", arrowcolor="#60a5fa", width=10)
        self.style.configure("Modern.TCheckbutton", background="#1e293b", foreground="#cbd5e1", font=("Segoe UI", 10))
        self.style.configure("Accent.TCheckbutton", background="#1e293b", foreground="#60a5fa",
                             font=("Segoe UI Semibold", 10), focuscolor="none")
        self.style.map("Accent.TCheckbutton", background=[("active", "#1e293b")], foreground=[("active", "#3b82f6")])
        self.style.configure("Small.TLabel", background="#1e293b", foreground="#94a3b8", font=("Segoe UI", 8))
        self.style.configure("Modern.Horizontal.TScale", background="#1e293b", troughcolor="#334155",
                             slidercolor="#3b82f6", sliderrelief="flat", borderwidth=0)
        self.style.map("Modern.Horizontal.TScale", slidercolor=[('active', '#60a5fa'), ('pressed', '#2563eb')])

    def _setup_validation(self):

        def validate(var, entry, allow_zero=False, allow_negative=False, max_value=None):
            val_str = var.get().strip()
            if val_str == "":
                entry.configure(style="Modern.TEntry")
                return
            try:
                val = float(val_str)
                if not allow_negative and val < 0:
                    raise ValueError
                if not allow_zero and val <= 0:
                    raise ValueError
                if max_value is not None and val > max_value:
                    raise ValueError
                entry.configure(style="Modern.TEntry")
            except ValueError:
                entry.configure(style="Error.TEntry")

        v = self
        v.frequency_var.trace_add("write", lambda *a: validate(v.frequency_var, v.freq_entry))
        v.distance_var.trace_add("write", lambda *a: validate(v.distance_var, v.dist_entry))
        v.tx_var.trace_add("write", lambda *a: validate(v.tx_var, v.tx_entry, allow_zero=True))
        v.rx_var.trace_add("write", lambda *a: validate(v.rx_var, v.rx_entry, allow_zero=True))
        v.tx_building_var.trace_add("write", lambda *a: validate(v.tx_building_var, v.tx_building_entry, allow_zero=True))
        v.rx_building_var.trace_add("write", lambda *a: validate(v.rx_building_var, v.rx_building_entry, allow_zero=True))
        v.obstacle_position_var.trace_add("write", lambda *a: validate(v.obstacle_position_var, v.pos_entry, allow_zero=True))
        v.obstacle_height_var.trace_add("write", lambda *a: validate(v.obstacle_height_var, v.h_entry, allow_zero=True))
        v.obstacle_reflectivity_var.trace_add("write", lambda *a: validate(
            v.obstacle_reflectivity_var, v.refl_entry, allow_zero=True, max_value=1.0))

        # dBm y dBi pueden ser cero o negativos
        v.tx_power_var.trace_add("write", lambda *a: validate(v.tx_power_var, v.tx_power_entry, allow_zero=True, allow_negative=True))
        v.rx_sensitivity_var.trace_add("write", lambda *a: validate(v.rx_sensitivity_var, v.rx_sensitivity_entry, allow_zero=True, allow_negative=True))
        v.tx_gain_var.trace_add("write", lambda *a: validate(v.tx_gain_var, v.tx_gain_entry, allow_zero=True, allow_negative=True))
        v.rx_gain_var.trace_add("write", lambda *a: validate(v.rx_gain_var, v.rx_gain_entry, allow_zero=True, allow_negative=True))

    def _build_layout(self):
        self.root.columnconfigure(0, weight=2)
        self.root.columnconfigure(1, weight=7)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)

        self.left_container = ttk.Frame(self.root, style="Panel.TFrame")
        self.left_container.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        self.left_canvas = tk.Canvas(self.left_container, bg="#0f1722", highlightthickness=0)
        self.left_canvas.pack(side="left", fill="both", expand=True)
        self.left_canvas.bind("<Configure>", self._resize_left_panel)
        self.left_scrollbar = ttk.Scrollbar(self.left_container, orient="vertical", command=self.left_canvas.yview)
        self.left_scrollbar.pack(side="right", fill="y")
        self.left_canvas.configure(yscrollcommand=self.left_scrollbar.set)
        self.left_panel = ttk.Frame(self.left_canvas, style="Panel.TFrame", padding=16)
        self.left_window = self.left_canvas.create_window((0, 0), window=self.left_panel, anchor="nw")
        self.left_panel.bind("<Configure>", lambda e: self.left_canvas.configure(scrollregion=self.left_canvas.bbox("all")))
        self._build_left_panel()

        self.right_panel = ttk.Frame(self.root, style="Panel.TFrame", padding=10)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 12), pady=12)
        self._build_graph_panel()

        self.bottom_panel = ttk.Frame(self.root, style="Panel.TFrame", padding=10)
        self.bottom_panel.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))
        self._build_results_panel()
        self._build_status_bar()

    def _build_status_bar(self):
        self.status_var = tk.StringVar()
        self.status_var.set("Listo")
        status_label = ttk.Label(self.bottom_panel, textvariable=self.status_var, style="Section.TLabel",
                                 background="#0f1722", anchor="w")
        status_label.pack(side="bottom", fill="x", pady=(5, 0))

    def update_status(self, message, duration=3000):
        self.status_var.set(message)
        if duration > 0:
            self.root.after(duration, lambda: self.status_var.set("Listo"))

    def _build_left_panel(self):
        header_frame = ttk.Frame(self.left_panel, style="Panel.TFrame")
        header_frame.pack(fill="x", pady=(0, 20))
        ttk.Label(header_frame, text="ETN-913", font=("Segoe UI Semibold", 22), foreground="#3b82f6",
                  background="#0f1722").pack(anchor="w")
        ttk.Label(header_frame, text="Analizador de Zona de Fresnel", font=("Segoe UI", 10),
                  foreground="#94a3b8", background="#0f1722").pack(anchor="w")
        ttk.Separator(header_frame, orient="horizontal").pack(fill="x", pady=(12, 0))

        self.obstacle_name_var = tk.StringVar()
        self.obstacle_position_var = tk.StringVar()
        self.obstacle_height_var = tk.StringVar()
        self.obstacle_reflectivity_var = tk.StringVar(value=str(self.DEFAULT_REFLECTIVITY))
        self.frequency_var = tk.StringVar(value="5")
        self.distance_var = tk.StringVar(value="2000")
        self.tx_var = tk.StringVar(value="80")       # altura antena TX
        self.rx_var = tk.StringVar(value="65")       # altura antena RX
        self.tx_building_var = tk.StringVar(value="80")   # altura edificio TX (por defecto igual a antena)
        self.rx_building_var = tk.StringVar(value="65")   # altura edificio RX

        # Parámetros de transmisión
        self.tx_power_var = tk.StringVar(value="20")
        self.tx_gain_var = tk.StringVar(value="15")
        self.rx_gain_var = tk.StringVar(value="15")
        self.rx_sensitivity_var = tk.StringVar(value="-85")   # dBm

        # Card 1: Parámetros del Enlace
        params_card = self._create_rounded_card(self.left_panel, bg_color="#1e293b", radius=6)
        params_card.pack(fill="x", pady=(0, 16))
        inner_params = ttk.Frame(params_card, style="Inner.TFrame")
        inner_params.pack(fill="both", expand=True, padx=18, pady=18)
        ttk.Label(inner_params, text="📡 Parámetros del Enlace", style="Title.TLabel").pack(anchor="w", pady=(0, 12))

        params_frame = ttk.Frame(inner_params, style="Inner.TFrame")
        params_frame.pack(fill="x", pady=(0, 8))
        top_row = ttk.Frame(params_frame, style="Inner.TFrame")
        top_row.pack(fill="x", pady=(0, 10))
        freq_frame = ttk.Frame(top_row, style="Inner.TFrame")
        freq_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Label(freq_frame, text="Frecuencia [GHz]", style="Section.TLabel").pack(anchor="w")
        self.freq_entry = ttk.Entry(freq_frame, textvariable=self.frequency_var, style="Modern.TEntry")
        self.freq_entry.pack(fill="x", pady=(4, 0))
        ToolTip(self.freq_entry, "Frecuencia en GHz (mayor que 0)")

        distance_frame = ttk.Frame(top_row, style="Inner.TFrame")
        distance_frame.pack(side="left", fill="x", expand=True, padx=(8, 0))
        ttk.Label(distance_frame, text="Distancia [m]", style="Section.TLabel").pack(anchor="w")
        self.dist_entry = ttk.Entry(distance_frame, textvariable=self.distance_var, style="Modern.TEntry")
        self.dist_entry.pack(fill="x", pady=(4, 0))
        ToolTip(self.dist_entry, "Distancia total del enlace en metros (modelo de tierra plana)")

        # Fila alturas de antena (sobre edificio)
        antenna_row = ttk.Frame(params_frame, style="Inner.TFrame")
        antenna_row.pack(fill="x", pady=(0, 10))
        tx_ant_frame = ttk.Frame(antenna_row, style="Inner.TFrame")
        tx_ant_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Label(tx_ant_frame, text="Antena TX (sobre edificio) [m]", style="Section.TLabel").pack(anchor="w")
        self.tx_entry = ttk.Entry(tx_ant_frame, textvariable=self.tx_var, style="Modern.TEntry")
        self.tx_entry.pack(fill="x", pady=(4, 0))
        ToolTip(self.tx_entry, "Altura adicional de la antena sobre el edificio (puede ser 0)")

        rx_ant_frame = ttk.Frame(antenna_row, style="Inner.TFrame")
        rx_ant_frame.pack(side="left", fill="x", expand=True, padx=(8, 0))
        ttk.Label(rx_ant_frame, text="Antena RX (sobre edificio) [m]", style="Section.TLabel").pack(anchor="w")
        self.rx_entry = ttk.Entry(rx_ant_frame, textvariable=self.rx_var, style="Modern.TEntry")
        self.rx_entry.pack(fill="x", pady=(4, 0))
        ToolTip(self.rx_entry, "Altura adicional de la antena sobre el edificio (puede ser 0)")

        # Fila alturas de edificio
        building_row = ttk.Frame(params_frame, style="Inner.TFrame")
        building_row.pack(fill="x", pady=(0, 10))
        tx_build_frame = ttk.Frame(building_row, style="Inner.TFrame")
        tx_build_frame.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Label(tx_build_frame, text="Altura edificio TX [m]", style="Section.TLabel").pack(anchor="w")
        self.tx_building_entry = ttk.Entry(tx_build_frame, textvariable=self.tx_building_var, style="Modern.TEntry")
        self.tx_building_entry.pack(fill="x", pady=(4, 0))
        ToolTip(self.tx_building_entry, "Altura del edificio en el lado TX (desde el suelo)")

        rx_build_frame = ttk.Frame(building_row, style="Inner.TFrame")
        rx_build_frame.pack(side="left", fill="x", expand=True, padx=(8, 0))
        ttk.Label(rx_build_frame, text="Altura edificio RX [m]", style="Section.TLabel").pack(anchor="w")
        self.rx_building_entry = ttk.Entry(rx_build_frame, textvariable=self.rx_building_var, style="Modern.TEntry")
        self.rx_building_entry.pack(fill="x", pady=(4, 0))
        ToolTip(self.rx_building_entry, "Altura del edificio en el lado RX (desde el suelo)")

        # Fila factor de despejamiento y zonas
        row_clearance_zones = ttk.Frame(inner_params, style="Inner.TFrame")
        row_clearance_zones.pack(fill="x", pady=(12, 0))
        row_clearance_zones.columnconfigure(0, weight=1)
        row_clearance_zones.columnconfigure(1, weight=1)

        clearance_frame = ttk.Frame(row_clearance_zones, style="Inner.TFrame")
        clearance_frame.grid(row=0, column=0, padx=(0, 30), sticky="ew")
        ttk.Label(clearance_frame, text="Despeje mínimo [×r₁] (0.1–1.2):", style="Section.TLabel").pack(anchor="w")
        self.clearance_factor_var = tk.DoubleVar(value=self.config.get("clearance_acceptable", 0.6))
        self.clearance_slider = ttk.Scale(clearance_frame, from_=0.1, to=1.2,
                                          variable=self.clearance_factor_var,
                                          orient='horizontal', style="Modern.Horizontal.TScale")
        self.clearance_slider.pack(fill="x", pady=(4, 2))
        clearance_value_entry = ttk.Entry(clearance_frame, textvariable=self.clearance_factor_var,
                                          width=5, style="Modern.TEntry")
        clearance_value_entry.pack(side="right", padx=(5, 0))
        ToolTip(clearance_value_entry, "Despeje mínimo (fracción de r1) para que un obstáculo sea ACEPTABLE y radio de la zona de despejamiento dibujada. 0.6 = criterio habitual (60 % de la 1ª zona de Fresnel)")

        zones_frame = ttk.Frame(row_clearance_zones, style="Inner.TFrame")
        zones_frame.grid(row=0, column=1, padx=(8, 0), sticky="ew")
        ttk.Label(zones_frame, text="Zonas de Fresnel a mostrar:", style="Section.TLabel").pack(anchor="w")
        self.zones_var = tk.IntVar(value=1)
        zones_spin = ttk.Spinbox(zones_frame, from_=1, to=5, textvariable=self.zones_var,
                                 width=6, font=("Segoe UI", 10), style="Modern.TEntry")
        zones_spin.pack(anchor="w", pady=(4, 0), fill="x")
        ToolTip(zones_spin, "Número de zonas de Fresnel a dibujar (1 a 5)")

        reflections_frame = ttk.Frame(inner_params, style="Inner.TFrame")
        reflections_frame.pack(fill="x", pady=(8, 0))
        self.reflections_check = ttk.Checkbutton(
            reflections_frame, text="Incluir reflexiones en obstáculos (modelo de un rebote)",
            variable=self.include_reflections_var, style="Accent.TCheckbutton")
        self.reflections_check.pack(anchor="w")
        ToolTip(self.reflections_check,
                "Suma coherente de los rayos reflejados en cada obstáculo; el factor se incluye en la potencia recibida")

        # Card: Parámetros de Transmisión
        tx_params_card = self._create_rounded_card(self.left_panel, bg_color="#1e293b", radius=6)
        tx_params_card.pack(fill="x", pady=(0, 16))
        inner_tx_params = ttk.Frame(tx_params_card, style="Inner.TFrame")
        inner_tx_params.pack(fill="both", expand=True, padx=18, pady=18)
        ttk.Label(inner_tx_params, text="🔧 Parámetros de Transmisión", style="Title.TLabel").pack(anchor="w", pady=(0, 12))

        tx_params_frame = ttk.Frame(inner_tx_params, style="Inner.TFrame")
        tx_params_frame.pack(fill="x")

        # Fila 1: Potencia TX y Sensibilidad RX
        row1 = ttk.Frame(tx_params_frame, style="Inner.TFrame")
        row1.pack(fill="x", pady=(0, 10))
        row1.columnconfigure(0, weight=1)
        row1.columnconfigure(1, weight=1)

        tx_power_frame = ttk.Frame(row1, style="Inner.TFrame")
        tx_power_frame.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ttk.Label(tx_power_frame, text="Potencia TX [dBm]", style="Section.TLabel").pack(anchor="w")
        self.tx_power_entry = ttk.Entry(tx_power_frame, textvariable=self.tx_power_var, style="Modern.TEntry")
        self.tx_power_entry.pack(fill="x", pady=(4, 0))
        ToolTip(self.tx_power_entry, "Potencia de transmisión en dBm")

        rx_sens_frame = ttk.Frame(row1, style="Inner.TFrame")
        rx_sens_frame.grid(row=0, column=1, padx=(4, 0), sticky="ew")
        ttk.Label(rx_sens_frame, text="Sensibilidad RX [dBm]", style="Section.TLabel").pack(anchor="w")
        self.rx_sensitivity_entry = ttk.Entry(rx_sens_frame, textvariable=self.rx_sensitivity_var, style="Modern.TEntry")
        self.rx_sensitivity_entry.pack(fill="x", pady=(4, 0))
        ToolTip(self.rx_sensitivity_entry, "Potencia mínima que el receptor puede detectar (dBm)")

        # Fila 2: Ganancia TX y Ganancia RX
        row2 = ttk.Frame(tx_params_frame, style="Inner.TFrame")
        row2.pack(fill="x", pady=(0, 0))
        row2.columnconfigure(0, weight=1)
        row2.columnconfigure(1, weight=1)

        tx_gain_frame = ttk.Frame(row2, style="Inner.TFrame")
        tx_gain_frame.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ttk.Label(tx_gain_frame, text="Ganancia antena TX [dBi]", style="Section.TLabel").pack(anchor="w")
        self.tx_gain_entry = ttk.Entry(tx_gain_frame, textvariable=self.tx_gain_var, style="Modern.TEntry")
        self.tx_gain_entry.pack(fill="x", pady=(4, 0))
        ToolTip(self.tx_gain_entry, "Ganancia de la antena transmisora en dBi")

        rx_gain_frame = ttk.Frame(row2, style="Inner.TFrame")
        rx_gain_frame.grid(row=0, column=1, padx=(4, 0), sticky="ew")
        ttk.Label(rx_gain_frame, text="Ganancia antena RX [dBi]", style="Section.TLabel").pack(anchor="w")
        self.rx_gain_entry = ttk.Entry(rx_gain_frame, textvariable=self.rx_gain_var, style="Modern.TEntry")
        self.rx_gain_entry.pack(fill="x", pady=(4, 0))
        ToolTip(self.rx_gain_entry, "Ganancia de la antena receptora en dBi")

        # Card 2: Nuevo Obstáculo
        obstacle_card = self._create_rounded_card(self.left_panel, bg_color="#1e293b", radius=6)
        obstacle_card.pack(fill="x", pady=(0, 16))
        inner_obstacle = ttk.Frame(obstacle_card, style="Inner.TFrame")
        inner_obstacle.pack(fill="both", expand=True, padx=18, pady=18)
        ttk.Label(inner_obstacle, text="➕ Nuevo Obstáculo", style="Title.TLabel").pack(anchor="w", pady=(0, 12))

        fields_frame = ttk.Frame(inner_obstacle, style="Inner.TFrame")
        fields_frame.pack(fill="x", pady=(0, 12))
        name_frame = ttk.Frame(fields_frame, style="Inner.TFrame")
        name_frame.pack(side="left", fill="x", expand=True)
        ttk.Label(name_frame, text="Nombre", style="Section.TLabel").pack(anchor="w")
        self.name_entry = ttk.Entry(name_frame, textvariable=self.obstacle_name_var, width=14, style="Modern.TEntry")
        self.name_entry.pack(fill="x", pady=(4, 0))
        ToolTip(self.name_entry, "Identificador del obstáculo")

        pos_frame = ttk.Frame(fields_frame, style="Inner.TFrame")
        pos_frame.pack(side="left", padx=8)
        ttk.Label(pos_frame, text="Posición [m]", style="Section.TLabel").pack(anchor="w")
        self.pos_entry = ttk.Entry(pos_frame, textvariable=self.obstacle_position_var, width=8, style="Modern.TEntry")
        self.pos_entry.pack(fill="x", pady=(4, 0))
        ToolTip(self.pos_entry, "Distancia desde el transmisor hasta el obstáculo (0 a distancia total)")

        h_frame = ttk.Frame(fields_frame, style="Inner.TFrame")
        h_frame.pack(side="left")
        ttk.Label(h_frame, text="Altura [m]", style="Section.TLabel").pack(anchor="w")
        self.h_entry = ttk.Entry(h_frame, textvariable=self.obstacle_height_var, width=8, style="Modern.TEntry")
        self.h_entry.pack(fill="x", pady=(4, 0))
        ToolTip(self.h_entry, "Altura del obstáculo sobre el suelo")

        refl_frame = ttk.Frame(inner_obstacle, style="Inner.TFrame")
        refl_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(refl_frame, text="Reflectividad (0–1)", style="Section.TLabel").pack(anchor="w")
        self.refl_entry = ttk.Entry(refl_frame, textvariable=self.obstacle_reflectivity_var,
                                    width=8, style="Modern.TEntry")
        self.refl_entry.pack(anchor="w", pady=(4, 0))
        ToolTip(self.refl_entry, "Coeficiente de reflexión del obstáculo (0 = no refleja, 1 = reflexión total)")

        buttons_frame = ttk.Frame(inner_obstacle, style="Inner.TFrame")
        buttons_frame.pack(fill="x", pady=(4, 0))
        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.columnconfigure(1, weight=1)
        btn_add = self._create_rounded_button(buttons_frame, "➕ Agregar", self.add_obstacle, radius=6, bg_color="#16a34a")
        btn_add.grid(row=0, column=0, padx=4, pady=2, sticky="ew")
        btn_update = self._create_rounded_button(buttons_frame, "✏ Actualizar", self.update_obstacle, radius=6, bg_color="#2563eb")
        btn_update.grid(row=0, column=1, padx=4, pady=2, sticky="ew")
        ToolTip(btn_add, "Añadir obstáculo a la lista")
        ToolTip(btn_update, "Actualizar obstáculo seleccionado")

        # Card 3: Obstáculos cargados
        obstacles_card = self._create_rounded_card(self.left_panel, bg_color="#1e293b", radius=6)
        obstacles_card.pack(fill="x", pady=(0, 16))
        inner_obstacles = ttk.Frame(obstacles_card, style="Inner.TFrame")
        inner_obstacles.pack(fill="both", expand=True, padx=18, pady=18)
        ttk.Label(inner_obstacles, text="⚙ Obstáculos cargados", style="Title.TLabel").pack(anchor="w", pady=(0, 10))

        list_frame = ttk.Frame(inner_obstacles, style="Inner.TFrame")
        list_frame.pack(fill="both", expand=True, pady=(4, 10))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        scrollbar.pack(side="right", fill="y")
        self.obstacle_tree = ttk.Treeview(list_frame, columns=("name", "position", "height"),
                                          show="headings", height=4, selectmode='extended')
        self.obstacle_tree.heading("name", text="Nombre")
        self.obstacle_tree.heading("position", text="Posición [m]")
        self.obstacle_tree.heading("height", text="Altura [m]")
        self.obstacle_tree.column("name", width=150, anchor="w")
        self.obstacle_tree.column("position", width=90, anchor="center")
        self.obstacle_tree.column("height", width=90, anchor="center")
        self.obstacle_tree.pack(side="left", fill="both", expand=True)
        self.obstacle_tree.bind("<<TreeviewSelect>>", self.on_obstacle_select)
        self.obstacle_tree.bind("<Double-1>", self.on_double_click)
        scrollbar.config(command=self.obstacle_tree.yview)
        self.obstacle_tree.configure(yscrollcommand=scrollbar.set)

        manage_frame = ttk.Frame(inner_obstacles, style="Inner.TFrame")
        manage_frame.pack(fill="x", pady=(6, 0))
        manage_frame.columnconfigure(0, weight=1)
        manage_frame.columnconfigure(1, weight=1)
        btn_del = self._create_rounded_button(manage_frame, "❌ Eliminar", self.delete_obstacle, radius=6, bg_color="#dc2626")
        btn_del.grid(row=0, column=0, padx=4, pady=2, sticky="ew")
        btn_csv = self._create_rounded_button(manage_frame, "📂 Cargar CSV", self.select_csv, radius=6, bg_color="#2563eb")
        btn_csv.grid(row=0, column=1, padx=4, pady=2, sticky="ew")

        # Card 4: Controles
        controls_card = self._create_rounded_card(self.left_panel, bg_color="#1e293b", radius=6)
        controls_card.pack(fill="x", pady=(0, 16))
        inner_controls = ttk.Frame(controls_card, style="Inner.TFrame")
        inner_controls.pack(fill="both", expand=True, padx=18, pady=18)
        ttk.Label(inner_controls, text="🎛 Controles", style="Title.TLabel").pack(anchor="w", pady=(0, 12))

        # Fila 1: Calcular y Limpiar
        calc_frame = ttk.Frame(inner_controls, style="Inner.TFrame")
        calc_frame.pack(fill="x", pady=(4, 8))
        calc_frame.columnconfigure(0, weight=1)
        calc_frame.columnconfigure(1, weight=1)
        self.calc_button = self._create_rounded_button(calc_frame, "▶ Calcular", self.calculate_link, radius=6, bg_color="#16a34a")
        self.calc_button.grid(row=0, column=0, padx=4, pady=2, sticky="ew")
        btn_clear = self._create_rounded_button(calc_frame, "🗑 Limpiar", self.clear_results, radius=6, bg_color="#4b5563")
        btn_clear.grid(row=0, column=1, padx=4, pady=2, sticky="ew")

        ttk.Separator(inner_controls, orient="horizontal").pack(fill="x", pady=10)

        # Fila 2: Exportar PDF y Vista 3D
        row_export_3d = ttk.Frame(inner_controls, style="Inner.TFrame")
        row_export_3d.pack(fill="x", pady=(0, 8))
        row_export_3d.columnconfigure(0, weight=1)
        row_export_3d.columnconfigure(1, weight=1)

        btn_export = self._create_rounded_button(row_export_3d, "📄 Exportar PDF", self.export_report, radius=6, bg_color="#8b5cf6")
        btn_export.grid(row=0, column=0, padx=4, pady=2, sticky="ew")
        ToolTip(btn_export, "Exportar gráfica y resultados a PDF")

        btn_3d = self._create_rounded_button(row_export_3d, "🌍 Vista 3D", self.open_3d_view, radius=6, bg_color="#3b82f6")
        btn_3d.grid(row=0, column=1, padx=4, pady=2, sticky="ew")
        ToolTip(btn_3d, "Abrir visualización 3D interactiva")

        # Fila 3: Salir
        row_exit = ttk.Frame(inner_controls, style="Inner.TFrame")
        row_exit.pack(fill="x", pady=(4, 0))
        btn_exit = self._create_rounded_button(row_exit, "✕ Salir", self.root.destroy, radius=6, bg_color="#dc2626")
        btn_exit.pack(fill="x", padx=4, pady=2)
        ToolTip(btn_exit, "Salir de la aplicación")

        for card in [params_card, tx_params_card, obstacle_card, obstacles_card, controls_card]:
            card.update_idletasks()
            self._redraw_rounded_card(card, 6, "#1e293b")

    def _build_graph_panel(self):
        self.figure = Figure(figsize=(9, 7), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.right_panel)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Aplicar tema (colores) inicial
        self.apply_theme()

        # Eventos de pan (arrastrar con botón izquierdo)
        self._pan_start = None
        self._pan_limits = None
        self.canvas.mpl_connect('button_press_event', self._on_pan_press)
        self.canvas.mpl_connect('button_release_event', self._on_pan_release)
        self.canvas.mpl_connect('motion_notify_event', self._on_pan_motion)

        # Zoom con rueda y tooltip al pasar sobre obstáculos
        self.canvas.mpl_connect('scroll_event', self._on_mousewheel_zoom)
        self.canvas.mpl_connect("motion_notify_event", self.on_hover)

    def _on_pan_press(self, event):
        if event.inaxes == self.ax and event.button == 1:
            self._pan_start = (event.xdata, event.ydata)
            self._pan_limits = (self.ax.get_xlim(), self.ax.get_ylim())
            self.canvas.get_tk_widget().config(cursor="hand2")

    def _on_pan_release(self, event):
        self._pan_start = None
        self._pan_limits = None
        self.canvas.get_tk_widget().config(cursor="")

    def _on_pan_motion(self, event):
        if self._pan_start is not None and event.inaxes == self.ax:
            dx = event.xdata - self._pan_start[0]
            dy = event.ydata - self._pan_start[1]
            xlim, ylim = self._pan_limits
            new_xlim = self._clamp_limits((xlim[0] - dx, xlim[1] - dx), 0)
            new_ylim = self._clamp_limits((ylim[0] - dy, ylim[1] - dy), 0)
            self.ax.set_xlim(new_xlim)
            self.ax.set_ylim(new_ylim)
            self.canvas.draw_idle()

    def _clamp_limits(self, lim, min_val=0):
        """Ajusta un rango (low, high) para que low >= min_val y high >= min_val."""
        low, high = lim
        if low < min_val:
            high += (min_val - low)
            low = min_val
        if high < min_val:
            high = min_val
        if low > high:
            low, high = high, low
        return (low, high)

    def _build_results_panel(self):
        header_frame = ttk.Frame(self.bottom_panel, style="Inner.TFrame")
        header_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(header_frame, text="Resultados del Enlace", style="Title.TLabel").pack(side="left")

        theme_btn = self._create_rounded_button(header_frame, "🌓 Cambiar Tema", self.toggle_theme,
                                                radius=6, bg_color="#4b5563", height=32)
        theme_btn.pack(side="right", padx=5)
        ToolTip(theme_btn, "Alternar entre tema claro y oscuro (solo gráfica)")

        self.results_box = tk.Text(self.bottom_panel, height=8, bg="#0f1722", fg="#cbd5e1",
                                   insertbackground="white", relief="flat", padx=12, pady=10,
                                   font=("Cascadia Code", 10))
        self.results_box.pack(fill="both", expand=True)
        self.results_box.tag_config("green", foreground="#4ade80")
        self.results_box.tag_config("yellow", foreground="#facc15")
        self.results_box.tag_config("red", foreground="#f87171")
        self.results_box.tag_config("bold", font=("Cascadia Code", 10, "bold"))

    # ---------------------- Obstáculos ----------------------
    def refresh_obstacle_list(self):
        for item in self.obstacle_tree.get_children():
            self.obstacle_tree.delete(item)
        if not self.obstacles:
            self.obstacle_tree.insert("", "end", values=("--- Sin obstáculos ---", "", ""), tags=("empty",))
            self.obstacle_tree.tag_configure("empty", foreground="#60a5fa", font=("Segoe UI", 9, "italic"))
        else:
            for obs in self.obstacles:
                self.obstacle_tree.insert("", "end", values=(obs.name, f"{obs.position:.0f}", f"{obs.height:.1f}"))

    def _clear_obstacle_fields(self):
        self.obstacle_name_var.set("")
        self.obstacle_position_var.set("")
        self.obstacle_height_var.set("")
        self.obstacle_reflectivity_var.set(str(self.DEFAULT_REFLECTIVITY))

    def _invalidate_results(self):
        """
        Los resultados dejan de corresponder a la lista de obstáculos:
        se descartan los datos del último cálculo (evita índices/estados
        desfasados al redibujar o exportar).
        """
        if self.last_data is not None:
            self.last_data = None
            self.update_status("Obstáculos modificados: vuelva a calcular", 4000)

    def _save_obstacles(self, ok_message=None):
        try:
            self.repo.save(self.obstacles, self.current_csv_path)
        except OSError as e:
            messagebox.showerror("Error al guardar", str(e))
            return False
        if ok_message:
            self.update_status(ok_message)
        return True

    def _parse_obstacle_fields(self):
        """Lee y valida los campos del formulario de obstáculos."""
        name = self.obstacle_name_var.get().strip()
        if not name:
            raise ValueError("Ingrese un nombre.")
        try:
            position = float(self.obstacle_position_var.get())
            height = float(self.obstacle_height_var.get())
        except ValueError:
            raise ValueError("Posición y altura deben ser números válidos.")
        refl_text = self.obstacle_reflectivity_var.get().strip()
        try:
            reflectivity = float(refl_text) if refl_text else self.DEFAULT_REFLECTIVITY
        except ValueError:
            raise ValueError("La reflectividad debe ser un número entre 0 y 1.")
        if not 0 <= reflectivity <= 1:
            raise ValueError("La reflectividad debe estar entre 0 y 1.")
        if height < 0:
            raise ValueError("La altura del obstáculo no puede ser negativa.")
        dist_text = self.distance_var.get().strip()
        try:
            distance = float(dist_text) if dist_text else None
        except ValueError:
            distance = None
        if position < 0 or (distance and position > distance):
            limit = f"{distance:g} m" if distance else "la distancia total"
            raise ValueError(f"La posición del obstáculo debe estar entre 0 y {limit}.")
        return name, position, height, reflectivity

    def on_obstacle_select(self, event):
        selection = self.obstacle_tree.selection()
        if not selection:
            return
        if len(selection) > 1:
            self.selected_obstacle_index = None
            self.obstacle_name_var.set("")
            self.obstacle_position_var.set("")
            self.obstacle_height_var.set("")
            self.obstacle_reflectivity_var.set("")
            return
        values = self.obstacle_tree.item(selection[0], "values")
        if values[0] == "--- Sin obstáculos ---":
            return
        index = self.obstacle_tree.index(selection[0])
        obs = self.obstacles[index]
        self.selected_obstacle_index = index
        self.obstacle_name_var.set(obs.name)
        self.obstacle_position_var.set(str(obs.position))
        self.obstacle_height_var.set(str(obs.height))
        self.obstacle_reflectivity_var.set(str(obs.reflectivity))
        self.redraw_with_selected_obstacle()

    def on_double_click(self, event):
        self.on_obstacle_select(event)
        if self.selected_obstacle_index is not None:
            self.name_entry.focus_set()

    def select_csv(self):
        filename = filedialog.askopenfilename(title="Seleccionar CSV", filetypes=[("CSV Files", "*.csv")])
        if not filename:
            return
        try:
            loaded = self.repo.load(filename)
        except ValueError as e:
            messagebox.showerror("Error al cargar CSV", str(e))
            return
        self.obstacles = loaded
        self.current_csv_path = filename   # los cambios posteriores se guardan en este archivo
        self.selected_obstacle_index = None
        self._invalidate_results()
        self.refresh_obstacle_list()
        self.update_status(f"CSV cargado: {len(self.obstacles)} obstáculos")

    def add_obstacle(self):
        try:
            name, position, height, reflectivity = self._parse_obstacle_fields()
            obs = Obstacle(name=name, position=position, height=height, reflectivity=reflectivity)
            self.obstacles.append(obs)
            if not self._save_obstacles():
                self.obstacles.pop()
                return
            self._invalidate_results()
            self.refresh_obstacle_list()
            self.update_status(f"Obstáculo agregado: {obs.name}")
            self._clear_obstacle_fields()
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def update_obstacle(self):
        if self.selected_obstacle_index is None:
            messagebox.showwarning("Advertencia", "Seleccione un obstáculo.")
            return
        try:
            # Se valida ANTES de modificar el objeto: un error no lo deja a medias
            name, position, height, reflectivity = self._parse_obstacle_fields()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return
        obs = self.obstacles[self.selected_obstacle_index]
        obs.name, obs.position, obs.height, obs.reflectivity = name, position, height, reflectivity
        self._save_obstacles()
        self._invalidate_results()
        self.refresh_obstacle_list()
        self.selected_obstacle_index = None
        self._clear_obstacle_fields()
        self.update_status(f"Obstáculo actualizado: {obs.name}")

    def delete_obstacle(self):
        selection = self.obstacle_tree.selection()
        if not selection:
            messagebox.showwarning("Advertencia", "Seleccione al menos un obstáculo.")
            return
        first_values = self.obstacle_tree.item(selection[0], "values")
        if first_values[0] == "--- Sin obstáculos ---":
            return
        count = len(selection)
        if not messagebox.askyesno("Confirmar eliminación", f"¿Eliminar {count} obstáculo(s)?"):
            return
        indices = sorted([self.obstacle_tree.index(item) for item in selection], reverse=True)
        for idx in indices:
            del self.obstacles[idx]
        self._save_obstacles()
        self._invalidate_results()
        self.refresh_obstacle_list()
        self.selected_obstacle_index = None
        self._clear_obstacle_fields()
        self.update_status(f"Eliminados {count} obstáculo(s)")

    # ---------------------- Cálculo ----------------------
    @staticmethod
    def _read_float(var, label):
        try:
            return float(var.get())
        except (ValueError, tk.TclError):
            raise ValueError(f"'{label}' no es un número válido.")

    def _read_params(self):
        """
        Lee y valida todos los parámetros desde los widgets.
        Se ejecuta en el hilo principal (Tk no es seguro entre hilos).
        """
        p = {
            "frequency_ghz": self._read_float(self.frequency_var, "Frecuencia"),
            "distance_m": self._read_float(self.distance_var, "Distancia"),
            "tx_antenna_extra": self._read_float(self.tx_var, "Antena TX"),
            "rx_antenna_extra": self._read_float(self.rx_var, "Antena RX"),
            "tx_building": self._read_float(self.tx_building_var, "Altura edificio TX"),
            "rx_building": self._read_float(self.rx_building_var, "Altura edificio RX"),
            "tx_power_dBm": self._read_float(self.tx_power_var, "Potencia TX"),
            "tx_gain_dBi": self._read_float(self.tx_gain_var, "Ganancia TX"),
            "rx_gain_dBi": self._read_float(self.rx_gain_var, "Ganancia RX"),
            "rx_sensitivity_dBm": self._read_float(self.rx_sensitivity_var, "Sensibilidad RX"),
            "clearance_factor": self._read_float(self.clearance_factor_var, "Despeje mínimo"),
        }
        try:
            p["n_zones"] = int(self.zones_var.get())
        except (ValueError, tk.TclError):
            raise ValueError("'Zonas de Fresnel' debe ser un entero entre 1 y 5.")
        p["include_reflections"] = bool(self.include_reflections_var.get())

        if p["frequency_ghz"] <= 0:
            raise ValueError("La frecuencia debe ser mayor que cero.")
        if p["distance_m"] <= 0:
            raise ValueError("La distancia debe ser mayor que cero.")
        if min(p["tx_building"], p["rx_building"]) < 0:
            raise ValueError("Las alturas de edificio no pueden ser negativas.")
        if min(p["tx_antenna_extra"], p["rx_antenna_extra"]) < 0:
            raise ValueError("Las alturas de antena adicionales no pueden ser negativas.")
        if not 0.1 <= p["clearance_factor"] <= 1.2:
            raise ValueError("El despeje mínimo debe estar entre 0.1 y 1.2 (×r1).")
        if not 1 <= p["n_zones"] <= 5:
            raise ValueError("Las zonas de Fresnel deben estar entre 1 y 5.")

        # Alturas totales para el cálculo electromagnético
        p["tx_total"] = p["tx_building"] + p["tx_antenna_extra"]
        p["rx_total"] = p["rx_building"] + p["rx_antenna_extra"]
        return p

    def calculate_link(self):
        if self._busy:
            self.update_status("Hay un cálculo en curso...", 2000)
            return
        try:
            params = self._read_params()
        except ValueError as e:
            messagebox.showerror("Error", str(e))
            return

        if not self.obstacles:
            messagebox.showwarning("Advertencia", "No existen obstáculos cargados.")
            return

        self._busy = True
        self.update_status(f"Calculando con zonas={params['n_zones']}...", 0)

        self.last_data = None
        self.obstacle_tree.selection_remove(self.obstacle_tree.selection())

        # Copia de los obstáculos: el cálculo y los resultados no se ven
        # afectados por ediciones posteriores de la lista.
        snapshot = [replace(o) for o in self.obstacles]
        thread = threading.Thread(target=self._calc_task, args=(params, snapshot), daemon=True)
        thread.start()

    def _calc_task(self, params, obstacles):
        """Cálculo en hilo secundario: NO accede a widgets Tk."""
        try:
            x, fresnel_zones, fmax, wavelength, results, los, reflection_factor_db = self.engine.compute(
                params["frequency_ghz"] * 1e9, params["distance_m"],
                params["tx_total"], params["rx_total"],
                obstacles,
                n_zones=params["n_zones"],
                include_reflections=params["include_reflections"],
                clearance_factor=params["clearance_factor"]
            )
            calc = {
                "x": x, "fresnel_zones": fresnel_zones, "fmax": fmax,
                "wavelength": wavelength, "results": results, "los": los,
                "reflection_factor_db": reflection_factor_db,
            }
            self.root.after(0, self._update_gui_after_calc, params, obstacles, calc)
        except Exception as e:
            self.root.after(0, self._show_calc_error, str(e))

    def _update_gui_after_calc(self, params, obstacles, calc):
        try:
            results = calc["results"]
            total_diff_loss = sum(r.diffraction_loss_db for r in results)
            budget = compute_link_budget(
                params["distance_m"], params["frequency_ghz"] * 1e9,
                params["tx_power_dBm"], params["tx_gain_dBi"], params["rx_gain_dBi"],
                params["rx_sensitivity_dBm"],
                diffraction_loss_db=total_diff_loss,
                reflection_factor_db=calc["reflection_factor_db"],
            )

            # Todo lo necesario para redibujar y exportar queda guardado:
            # el PDF reutiliza exactamente estos valores.
            self.last_data = {
                'x': calc["x"],
                'fresnel_zones': calc["fresnel_zones"],
                'los': calc["los"],
                'distance_m': params["distance_m"],
                'frequency_ghz': params["frequency_ghz"],
                'tx_total': params["tx_total"],
                'rx_total': params["rx_total"],
                'tx_building_height': params["tx_building"],
                'rx_building_height': params["rx_building"],
                'tx_antenna_extra': params["tx_antenna_extra"],
                'rx_antenna_extra': params["rx_antenna_extra"],
                'obstacles': obstacles,
                'results': results,
                'fmax': calc["fmax"],
                'wavelength': calc["wavelength"],
                'reflection_factor_db': calc["reflection_factor_db"],
                'include_reflections': params["include_reflections"],
                'clearance_factor': params["clearance_factor"],
                'budget': budget,
            }

            self._render_plot()
            self._write_results(budget, calc["wavelength"], calc["fmax"], results)
            self.update_status("Cálculo completado")
        except Exception as e:
            self.last_data = None
            messagebox.showerror("Error en el cálculo", str(e))
            self.update_status("Error en el cálculo")
        finally:
            self._busy = False

    def _write_results(self, budget, wavelength, fmax, results):
        box = self.results_box
        box.delete(1.0, tk.END)
        box.insert(tk.END, f"Longitud de onda: {wavelength:.4f} m\n", "bold")
        box.insert(tk.END, f"Radio máximo Fresnel (1ª zona): {fmax:.2f} m\n\n", "bold")

        box.insert(tk.END, "=== Link Budget ===\n", "bold")
        box.insert(tk.END, f"Potencia TX: {budget.tx_power_dbm:.2f} dBm\n")
        box.insert(tk.END, f"Ganancia TX: {budget.tx_gain_dbi:.2f} dBi\n")
        box.insert(tk.END, f"Ganancia RX: {budget.rx_gain_dbi:.2f} dBi\n")
        box.insert(tk.END, f"FSL: {budget.fsl_db:.2f} dB\n")
        box.insert(tk.END, f"Pérdida por difracción total: {budget.diffraction_loss_db:.2f} dB\n")
        box.insert(tk.END, f"Factor por reflexión en obstáculos: {budget.reflection_factor_db:+.2f} dB\n")
        box.insert(tk.END, f"Potencia recibida: {budget.rx_power_dbm:.2f} dBm\n")
        box.insert(tk.END, f"Sensibilidad RX: {budget.rx_sensitivity_dbm} dBm\n")
        box.insert(tk.END, f"Margen: {budget.margin_db:.2f} dB")
        if budget.viable:
            box.insert(tk.END, " (Enlace viable)\n", "green")
        else:
            box.insert(tk.END, " (Enlace NO viable)\n", "red")

        box.insert(tk.END, "\n\n=== Obstáculos ===\n", "bold")
        for r in results:
            if "ACEPTABLE" in r.state:
                tag = "green"
            elif "CRITICO" in r.state:
                tag = "yellow"
            else:
                tag = "red"
            box.insert(tk.END, r.message + "\n", tag)

    def _show_calc_error(self, error_msg):
        self._busy = False
        messagebox.showerror("Error en el cálculo", error_msg)
        self.update_status("Error en el cálculo")

    # ---------------------- Dibujo ----------------------
    def _render_plot(self, selected_idx=None):
        """
        Dibuja el último cálculo. ax.clear() elimina la anotación del tooltip
        y restablece los colores de ejes, por lo que ambos se recrean aquí.
        """
        d = self.last_data
        self.tooltip_annot = None
        self._tip_key = None
        VisualizationEngine(self.config).draw(
            self.ax, d['x'], d['fresnel_zones'], d['los'], d['distance_m'],
            d['tx_total'], d['rx_total'],
            d['obstacles'], d['results'],
            selected_idx=selected_idx,
            tx_building_height=d['tx_building_height'],
            rx_building_height=d['rx_building_height'],
            tx_antenna_extra=d['tx_antenna_extra'],
            rx_antenna_extra=d['rx_antenna_extra'],
            include_reflections=d['include_reflections'],
            clearance_factor=d['clearance_factor'],
        )
        self._create_tooltip_annot()
        self.apply_theme()
        self.canvas.draw()

    def redraw_with_selected_obstacle(self):
        if self.last_data is None:
            return
        selection = self.obstacle_tree.selection()
        selected_idx = None
        if selection:
            idx = self.obstacle_tree.index(selection[0])
            if idx < len(self.last_data['obstacles']):
                selected_idx = idx
        self._render_plot(selected_idx)

    def clear_results(self):
        self.results_box.delete(1.0, tk.END)
        self.ax.clear()
        self.tooltip_annot = None
        self._tip_key = None
        self.last_data = None
        self.apply_theme()
        self.canvas.draw()
        self.update_status("Resultados limpiados")

    def _create_tooltip_annot(self):
        self.tooltip_annot = self.ax.annotate(
            "", xy=(0, 0), xytext=(10, 10), textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="yellow", alpha=0.9, edgecolor="black"),
            arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
            fontsize=9, fontweight="bold", color="black"
        )
        self.tooltip_annot.set_visible(False)

    def on_hover(self, event):
        # Sin cálculo dibujado no hay tooltip
        if self.tooltip_annot is None or self.last_data is None:
            return
        if event.inaxes != self.ax or event.xdata is None or event.ydata is None:
            self._hide_tooltip()
            return
        x_mouse, y_mouse = event.xdata, event.ydata
        SENS_X = 80
        found = None
        for i, (obs, res) in enumerate(zip(self.last_data['obstacles'], self.last_data['results'])):
            if abs(obs.position - x_mouse) < SENS_X and 0 <= y_mouse <= obs.height + 2:
                found = (i, obs, res)
                break
        if found is None:
            self._hide_tooltip()
            return
        i, obs, res = found
        if self._tip_key == i:
            return   # ya visible: evita redibujar en cada movimiento
        self.tooltip_annot.xy = (obs.position, obs.height + 5)
        self.tooltip_annot.set_text(f"{obs.name}\n{res.diffraction_loss_db:.1f} dB")
        self.tooltip_annot.set_visible(True)
        self._tip_key = i
        self.canvas.draw_idle()

    def _hide_tooltip(self):
        if self._tip_key is not None and self.tooltip_annot is not None:
            self.tooltip_annot.set_visible(False)
            self._tip_key = None
            self.canvas.draw_idle()

    # ---------------------- Exportación y vistas ----------------------
    def export_report(self):
        if self.last_data is None:
            messagebox.showwarning("Advertencia", "No hay datos para exportar. Realice un cálculo primero.")
            return
        filepath = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if not filepath:
            return

        d = self.last_data
        b = d['budget']
        # Todos los valores provienen del último cálculo, no de los campos actuales
        results_data = {
            'frecuencia': d['frequency_ghz'],
            'distancia': d['distance_m'],
            'wavelength': d['wavelength'],
            'fresnel_radius': d['fmax'],
            'tx_building': d['tx_building_height'],
            'tx_antenna_extra': d['tx_antenna_extra'],
            'tx_total': d['tx_total'],
            'rx_building': d['rx_building_height'],
            'rx_antenna_extra': d['rx_antenna_extra'],
            'rx_total': d['rx_total'],
            'tx_power': b.tx_power_dbm,
            'tx_gain': b.tx_gain_dbi,
            'rx_gain': b.rx_gain_dbi,
            'rx_sensitivity': b.rx_sensitivity_dbm,
            'fsl': b.fsl_db,
            'total_diff_loss': b.diffraction_loss_db,
            'potencia_recibida': b.rx_power_dbm,
            'margen': b.margin_db,
            'reflection_factor_db': b.reflection_factor_db,
            'obstaculos': d['results']
        }

        try:
            from visualization_3d import Visualization3D
            fig_3d = Visualization3D(self.config).render_to_figure(
                d['x'], d['fresnel_zones'], d['los'], d['distance_m'],
                d['tx_total'], d['rx_total'],
                d['obstacles'], d['results'],
                d['tx_building_height'], d['rx_building_height'],
                d['tx_antenna_extra'], d['rx_antenna_extra'],
                elev=30, azim=-60
            )
            ExportService.generate_report(results_data, self.figure, filepath, figure_3d=fig_3d)
        except Exception as e:
            messagebox.showerror("Error al exportar", str(e))
            return
        self.update_status(f"Reporte exportado a {os.path.basename(filepath)}")

    def _on_mousewheel_zoom(self, event):
        """Zoom con rueda del ratón, evitando valores negativos en los ejes."""
        if event.inaxes != self.ax:
            return
        scale_factor = 1.1
        xdata, ydata = event.xdata, event.ydata
        if xdata is None or ydata is None:
            return

        cur_xlim = self.ax.get_xlim()
        cur_ylim = self.ax.get_ylim()

        if (hasattr(event, 'button') and event.button == 'up') or (hasattr(event, 'step') and event.step > 0):
            new_width = (cur_xlim[1] - cur_xlim[0]) / scale_factor
            new_height = (cur_ylim[1] - cur_ylim[0]) / scale_factor
        else:
            new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
            new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

        new_xlim = self._clamp_limits((xdata - new_width / 2, xdata + new_width / 2), 0)
        new_ylim = self._clamp_limits((ydata - new_height / 2, ydata + new_height / 2), 0)
        self.ax.set_xlim(new_xlim)
        self.ax.set_ylim(new_ylim)
        self.canvas.draw_idle()

    def open_3d_view(self):
        """Abre una ventana con la visualización 3D del último cálculo (bloqueante)."""
        if self.last_data is None:
            messagebox.showwarning("Advertencia", "No hay datos para visualizar en 3D. Realice un cálculo primero.")
            return

        # Import diferido: evita cargar mpl_toolkits al iniciar la aplicación
        from visualization_3d import Visualization3D

        d = self.last_data
        Visualization3D(self.config).draw(
            d['x'], d['fresnel_zones'], d['los'], d['distance_m'],
            d['tx_total'], d['rx_total'],
            d['obstacles'], d['results'],
            d['tx_building_height'], d['rx_building_height'],
            d['tx_antenna_extra'], d['rx_antenna_extra']
        )
        self.update_status("Vista 3D cerrada")

    def toggle_theme(self):
        """Cambia entre tema claro y oscuro y actualiza la gráfica."""
        self.theme = "light" if self.theme == "dark" else "dark"
        self.config["theme"] = self.theme
        if self.last_data:
            self.redraw_with_selected_obstacle()
        else:
            self.apply_theme()
        self.update_status(f"Tema cambiado a {self.theme}")

    def apply_theme(self):
        """Aplica los colores del tema a la figura y ejes."""
        if self.theme == "dark":
            self.figure.patch.set_facecolor("#0f1722")
            self.ax.set_facecolor("#0f1722")
            self.ax.tick_params(colors="white")
            self.ax.xaxis.label.set_color("white")
            self.ax.yaxis.label.set_color("white")
            self.ax.title.set_color("white")
            for spine in self.ax.spines.values():
                spine.set_color("white")
        else:
            self.figure.patch.set_facecolor("white")
            self.ax.set_facecolor("white")
            self.ax.tick_params(colors="black")
            self.ax.xaxis.label.set_color("black")
            self.ax.yaxis.label.set_color("black")
            self.ax.title.set_color("black")
            for spine in self.ax.spines.values():
                spine.set_color("black")
        self.canvas.draw_idle()

    def run(self):
        self.root.mainloop()
