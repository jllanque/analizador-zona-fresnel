"""
tests/test_obstacle_checker.py
Pruebas para la verificación de obstáculos: despeje, clasificación y difracción.
Modelo de tierra plana (sin curvatura).
"""

import numpy as np
import pytest
from models.obstacle import Obstacle
from obstacle_checker import ObstacleChecker


def _flat_checker(**kwargs):
    """Enlace de 1 km, antenas a 50 m y radio de Fresnel constante de 10 m."""
    x = np.linspace(0, 1000, 101)
    fresnel = np.full_like(x, 10.0)
    fresnel[0] = 0
    fresnel[-1] = 0
    return ObstacleChecker(x, fresnel, 1000.0, 50.0, 50.0, wavelength=0.125, **kwargs)


def _state_at_clearance(c, **kwargs):
    """Estado de un obstáculo cuyo despeje es c·r1 (r1 = 10 m, LOS = 50 m)."""
    checker = _flat_checker(**kwargs)
    return checker.check([Obstacle("T", 500.0, 50.0 - c * 10.0)])[0]


def test_no_obstruction():
    """Obstáculo muy por debajo de la LOS → sin penetración, sin pérdida."""
    r = _flat_checker().check([Obstacle("Bajo", 500.0, 5.0)])[0]
    assert r.block_percent == 0.0
    assert r.diffraction_loss_db == 0.0
    assert r.state == "ACEPTABLE"
    assert r.clearance_ratio == pytest.approx(4.5)


def test_full_obstruction():
    """Obstáculo sobre la LOS → 100 % de penetración, NO VIABLE, pérdida alta."""
    r = _flat_checker().check([Obstacle("Alto", 500.0, 100.0)])[0]
    assert r.block_percent == 100.0
    assert r.state == "NO VIABLE"
    assert r.clearance_ratio < 0
    assert r.diffraction_loss_db > 20


def test_classification_by_clearance():
    """ACEPTABLE si c >= 0.6; CRITICO si 0 < c < 0.6; NO VIABLE si c <= 0."""
    assert _state_at_clearance(0.7).state == "ACEPTABLE"
    assert _state_at_clearance(0.61).state == "ACEPTABLE"
    assert _state_at_clearance(0.59).state == "CRITICO"
    assert _state_at_clearance(0.3).state == "CRITICO"
    assert _state_at_clearance(0.01).state == "CRITICO"
    assert _state_at_clearance(0.0).state == "NO VIABLE"
    assert _state_at_clearance(-0.5).state == "NO VIABLE"


def test_block_percent_is_penetration():
    """Con c = 0.6 la penetración en r1 es 40 %."""
    assert _state_at_clearance(0.6).block_percent == pytest.approx(40.0)
    assert _state_at_clearance(0.25).block_percent == pytest.approx(75.0)


def test_custom_clearance_threshold():
    """El umbral de despeje aceptable es configurable."""
    assert _state_at_clearance(0.4, clearance_acceptable=0.3).state == "ACEPTABLE"
    assert _state_at_clearance(0.4, clearance_acceptable=0.8).state == "CRITICO"


def test_zero_fresnel_radius_near_terminals():
    """Con r1 = 0 (extremos) la clasificación depende solo de la LOS."""
    checker = _flat_checker()
    below = checker.check([Obstacle("A", 0.0, 10.0)])[0]
    above = checker.check([Obstacle("B", 0.0, 60.0)])[0]
    assert below.state == "ACEPTABLE" and below.block_percent == 0.0
    assert above.state == "NO VIABLE" and above.block_percent == 100.0


def test_knife_edge_loss_reference_values():
    """
    Valores de la aproximación P.526 frente a la integral de Fresnel exacta
    (J = -20·log10|F(nu)|): 6.02, 13.86, 19.09, 22.52, 26.94 y 32.95 dB.
    """
    exact = {0.0: 6.021, 1.0: 13.864, 2.0: 19.091, 3.0: 22.522, 5.0: 26.936, 10.0: 32.954}
    for nu, value in exact.items():
        assert ObstacleChecker.knife_edge_loss(nu) == pytest.approx(value, abs=0.15)


def test_knife_edge_loss_is_zero_below_threshold_and_continuous():
    assert ObstacleChecker.knife_edge_loss(-1.0) == 0.0
    assert ObstacleChecker.knife_edge_loss(-0.78) == 0.0
    # Sin salto en el umbral: justo por encima la pérdida es ~0 dB
    assert ObstacleChecker.knife_edge_loss(-0.77) == pytest.approx(0.0, abs=0.1)


def test_knife_edge_loss_is_monotonic():
    values = [ObstacleChecker.knife_edge_loss(nu) for nu in np.linspace(-0.7, 10, 60)]
    assert all(b >= a for a, b in zip(values, values[1:]))


def test_diffraction_loss_with_obstacle():
    """Un obstáculo que penetra la zona debe producir pérdida positiva."""
    x = np.linspace(0, 2000, 100)
    wavelength = 0.125
    d1 = x
    d2 = 2000 - x
    fresnel = np.sqrt(wavelength * d1 * d2 / (d1 + d2))
    fresnel[0] = 0
    fresnel[-1] = 0
    checker = ObstacleChecker(x, fresnel, 2000, 80, 80, wavelength=wavelength)
    idx_centro = len(x) // 2
    altura_obs = checker.los[idx_centro] - fresnel[idx_centro] + 5   # intrusión de 5 m
    obs = Obstacle("Test", x[idx_centro], altura_obs)
    assert checker.check([obs])[0].diffraction_loss_db > 0


def test_result_independent_of_grid_resolution():
    """Interpolar r1 hace que la malla (1000 vs 40000 puntos) apenas afecte."""
    wl, dist = 0.0625, 2000.0
    out = []
    for n in (1000, 40000):
        x = np.linspace(0, dist, n)
        fresnel = np.sqrt(wl * x * (dist - x) / dist)
        checker = ObstacleChecker(x, fresnel, dist, 160, 130, wavelength=wl)
        out.append(checker.check([Obstacle("O", 777.7, 140.0)])[0])
    assert out[0].clearance_ratio == pytest.approx(out[1].clearance_ratio, rel=1e-3)
    assert out[0].diffraction_loss_db == pytest.approx(out[1].diffraction_loss_db, abs=0.05)


def test_los_is_straight_line():
    """La LOS es la recta entre las puntas de antena (sin curvatura)."""
    x = np.linspace(0, 50000, 200)
    fresnel = np.zeros_like(x)
    checker = ObstacleChecker(x, fresnel, 50000, 150, 150, wavelength=0.1)
    assert np.allclose(checker.los, 150.0)
    checker2 = ObstacleChecker(x, fresnel, 50000, 100, 200, wavelength=0.1)
    assert checker2.los[0] == pytest.approx(100)
    assert checker2.los[-1] == pytest.approx(200)


def test_curvature_parameter_removed():
    """El modelo ya no admite k_factor."""
    x = np.linspace(0, 1000, 10)
    with pytest.raises(TypeError):
        ObstacleChecker(x, np.zeros_like(x), 1000, 50, 50, k_factor=1.333)


def test_invalid_arguments_raise():
    x = np.linspace(0, 1000, 10)
    with pytest.raises(ValueError):
        ObstacleChecker(x, np.zeros_like(x), 0, 50, 50)
    with pytest.raises(ValueError):
        ObstacleChecker(x, np.zeros_like(x), 1000, 50, 50, clearance_acceptable=0)
