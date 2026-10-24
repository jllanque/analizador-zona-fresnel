"""
tests/test_link_budget.py
Pruebas del módulo link_budget (sin GUI).
"""

import pytest
from link_budget import free_space_loss_db, compute_link_budget


def test_fsl_calculation():
    """Free Space Loss a 2 km y 5 GHz debe ser ~112.44 dB."""
    assert free_space_loss_db(2000.0, 5e9) == pytest.approx(112.44, abs=0.01)


def test_fsl_increases_6db_when_distance_doubles():
    assert free_space_loss_db(4000.0, 5e9) - free_space_loss_db(2000.0, 5e9) == pytest.approx(6.02, abs=0.01)


def test_received_power():
    b = compute_link_budget(2000.0, 5e9, 20, 15, 15, -85, diffraction_loss_db=31.55)
    assert b.fsl_db == pytest.approx(112.44, abs=0.01)
    assert b.rx_power_dbm == pytest.approx(-93.99, abs=0.01)
    assert b.margin_db == pytest.approx(-8.99, abs=0.01)


def test_margin_viability():
    b = compute_link_budget(2000.0, 5e9, 20, 15, 15, -85)
    assert b.margin_db > 0
    assert b.viable


def test_margin_non_viable():
    b = compute_link_budget(2000.0, 5e9, 20, 15, 15, -85, diffraction_loss_db=40)
    assert b.margin_db < 0
    assert not b.viable


def test_reflection_factor_is_added():
    base = compute_link_budget(2000.0, 5e9, 20, 15, 15, -85)
    refl = compute_link_budget(2000.0, 5e9, 20, 15, 15, -85, reflection_factor_db=-3.0)
    assert refl.rx_power_dbm == pytest.approx(base.rx_power_dbm - 3.0)


def test_invalid_inputs():
    with pytest.raises(ValueError):
        free_space_loss_db(0, 5e9)
    with pytest.raises(ValueError):
        free_space_loss_db(1000, 0)
