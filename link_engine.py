"""
link_engine.py
==============

Motor de cálculo que integra Fresnel, obstáculos y reflexiones.
Modelo de tierra plana (sin curvatura terrestre).
"""

from typing import Optional

import numpy as np
from fresnel_calculator import FresnelCalculator
from obstacle_checker import ObstacleChecker
from reflection_obstacle import reflection_phasor, field_factor_db


class LinkEngine:
    """
    Orquesta los cálculos del radioenlace:
    - Primera zona de Fresnel (y opcionalmente zonas superiores)
    - Verificación de obstáculos con pérdida por difracción
    - Factor de reflexión combinado (opcional)
    """

    def __init__(self, config: dict):
        """
        Args:
            config: Diccionario con la configuración (samples, umbrales, etc.)
        """
        self.config = config

    @staticmethod
    def _validate(frequency_hz, distance_m, obstacles):
        if frequency_hz <= 0:
            raise ValueError("La frecuencia debe ser mayor que cero.")
        if distance_m <= 0:
            raise ValueError("La distancia debe ser mayor que cero.")
        outside = [
            f"'{o.name}' ({o.position:g} m)"
            for o in obstacles
            if not 0 <= o.position <= distance_m
        ]
        if outside:
            raise ValueError(
                f"Obstáculos fuera del enlace (0 a {distance_m:g} m): "
                + ", ".join(outside)
            )

    def compute(self,
                frequency_hz: float,
                distance_m: float,
                tx_height: float,
                rx_height: float,
                obstacles: list,
                n_zones: int = 1,
                include_reflections: bool = False,
                clearance_factor: Optional[float] = None):
        """
        Realiza el cálculo completo del enlace.

        Args:
            frequency_hz: Frecuencia en Hz.
            distance_m: Distancia total del enlace (m).
            tx_height: Altura total de la antena transmisora sobre el suelo (m).
            rx_height: Altura total de la antena receptora sobre el suelo (m).
            obstacles: Lista de objetos Obstacle (posiciones entre 0 y distance_m).
            n_zones: Número de zonas de Fresnel a calcular (1 a 5).
            include_reflections: Si es True, calcula el factor de reflexión.
            clearance_factor: despeje mínimo aceptable en unidades de r1
                (por defecto config["clearance_acceptable"], 0.6).

        Returns:
            tuple: (x, fresnel_zones, fmax, wavelength, results, los, reflection_factor_db)
                - x: numpy.ndarray – posiciones a lo largo del enlace (m)
                - fresnel_zones: dict – {n: numpy.ndarray} radios para cada zona n
                - fmax: float – radio máximo de la primera zona (m)
                - wavelength: float – longitud de onda (m)
                - results: list[ObstacleResult] – resultados de los obstáculos
                - los: numpy.ndarray – línea de vista recta (m)
                - reflection_factor_db: float – factor de reflexión (0.0 si no se pidió)

        Raises:
            ValueError: frecuencia/distancia no positivas u obstáculos fuera del enlace.
        """
        self._validate(frequency_hz, distance_m, obstacles)
        n_zones = max(1, int(n_zones))
        if clearance_factor is None:
            clearance_factor = self.config.get("clearance_acceptable", 0.6)

        # 1. Cálculo básico de la primera zona de Fresnel
        calc = FresnelCalculator(frequency_hz, distance_m, self.config["samples"])
        x, fresnel_1, fmax, wavelength = calc.calculate()

        # 2. Diccionario de zonas de Fresnel (n=1..n_zones)
        fresnel_zones = {1: fresnel_1}
        for n in range(2, n_zones + 1):
            fresnel_zones[n] = np.sqrt(n) * fresnel_1

        # 3. Verificar obstáculos
        checker = ObstacleChecker(
            x, fresnel_1, distance_m, tx_height, rx_height,
            clearance_acceptable=clearance_factor,
            wavelength=wavelength
        )
        results = checker.check(obstacles)

        reflection_factor_db = 0.0
        if include_reflections:
            reflection_factor_db = self.compute_reflection_factor(
                distance_m, tx_height, rx_height, obstacles, wavelength)

        return x, fresnel_zones, fmax, wavelength, results, checker.los, reflection_factor_db

    def compute_reflection_factor(self, distance_m, tx_height, rx_height, obstacles, wavelength):
        """
        Factor de reflexión total (dB) con todos los obstáculos reflectantes.

        Los fasores de los rayos reflejados se suman coherentemente con el
        rayo directo (ver reflection_obstacle).
        """
        phasors = [
            reflection_phasor(0.0, distance_m, obs.position,
                              tx_height, rx_height, obs.height,
                              wavelength, obs.reflectivity)
            for obs in obstacles
            if obs.reflectivity > 0
        ]
        if not phasors:
            return 0.0
        return field_factor_db(phasors)
