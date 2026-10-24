"""
examples/link_example.py
========================

Ejemplo de uso del motor de cálculo SIN interfaz gráfica (reemplaza al
antiguo t.py). Ejecutar desde la raíz del proyecto:

    python examples/link_example.py
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import matplotlib.pyplot as plt

from link_engine import LinkEngine
from link_budget import compute_link_budget
from models.obstacle import Obstacle
from visualization_engine import VisualizationEngine


def main():
    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as f:
        config = json.load(f)

    engine = LinkEngine(config)

    # Enlace de ejemplo (alturas TOTALES de antena sobre el suelo)
    freq_hz = 2.4e9
    dist = 2000.0
    tx_h = 80.0
    rx_h = 65.0
    obstaculos = [Obstacle("Edificio", 1000.0, 70.0)]

    x, zonas, fmax, wl, resultados, los, refl_db = engine.compute(
        freq_hz, dist, tx_h, rx_h, obstaculos, n_zones=3
    )

    budget = compute_link_budget(
        dist, freq_hz, tx_power_dbm=20, tx_gain_dbi=15, rx_gain_dbi=15,
        rx_sensitivity_dbm=-85,
        diffraction_loss_db=sum(r.diffraction_loss_db for r in resultados),
        reflection_factor_db=refl_db,
    )

    print("Longitud de onda:", wl, "m")
    print("Radio máximo F1:", fmax, "m")
    print("Zonas calculadas:", list(zonas.keys()))
    print("Resultado:", resultados[0].message)
    print(f"Potencia recibida: {budget.rx_power_dbm:.2f} dBm | margen: {budget.margin_db:.2f} dB")

    viz = VisualizationEngine(config)
    fig, ax = plt.subplots(figsize=(10, 6))
    viz.draw(ax, x, zonas, los, dist, tx_h, rx_h, obstaculos, resultados)
    plt.show()


if __name__ == "__main__":
    main()
