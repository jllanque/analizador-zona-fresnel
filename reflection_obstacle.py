"""
reflection_obstacle.py
======================

Modelo simplificado de reflexión en obstáculos (un rebote).

Cada obstáculo se trata como un punto reflector situado en su cima
(obs_pos, obs_height). El rayo reflejado recorre TX -> obstáculo -> RX y
se combina con el rayo directo. Es un modelo heurístico: no comprueba la
geometría especular ni corrige la amplitud por la mayor distancia recorrida.

Para varios obstáculos los fasores se suman COHERENTEMENTE con el rayo
directo:

    E_total = 1 + sum_i  R_i * exp(-j * phi_i)
    G [dB]  = 20 * log10(|E_total|)

con R_i = -reflectividad_i y phi_i = 2*pi*delta_i / lambda.
"""

import numpy as np

# Campo mínimo relativo (-120 dB) para evitar log10(0) en cancelaciones totales
_MIN_FIELD = 1e-6


def reflection_phasor(tx_pos, rx_pos, obs_pos, tx_height, rx_height, obs_height,
                      wavelength, reflectivity=1.0) -> complex:
    """
    Fasor del rayo reflejado en un obstáculo, relativo al rayo directo.

    Returns:
        R * exp(-j * 2*pi*delta/lambda), con R = -reflectivity.
    """
    if wavelength <= 0:
        raise ValueError("La longitud de onda debe ser mayor que cero.")

    tx = np.array([tx_pos, tx_height], dtype=float)
    rx = np.array([rx_pos, rx_height], dtype=float)
    obs = np.array([obs_pos, obs_height], dtype=float)

    d_direct = np.linalg.norm(rx - tx)
    d_reflect = np.linalg.norm(obs - tx) + np.linalg.norm(rx - obs)
    delta = d_reflect - d_direct

    # Signo negativo: inversión de fase típica en la reflexión
    R = -reflectivity
    phi = 2 * np.pi * delta / wavelength
    return complex(R * np.exp(-1j * phi))


def field_factor_db(phasors) -> float:
    """
    Factor (dB) del campo total respecto al rayo directo solo.

    Args:
        phasors: iterable de fasores de rayos reflejados (ver reflection_phasor).
    """
    total = abs(1 + sum(phasors))
    return float(20 * np.log10(max(total, _MIN_FIELD)))


def reflection_factor(tx_pos, rx_pos, obs_pos, tx_height, rx_height, obs_height,
                      wavelength, reflectivity=1.0):
    """
    Factor de ganancia/pérdida (dB) por la reflexión en UN obstáculo.
    Se modela como una trayectoria Tx -> obstáculo -> Rx.
    """
    phasor = reflection_phasor(tx_pos, rx_pos, obs_pos, tx_height, rx_height,
                               obs_height, wavelength, reflectivity)
    return field_factor_db([phasor])
