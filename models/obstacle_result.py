"""
models/obstacle_result.py
=========================

Modelo de resultado de evaluación de obstáculos.
"""

from dataclasses import dataclass

@dataclass
class ObstacleResult:
    """
    Resultado del análisis de un obstáculo.

    Attributes:
        block_percent: penetración del obstáculo en el radio de la 1ª zona de
            Fresnel, en % (0 = sin intrusión, 100 = alcanza o supera la LOS).
        diffraction_loss_db: pérdida por difracción (filo de cuchillo), en dB.
        clearance_ratio: despeje = (altura LOS - altura obstáculo) / r1.
            >= 1 libre de la 1ª zona; 0 = el obstáculo toca la LOS;
            < 0 = el obstáculo la supera. Puede ser +-inf si r1 ~ 0.
    """
    index: int
    name: str
    position: float
    height: float
    block_percent: float
    state: str
    message: str
    diffraction_loss_db: float = 0.0
    clearance_ratio: float = 0.0
