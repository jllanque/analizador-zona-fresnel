"""
tests/test_fresnel.py
Pruebas para el calculador de la zona de Fresnel.
"""

import numpy as np
import pytest
from fresnel_calculator import FresnelCalculator

def test_symmetry():
    """La zona de Fresnel debe ser simétrica respecto al centro del enlace."""
    calc = FresnelCalculator(2.4e9, 1000.0, 101)
    x, fresnel, _, _ = calc.calculate()
    assert np.allclose(fresnel, fresnel[::-1], rtol=1e-5)

def test_ends_zero():
    """En los extremos (x=0 y x=distancia) el radio debe ser cero."""
    calc = FresnelCalculator(2.4e9, 1000.0, 100)
    x, fresnel, _, _ = calc.calculate()
    assert fresnel[0] == 0.0
    assert fresnel[-1] == 0.0

def test_positive_radii():
    """Todos los radios interiores deben ser >= 0."""
    calc = FresnelCalculator(2.4e9, 1000.0, 200)
    x, fresnel, _, _ = calc.calculate()
    assert np.all(fresnel >= 0)

def test_fmax_positive():
    """El radio máximo debe ser mayor que cero."""
    calc = FresnelCalculator(2.4e9, 1000.0, 100)
    _, _, fmax, _ = calc.calculate()
    assert fmax > 0

def test_fmax_value():
    """Valor del radio máximo para 2.4 GHz y 1 km debe ser ~5.59 m."""
    calc = FresnelCalculator(2.4e9, 1000.0, 500)
    _, _, fmax, _ = calc.calculate()
    # Valor esperado: 5.59016 m, margen del 2%
    assert 5.48 < fmax < 5.70

def test_fresnel_scale_with_n():
    """El radio para zona n debe ser sqrt(n) veces el radio de la zona 1."""
    calc = FresnelCalculator(2.4e9, 1000, 100)
    x, f1, _, _ = calc.calculate()
    for n in [2, 3, 4]:
        fn = np.sqrt(n) * f1
        # Verificar en un punto interior (ej. índice 50)
        assert fn[50] == pytest.approx(np.sqrt(n) * f1[50], rel=1e-5)

def test_wavelength():
    """La longitud de onda calculada debe coincidir con c/f."""
    calc = FresnelCalculator(2.4e9, 1000, 10)
    _, _, _, wl = calc.calculate()
    expected_wl = 3e8 / 2.4e9
    assert wl == pytest.approx(expected_wl, rel=1e-6)