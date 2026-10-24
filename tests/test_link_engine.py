"""
tests/test_link_engine.py
Pruebas para el motor de cálculo (integración entre Fresnel, obstáculos y reflexiones).
Modelo de tierra plana: no existe factor k ni curvatura.
"""

import numpy as np
import pytest
from link_engine import LinkEngine
from models.obstacle import Obstacle
from reflection_obstacle import reflection_factor, reflection_phasor, field_factor_db


@pytest.fixture
def config():
    """Configuración mínima para las pruebas."""
    return {
        "samples": 100,
        "clearance_acceptable": 0.6
    }


def test_link_engine_returns_seven_values(config):
    engine = LinkEngine(config)
    out = engine.compute(2.4e9, 1000, 50, 50, [])
    assert len(out) == 7


def test_link_engine_zones(config):
    engine = LinkEngine(config)
    _, zones, _, _, _, _, _ = engine.compute(2.4e9, 1000, 50, 50, [], n_zones=3)
    assert list(zones.keys()) == [1, 2, 3]
    assert np.allclose(zones[3], np.sqrt(3) * zones[1])


def test_link_engine_los_is_straight(config):
    engine = LinkEngine(config)
    _, _, _, _, _, los, _ = engine.compute(2.4e9, 1000, 80, 60, [])
    assert los[0] == pytest.approx(80)
    assert los[-1] == pytest.approx(60)
    # Línea recta: el punto medio es el promedio de las alturas
    assert los[len(los) // 2] == pytest.approx(70, abs=0.2)


def test_link_engine_no_curvature_for_long_links(config):
    """Con antenas iguales la LOS es horizontal aunque el enlace sea largo."""
    engine = LinkEngine(config)
    _, _, _, _, _, los, _ = engine.compute(2.4e9, 50000, 100, 100, [])
    assert np.allclose(los, 100.0)


def test_link_engine_rejects_k_factor(config):
    engine = LinkEngine(config)
    with pytest.raises(TypeError):
        engine.compute(2.4e9, 1000, 80, 80, [], k_factor=1.333)


def test_link_engine_with_obstacle(config):
    engine = LinkEngine(config)
    obs = Obstacle("Torre", 500, 60)
    _, _, _, _, results, _, _ = engine.compute(2.4e9, 1000, 80, 80, [obs])
    assert len(results) == 1
    assert results[0].name == "Torre"
    assert results[0].block_percent >= 0


def test_obstacle_outside_link_raises(config):
    engine = LinkEngine(config)
    obs = Obstacle("Fuera", 2500, 60)
    with pytest.raises(ValueError, match="Fuera"):
        engine.compute(2.4e9, 2000, 80, 65, [obs])


def test_obstacle_at_link_ends_is_accepted(config):
    engine = LinkEngine(config)
    obs = [Obstacle("Inicio", 0, 10), Obstacle("Final", 2000, 10)]
    _, _, _, _, results, _, _ = engine.compute(2.4e9, 2000, 80, 65, obs)
    assert len(results) == 2


def test_invalid_frequency_and_distance(config):
    engine = LinkEngine(config)
    with pytest.raises(ValueError):
        engine.compute(0, 1000, 50, 50, [])
    with pytest.raises(ValueError):
        engine.compute(2.4e9, 0, 50, 50, [])


def test_reflection_factor_is_zero_when_not_requested(config):
    engine = LinkEngine(config)
    obs = Obstacle("Edificio", 500, 60, reflectivity=0.8)
    *_, refl = engine.compute(2.4e9, 1000, 80, 80, [obs], include_reflections=False)
    assert refl == 0.0


def test_reflection_factor_zero_without_reflective_obstacles(config):
    engine = LinkEngine(config)
    obs = Obstacle("Mate", 500, 60, reflectivity=0.0)
    *_, refl = engine.compute(2.4e9, 1000, 80, 80, [obs], include_reflections=True)
    assert refl == 0.0


def test_reflection_single_obstacle_matches_module_function(config):
    engine = LinkEngine(config)
    obs = Obstacle("Edificio", 500, 60, reflectivity=0.8)
    wl = 3e8 / 2.4e9
    expected = reflection_factor(0, 1000, 500, 80, 80, 60, wl, 0.8)
    *_, refl = engine.compute(2.4e9, 1000, 80, 80, [obs], include_reflections=True)
    assert refl == pytest.approx(expected)


def test_reflection_two_obstacles_combine_coherently(config):
    """Dos reflejos se suman como fasores, no como potencias independientes."""
    engine = LinkEngine(config)
    wl = 3e8 / 2.4e9
    o1 = Obstacle("A", 400, 60, reflectivity=0.5)
    o2 = Obstacle("B", 700, 55, reflectivity=0.5)
    p1 = reflection_phasor(0, 1000, 400, 80, 80, 60, wl, 0.5)
    p2 = reflection_phasor(0, 1000, 700, 80, 80, 55, wl, 0.5)
    expected = field_factor_db([p1, p2])
    *_, refl = engine.compute(2.4e9, 1000, 80, 80, [o1, o2], include_reflections=True)
    assert refl == pytest.approx(expected)


def test_clearance_factor_comes_from_config_and_can_be_overridden(config):
    engine = LinkEngine(config)
    # LOS a 80 m, F1 máx = 5.6 m en el centro; obstáculo con despeje ~0.5·r1
    obs = Obstacle("O", 500, 80 - 0.5 * 5.59)
    _, _, _, _, res_default, _, _ = engine.compute(2.4e9, 1000, 80, 80, [obs])
    _, _, _, _, res_loose, _, _ = engine.compute(2.4e9, 1000, 80, 80, [obs], clearance_factor=0.3)
    assert res_default[0].state == "CRITICO"
    assert res_loose[0].state == "ACEPTABLE"


def test_default_clearance_when_config_has_no_key():
    engine = LinkEngine({"samples": 100})
    obs = Obstacle("O", 500, 40)
    _, _, _, _, res, _, _ = engine.compute(2.4e9, 1000, 80, 80, [obs])
    assert res[0].state == "ACEPTABLE"
