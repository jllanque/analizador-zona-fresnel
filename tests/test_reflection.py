"""
tests/test_reflection.py
Pruebas del modelo de reflexión en obstáculos (fasores).
"""

import numpy as np
import pytest
from reflection_obstacle import reflection_phasor, field_factor_db, reflection_factor

D = 1000.0
H = 50.0
OBS_Y = 100.0   # obstáculo a mitad del enlace, 50 m sobre las antenas


def _delta():
    d_direct = D
    d_reflect = 2 * np.hypot(D / 2, OBS_Y - H)
    return d_reflect - d_direct


def test_in_phase_reflection_with_full_wavelength_difference():
    """delta = lambda -> fasor = -rho -> factor = 20*log10(1 - rho)."""
    wl = _delta()
    f = reflection_factor(0, D, D / 2, H, H, OBS_Y, wl, 0.5)
    assert f == pytest.approx(20 * np.log10(0.5), abs=1e-6)


def test_half_wavelength_difference_is_constructive():
    """delta = lambda/2 -> fasor = +rho -> factor = 20*log10(1 + rho)."""
    wl = 2 * _delta()
    f = reflection_factor(0, D, D / 2, H, H, OBS_Y, wl, 0.5)
    assert f == pytest.approx(20 * np.log10(1.5), abs=1e-6)


def test_two_identical_reflections_add_as_phasors():
    wl = 2 * _delta()
    p = reflection_phasor(0, D, D / 2, H, H, OBS_Y, wl, 0.5)
    # |1 + 0.5 + 0.5| = 2 -> 6.02 dB (con suma de potencias sería 6.53 dB)
    assert field_factor_db([p, p]) == pytest.approx(20 * np.log10(2.0), abs=1e-6)


def test_total_cancellation_is_finite():
    wl = _delta()
    f = reflection_factor(0, D, D / 2, H, H, OBS_Y, wl, 1.0)
    assert np.isfinite(f)
    assert f <= -100


def test_zero_reflectivity_has_no_effect():
    f = reflection_factor(0, D, D / 2, H, H, OBS_Y, 0.125, 0.0)
    assert f == pytest.approx(0.0, abs=1e-9)


def test_invalid_wavelength():
    with pytest.raises(ValueError):
        reflection_phasor(0, D, D / 2, H, H, OBS_Y, 0.0, 0.5)
