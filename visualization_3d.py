"""
visualization_3d.py
===================

Motor de visualización 3D para el radioenlace.
Sin superficies pesadas: líneas, anillos y prismas semitransparentes.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registra la proyección 3d)
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


class Visualization3D:
    """
    Genera una figura 3D del enlace.
    """

    LATERAL_WIDTH = 20.0

    STYLES = {
        1: {'color': 'blue', 'linestyle': '-', 'linewidth': 2, 'alpha': 0.8, 'label': 'Zona 1'},
        2: {'color': 'green', 'linestyle': '--', 'linewidth': 1.5, 'alpha': 0.7, 'label': None},
        3: {'color': 'orange', 'linestyle': ':', 'linewidth': 1.5, 'alpha': 0.6, 'label': None},
        4: {'color': 'purple', 'linestyle': '-.', 'linewidth': 1.5, 'alpha': 0.5, 'label': None},
        5: {'color': 'brown', 'linestyle': (0, (5, 5)), 'linewidth': 1.5, 'alpha': 0.5, 'label': None}
    }

    def __init__(self, config: dict):
        self.config = config
        self.theme = config.get("theme", "dark")

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def draw(self, x, fresnel_zones, los, distance_m,
             tx_total, rx_total, obstacles, results,
             tx_building_height, rx_building_height,
             tx_antenna_extra, rx_antenna_extra):
        """Dibuja el radioenlace en 3D en una ventana interactiva (bloqueante)."""
        fig = plt.figure(figsize=(12, 8))
        self._populate(fig, x, fresnel_zones, los, distance_m, tx_total, rx_total,
                       obstacles, results, tx_building_height, rx_building_height,
                       title="Vista 3D del Radioenlace - Zonas de Fresnel",
                       text_size=8, legend_size=9)
        fig.tight_layout()
        plt.show()

    def render_to_figure(self, x, fresnel_zones, los, distance_m,
                         tx_total, rx_total, obstacles, results,
                         tx_building_height, rx_building_height,
                         tx_antenna_extra, rx_antenna_extra,
                         elev=25, azim=-60):
        """
        Genera la figura 3D sin mostrarla en pantalla y la retorna.

        Usa un Figure con canvas Agg propio: no toca pyplot ni el backend
        global, por lo que es seguro invocarlo con la GUI Tk abierta.
        """
        fig = Figure(figsize=(10, 7))
        FigureCanvasAgg(fig)
        ax = self._populate(fig, x, fresnel_zones, los, distance_m, tx_total, rx_total,
                            obstacles, results, tx_building_height, rx_building_height,
                            title="Vista 3D del Radioenlace",
                            text_size=7, legend_size=8)
        ax.view_init(elev=elev, azim=azim)
        return fig

    # ------------------------------------------------------------------
    # Construcción común de la escena
    # ------------------------------------------------------------------
    def _state_color(self, state):
        if state == "ACEPTABLE":
            color = self.config["acceptable_color"]
        elif state == "CRITICO":
            color = self.config["critical_color"]
        else:
            color = self.config["non_viable_color"]
        return tuple(color) if isinstance(color, list) else color

    def _populate(self, fig, x, fresnel_zones, los, distance_m,
                  tx_total, rx_total, obstacles, results,
                  tx_building_height, rx_building_height,
                  title, text_size, legend_size):
        ax = fig.add_subplot(111, projection='3d')
        ax.set_title(title)
        ax.set_xlabel("Distancia [m]")
        ax.set_ylabel("Desplazamiento lateral [m]")
        ax.set_zlabel("Altura [m]")

        lateral_width = self.LATERAL_WIDTH
        zeros = np.zeros_like(x)

        # 1. Línea de vista (LOS)
        ax.plot(x, zeros, los, 'r--', linewidth=2, label="Línea de Vista")

        # 2. Zonas de Fresnel
        for n, fresnel in fresnel_zones.items():
            style = self.STYLES.get(n, self.STYLES[1])
            ax.plot(x, zeros, los + fresnel, color=style['color'], linestyle=style['linestyle'],
                    linewidth=style['linewidth'], alpha=style['alpha'], label=style['label'])
            ax.plot(x, zeros, los - fresnel, color=style['color'], linestyle=style['linestyle'],
                    linewidth=style['linewidth'], alpha=style['alpha'])
            if n == 1:
                self._draw_fresnel_mesh(ax, x, fresnel, los, style['color'])

        # 3. Edificios y antenas
        building_width = distance_m * self.config["building_width_ratio"]
        obstacle_width = distance_m * self.config["obstacle_width_ratio"]

        self._draw_prism_solid(ax, 0, -lateral_width / 2, 0,
                               building_width, lateral_width, tx_building_height,
                               self.config["tx_building_color"], alpha=0.6)
        tx_ant_x = building_width / 2
        ax.plot([tx_ant_x, tx_ant_x], [0, 0], [tx_building_height, tx_total],
                color='black', linewidth=3)
        ax.scatter([tx_ant_x], [0], [tx_total], color='red', s=50, label="Antena TX")

        self._draw_prism_solid(ax, distance_m - building_width, -lateral_width / 2, 0,
                               building_width, lateral_width, rx_building_height,
                               self.config["rx_building_color"], alpha=0.6)
        rx_ant_x = distance_m - building_width / 2
        ax.plot([rx_ant_x, rx_ant_x], [0, 0], [rx_building_height, rx_total],
                color='black', linewidth=3)
        ax.scatter([rx_ant_x], [0], [rx_total], color='blue', s=50, label="Antena RX")

        # 4. Obstáculos (prismas semitransparentes con etiquetas)
        text_color = 'black' if self.theme == 'light' else 'white'
        for obs, res in zip(obstacles, results):
            color = self._state_color(res.state)
            self._draw_prism_solid(ax, obs.position - obstacle_width / 2,
                                   -lateral_width / 4, 0,
                                   obstacle_width, lateral_width / 2, obs.height,
                                   color, alpha=0.5)
            ax.text(obs.position, lateral_width / 2 + 2, obs.height + 2,
                    f"{obs.name}\n{obs.height:.1f}m",
                    fontsize=text_size, ha='center', va='bottom',
                    bbox=dict(boxstyle="round,pad=0.2", facecolor=color, alpha=0.7),
                    color=text_color)

        # Límites
        ax.set_xlim([0, distance_m])
        max_height = max(tx_total, rx_total,
                         max([obs.height for obs in obstacles], default=0))
        ax.set_zlim([0, max_height + self.config.get("plot_margin", 50)])
        ax.set_ylim([-lateral_width, lateral_width])
        ax.legend(loc='upper right', fontsize=legend_size)
        return ax

    @staticmethod
    def _draw_fresnel_mesh(ax, x, fresnel, los, color):
        """
        Malla ligera del volumen de la 1ª zona: anillos circulares en
        secciones transversales y generatrices longitudinales.
        Cada punto de la sección es (y, z) = (r*cos θ, l + r*sin θ).
        """
        n_secciones = min(20, len(x))
        indices = np.linspace(0, len(x) - 1, n_secciones, dtype=int)
        x_malla = x[indices]
        r_malla = fresnel[indices]
        los_malla = los[indices]
        theta = np.linspace(0, 2 * np.pi, 33)

        for xi, ri, li in zip(x_malla, r_malla, los_malla):
            ax.plot(xi * np.ones_like(theta), ri * np.cos(theta), li + ri * np.sin(theta),
                    color=color, linewidth=0.5, alpha=0.3)

        for ang in np.linspace(0, 2 * np.pi, 8, endpoint=False):
            ax.plot(x_malla, r_malla * np.cos(ang), los_malla + r_malla * np.sin(ang),
                    color=color, linewidth=0.5, alpha=0.2)

    @staticmethod
    def _draw_prism_solid(ax, x0, y0, z0, dx, dy, dz, color, alpha=0.5):
        """Dibuja un prisma rectangular con caras semitransparentes."""
        x = [x0, x0 + dx, x0 + dx, x0, x0, x0 + dx, x0 + dx, x0]
        y = [y0, y0, y0 + dy, y0 + dy, y0, y0, y0 + dy, y0 + dy]
        z = [z0, z0, z0, z0, z0 + dz, z0 + dz, z0 + dz, z0 + dz]

        faces = [
            [0, 1, 2, 3],  # inferior
            [4, 5, 6, 7],  # superior
            [0, 1, 5, 4],  # lateral y=y0
            [2, 3, 7, 6],  # lateral y=y0+dy
            [0, 3, 7, 4],  # lateral x=x0
            [1, 2, 6, 5]   # lateral x=x0+dx
        ]
        verts = [[(x[i], y[i], z[i]) for i in face] for face in faces]
        collection = Poly3DCollection(verts, facecolor=color, alpha=alpha,
                                      linewidths=0.5, edgecolors='black')
        ax.add_collection3d(collection)
