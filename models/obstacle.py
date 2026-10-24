"""
models/obstacle.py
==================

Modelo de obstáculo para el análisis
de la zona de Fresnel.
"""

from dataclasses import dataclass


@dataclass
class Obstacle:
    """
    Representa un obstáculo dentro
    del radioenlace.

    Attributes:
        name: identificador del obstáculo.
        position: distancia desde el transmisor (m).
        height: altura sobre el suelo (m).
        reflectivity: coeficiente de reflexión (0 = sin reflexión,
            1 = reflexión total). Es también el valor por defecto que
            usa el repositorio CSV cuando la columna no existe.
    """

    name: str
    position: float
    height: float
    reflectivity: float = 0.8
