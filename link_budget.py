"""
link_budget.py
==============

Presupuesto de enlace (link budget) sin dependencias de GUI.

    P_rx = P_tx + G_tx + G_rx - FSL - L_difracción + G_reflexión
    margen = P_rx - sensibilidad

No incluye pérdidas de cable, atmosféricas ni de polarización.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class LinkBudget:
    """Resultado del presupuesto de enlace (todo en dB / dBm / dBi)."""
    distance_m: float
    frequency_hz: float
    tx_power_dbm: float
    tx_gain_dbi: float
    rx_gain_dbi: float
    rx_sensitivity_dbm: float
    fsl_db: float
    diffraction_loss_db: float
    reflection_factor_db: float
    rx_power_dbm: float
    margin_db: float

    @property
    def viable(self) -> bool:
        return self.margin_db >= 0


def free_space_loss_db(distance_m: float, frequency_hz: float) -> float:
    """
    Pérdida en espacio libre: 20*log10(d[km]) + 20*log10(f[MHz]) + 32.44.
    """
    if distance_m <= 0:
        raise ValueError("La distancia debe ser mayor que cero.")
    if frequency_hz <= 0:
        raise ValueError("La frecuencia debe ser mayor que cero.")
    distance_km = distance_m / 1000.0
    frequency_mhz = frequency_hz / 1e6
    return float(20 * np.log10(distance_km) + 20 * np.log10(frequency_mhz) + 32.44)


def compute_link_budget(distance_m: float, frequency_hz: float,
                        tx_power_dbm: float, tx_gain_dbi: float,
                        rx_gain_dbi: float, rx_sensitivity_dbm: float,
                        diffraction_loss_db: float = 0.0,
                        reflection_factor_db: float = 0.0) -> LinkBudget:
    """Calcula el presupuesto de enlace completo."""
    fsl = free_space_loss_db(distance_m, frequency_hz)
    rx_power = (tx_power_dbm + tx_gain_dbi + rx_gain_dbi
                - fsl - diffraction_loss_db + reflection_factor_db)
    return LinkBudget(
        distance_m=distance_m,
        frequency_hz=frequency_hz,
        tx_power_dbm=tx_power_dbm,
        tx_gain_dbi=tx_gain_dbi,
        rx_gain_dbi=rx_gain_dbi,
        rx_sensitivity_dbm=rx_sensitivity_dbm,
        fsl_db=fsl,
        diffraction_loss_db=diffraction_loss_db,
        reflection_factor_db=reflection_factor_db,
        rx_power_dbm=rx_power,
        margin_db=rx_power - rx_sensitivity_dbm,
    )
