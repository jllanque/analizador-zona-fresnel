"""
tests/test_visualization.py
Pruebas básicas de visualización (sin mostrar ventanas).
"""

import matplotlib.pyplot as plt
import numpy as np
import pytest
from visualization_engine import VisualizationEngine

@pytest.fixture
def config():
    return {
        "building_width_ratio": 0.04,
        "obstacle_width_ratio": 0.025,
        "plot_margin": 50,
        "tx_building_color": [0.4,0.4,0.4],
        "rx_building_color": [0.4,0.4,0.4],
        "acceptable_color": [0,0.7,0],
        "critical_color": [1,0.7,0],
        "non_viable_color": [1,0,0]
    }

def test_draw_no_crash(config):
    """Verifica que draw no lanza excepciones con datos mínimos."""
    fig, ax = plt.subplots()
    x = np.linspace(0, 1000, 50)
    fresnel_zones = {1: np.full_like(x, 10)}
    los = np.linspace(50, 50, len(x))
    engine = VisualizationEngine(config)
    engine.draw(ax, x, fresnel_zones, los, 1000, 50, 50, [], [])
    plt.close(fig)
    # Si llegamos aquí, no hubo excepción
    assert True