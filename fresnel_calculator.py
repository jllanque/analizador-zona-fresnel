"""
fresnel_calculator.py
=====================

Cálculo de la primera zona de Fresnel
para un radioenlace.

Implementa:
    - Longitud de onda
    - Primera zona de Fresnel
    - Radio máximo Fresnel
"""

import numpy as np


class FresnelCalculator:
    """
    Encapsula todos los cálculos
    relacionados con la zona de Fresnel.
    """

    def __init__(
        self,
        frequency_hz: float,
        distance_m: float,
        samples: int = 1000
    ):
        self.frequency_hz = frequency_hz
        self.distance_m = distance_m
        self.samples = samples

        # Constante física
        self.c = 3e8

    def calculate(self):
        """
        Calcula la primera zona de Fresnel.

        Returns
        -------
        tuple:
            x         -> eje del enlace
            fresnel   -> radio Fresnel
            fmax      -> radio máximo
            wavelength -> longitud de onda
        """

        # Longitud de onda
        wavelength = self.c / self.frequency_hz

        # Eje del enlace
        x = np.linspace(
            0,
            self.distance_m,
            self.samples
        )

        d1 = x
        d2 = self.distance_m - x

        # Primera zona de Fresnel
        denominator = d1 + d2

        fresnel = np.sqrt(
            (wavelength * d1 * d2)
            / denominator
        )

        # Corregir extremos
        fresnel[0] = 0
        fresnel[-1] = 0

        # Radio máximo
        fmax = np.max(fresnel)

        return (
            x,
            fresnel,
            fmax,
            wavelength
        )