"""
visualization_engine.py
=======================

Motor de visualización del radioenlace.
Soporta dibujo de múltiples zonas de Fresnel (n=1..N) y anotaciones dinámicas escaladas.
"""

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np
import matplotlib.cm as cm

class VisualizationEngine:
    """
    Motor gráfico del análisis de zona de Fresnel.
    """

    def __init__(self, config: dict):
        self.config = config

    def draw(self, ax, x, fresnel_zones, los, distance_m, tx_antenna_total, rx_antenna_total,
            obstacles, results, selected_idx=None, tx_building_height=None, rx_building_height=None,
            tx_antenna_extra=None, rx_antenna_extra=None, include_reflections=False,
            clearance_factor=0.6):
        """
        Dibuja el radioenlace con múltiples zonas de Fresnel.

        Args:
            include_reflections: Si es True, dibuja la trayectoria reflejada en cada obstáculo.
        """
        ax.clear()
        ax.grid(True)

        # ===== AQUÍ =====
        if tx_building_height is None:
            tx_building_height = 0
        if rx_building_height is None:
            rx_building_height = 0
        # ================

        # Parámetros gráficos
        building_width = distance_m * self.config["building_width_ratio"]
        obstacle_width = distance_m * self.config["obstacle_width_ratio"]

        scale_factor = max(0.3, min(1.0, distance_m / 5000.0))
        x_offset = 15 * scale_factor
        y_offset = 5 * scale_factor

        # Dibujar edificios
        tx_building = Rectangle((0, 0), building_width, tx_building_height,
                                facecolor=self.config["tx_building_color"])
        ax.add_patch(tx_building)

        rx_building = Rectangle((distance_m - building_width, 0), building_width, rx_building_height,
                                facecolor=self.config["rx_building_color"])
        ax.add_patch(rx_building)

        # Posición de las antenas
        x1 = building_width / 2
        y1 = tx_antenna_total
        x2 = distance_m - building_width / 2
        y2 = rx_antenna_total

        # Línea de vista (LOS)
        ax.plot(x, los, 'r--', linewidth=2, label="Línea de Vista")

        styles = {
            1: {'color': 'blue', 'linestyle': '-', 'linewidth': 2, 'alpha': 0.25, 'fill': True},
            2: {'color': 'green', 'linestyle': '--', 'linewidth': 1.5, 'alpha': 0.2, 'fill': False},
            3: {'color': 'orange', 'linestyle': ':', 'linewidth': 1.5, 'alpha': 0.15, 'fill': False},
            4: {'color': 'purple', 'linestyle': '-.', 'linewidth': 1.5, 'alpha': 0.1, 'fill': False},
            5: {'color': 'brown', 'linestyle': (0, (5, 5)), 'linewidth': 1.5, 'alpha': 0.1, 'fill': False}
        }

        for n, fresnel in fresnel_zones.items():
            style = styles.get(n, styles[1])
            color = style['color']
            ls = style['linestyle']
            lw = style['linewidth']
            alpha = style['alpha']

            # Curvas de Fresnel
            ax.plot(x, los + fresnel, color=color, linestyle=ls, linewidth=lw,
                    label=f"Zona {n} (F{n})" if n == 1 else "")
            ax.plot(x, los - fresnel, color=color, linestyle=ls, linewidth=lw)

            # Relleno de la primera zona (solo para n=1)
            if style.get('fill', False):
                ax.fill_between(x, los - fresnel, los + fresnel, color=color, alpha=alpha)

            # --- ZONA DE DESPEJAMIENTO (solo para n=1) ---
            if n == 1:
                # Calcular curvas superior e inferior de la zona de despejamiento
                upper_clearance = los + clearance_factor * fresnel
                lower_clearance = los - clearance_factor * fresnel

                # Relleno de la zona de despejamiento (verde semitransparente)
                ax.fill_between(x, lower_clearance, upper_clearance,
                                color='green', alpha=0.15, label=f'Zona despejamiento ({clearance_factor:.2f}·r₁)')

                # Líneas de borde (verde oscuro, discontinuas)
                ax.plot(x, upper_clearance, 'g--', linewidth=1.5, alpha=0.7)
                ax.plot(x, lower_clearance, 'g--', linewidth=1.5, alpha=0.7,
                        label=f'{clearance_factor:.2f}·r₁ (despejamiento)')
                
        # ==========================
        # DIBUJO DE REFLEXIONES (nuevo)
        # ==========================
        if include_reflections:
            # Coordenadas TX y RX (puntos de las antenas)
            tx_x = building_width / 2
            tx_y = tx_antenna_total
            rx_x = distance_m - building_width / 2
            rx_y = rx_antenna_total

            for obstacle, result in zip(obstacles, results):
                # Verificar si el obstáculo tiene reflectividad > 0
                if hasattr(obstacle, 'reflectivity') and obstacle.reflectivity > 0:
                    obs_x = obstacle.position
                    obs_y = obstacle.height

                    # Dibujar trayectoria reflejada: TX -> Obstáculo -> RX
                    ax.plot([tx_x, obs_x], [tx_y, obs_y], 'b-.', linewidth=1.5, alpha=0.7,
                            label='Reflexión' if obstacle == obstacles[0] else "")
                    ax.plot([obs_x, rx_x], [obs_y, rx_y], 'b-.', linewidth=1.5, alpha=0.7)

                    # Marcar punto de reflexión en el obstáculo
                    ax.plot(obs_x, obs_y, 'go', markersize=8, alpha=0.8)
                    ax.text(obs_x, obs_y + 5, f'Reflejo en {obstacle.name}',
                            fontsize=7, ha='center', va='bottom',
                            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))

                    # Añadir etiqueta en la leyenda (solo una vez)
                    if obstacle == obstacles[0]:
                        ax.plot([], [], 'b-.', linewidth=1.5, label='Reflexión en obstáculo')

        # Obstáculos (sin cambios)
        for obstacle, result in zip(obstacles, results):
            state = result.state
            if state == "ACEPTABLE":
                color = self.config["acceptable_color"]
            elif state == "CRITICO":
                color = self.config["critical_color"]
            else:
                color = self.config["non_viable_color"]

            obs_rect = Rectangle(
                (obstacle.position - obstacle_width / 2, 0),
                obstacle_width,
                obstacle.height,
                facecolor=color
            )
            ax.add_patch(obs_rect)

        # Anotaciones para obstáculo seleccionado
        if selected_idx is not None and 0 <= selected_idx < len(obstacles):
            self._draw_annotations(ax, x, los, fresnel_zones[1],
                                   obstacles[selected_idx], results[selected_idx],
                                   x_offset, y_offset)

        # ==================================================
        # DIBUJO DE ANTENAS TIPO YAGI (3 elementos)
        # ==================================================
        def draw_yagi(ax, x, y_base, y_antenna, label):
            """Dibuja una antena Yagi simplificada en la posición (x, y_antenna)."""
            if y_antenna <= y_base:
                ax.plot(x, y_antenna, 'ko', markersize=4)
                ax.text(x, y_antenna + 2, label, ha='center', fontsize=9, fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='black', alpha=0.7))
                return

            ax.plot([x, x], [y_base, y_antenna], color='#555555', linewidth=2, solid_capstyle='round')

            reflector_len = 3.0
            driven_len = 2.0
            director_len = 1.5
            spacing = 1.2

            ax.plot([x - reflector_len/2, x + reflector_len/2], [y_antenna, y_antenna],
                    color='black', linewidth=2, solid_capstyle='round')
            ax.plot([x - director_len/2, x + director_len/2], [y_antenna + spacing, y_antenna + spacing],
                    color='black', linewidth=1.5, solid_capstyle='round')
            circle = plt.Circle((x, y_antenna - 0.2), driven_len/2.5,
                                facecolor='#DDDDDD', edgecolor='black', linewidth=1.2)
            ax.add_patch(circle)
            ax.plot([x - driven_len/2, x + driven_len/2], [y_antenna - 0.2, y_antenna - 0.2],
                    color='black', linewidth=2, solid_capstyle='round')
            ax.plot([x, x], [y_antenna - 0.2, y_antenna], color='#555555', linewidth=1, linestyle=':')

            ax.text(x, y_antenna + spacing + 1.2, label, ha='center', fontsize=9, fontweight='bold',
                    color='white', bbox=dict(boxstyle='round,pad=0.2', facecolor='black', alpha=0.7))

        draw_yagi(ax, x1, tx_building_height, tx_antenna_total, 'TX')
        draw_yagi(ax, x2, rx_building_height, rx_antenna_total, 'RX')

        ax.set_xlabel("Distancia [m]")
        ax.set_ylabel("Altura [m]")
        ax.set_title("Análisis de Zona de Fresnel")
        ax.legend(loc="best", fontsize=8)

        ax.set_xlim([0, distance_m])
        max_height = max([tx_antenna_total, rx_antenna_total] + [obs.height for obs in obstacles])
        ax.set_ylim([0, max_height + self.config["plot_margin"]])

    def _draw_annotations(self, ax, x, los, fresnel, obstacle, result, x_offset, y_offset):
        idx = np.argmin(np.abs(x - obstacle.position))
        x_obs = x[idx]
        los_at = los[idx]
        fresnel_at = fresnel[idx]
        y_lower = los_at - fresnel_at
        y_obs = obstacle.height
        penetracion = y_obs > y_lower

        sep_r1 = 28.0 * x_offset
        sep_h = 7.0 * x_offset

        if 0 < x_obs < x[-1]:
            mid_r = (los_at + y_lower) / 2
            ax.annotate('', xy=(x_obs - x_offset, los_at), xytext=(x_obs - x_offset, y_lower),
                        arrowprops=dict(arrowstyle='<->', color='blue', lw=1.5))
            ax.annotate('$r_1$',
                        xy=(x_obs - x_offset, mid_r), xycoords='data',
                        xytext=(x_obs - x_offset - sep_r1, mid_r), textcoords='data',
                        fontsize=9, color='blue',
                        arrowprops=dict(arrowstyle='-', color='gray', lw=0.8, alpha=0.7))

        if penetracion:
            mid_h = (y_lower + y_obs) / 2
            ax.annotate('', xy=(x_obs + x_offset, y_lower), xytext=(x_obs + x_offset, y_obs),
                        arrowprops=dict(arrowstyle='<->', color='red', lw=1.5))
            ax.annotate('$h$',
                        xy=(x_obs + x_offset, mid_h), xycoords='data',
                        xytext=(x_obs + x_offset + sep_h, mid_h), textcoords='data',
                        fontsize=9, color='red',
                        arrowprops=dict(arrowstyle='-', color='gray', lw=0.8, alpha=0.7))