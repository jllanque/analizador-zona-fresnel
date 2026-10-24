"""
obstacle_checker.py
===================

Evaluación de obstáculos respecto a la primera zona de Fresnel.

Incluye:
- Línea de vista (LOS) recta entre las puntas de antena.
- Despeje del obstáculo respecto al radio r1 de la 1ª zona de Fresnel.
- Pérdida por difracción (filo de cuchillo, aproximación de la Rec. UIT-R P.526).

Criterio de clasificación (despeje c = (h_LOS - h_obstáculo) / r1):
    ACEPTABLE : c >= clearance_acceptable   (por defecto 0.6: difracción
                                             despreciable, criterio del 60 %
                                             de la 1ª zona de Fresnel)
    CRITICO   : 0 < c < clearance_acceptable (intrusión parcial en la 1ª zona)
    NO VIABLE : c <= 0                       (el obstáculo alcanza o supera la LOS)

Modelo de tierra plana: NO se calcula la curvatura terrestre. Es una
aproximación razonable para enlaces cortos; a partir de ~15-20 km el
abultamiento de la Tierra (d1*d2 / (2*k*R)) deja de ser despreciable
frente al radio de Fresnel.
"""

import numpy as np
from models.obstacle import Obstacle
from models.obstacle_result import ObstacleResult


class ObstacleChecker:
    """
    Evalúa obstáculos sobre la primera zona de Fresnel.
    """

    def __init__(
        self,
        x: np.ndarray,
        fresnel: np.ndarray,
        distance_m: float,
        tx_height: float,
        rx_height: float,
        clearance_acceptable: float = 0.6,
        wavelength: float = 0.125
    ):
        """
        Args:
            x: posiciones a lo largo del eje del enlace (m)
            fresnel: radio de la primera zona de Fresnel (m)
            distance_m: distancia total (m), debe ser > 0
            tx_height: altura de la antena transmisora (m)
            rx_height: altura de la antena receptora (m)
            clearance_acceptable: despeje mínimo (en unidades de r1) para
                considerar ACEPTABLE al obstáculo. Debe ser > 0.
            wavelength: longitud de onda (m)
        """
        if distance_m <= 0:
            raise ValueError("La distancia del enlace debe ser mayor que cero.")
        if clearance_acceptable <= 0:
            raise ValueError("El despeje aceptable debe ser mayor que cero.")

        self.x = x
        self.fresnel = fresnel
        self.distance_m = distance_m
        self.tx_height = tx_height
        self.rx_height = rx_height
        self.clearance_acceptable = clearance_acceptable
        self.wavelength = wavelength

        # Línea de vista recta (sin curvatura terrestre)
        self.los = self._los_at(self.x)

    def _los_at(self, position):
        """Altura de la LOS recta en una posición (m) o array de posiciones."""
        slope = (self.rx_height - self.tx_height) / self.distance_m
        return self.tx_height + slope * position

    @staticmethod
    def knife_edge_loss(nu: float) -> float:
        """
        Pérdida por difracción (dB) de un obstáculo tipo filo de cuchillo.

        Aproximación de la Rec. UIT-R P.526:
            J(nu) = 6.9 + 20*log10( sqrt((nu - 0.1)^2 + 1) + nu - 0.1 ),  nu > -0.78
        Para nu <= -0.78 la pérdida es despreciable (0 dB).
        Frente a la integral de Fresnel exacta el error es <= ~0.12 dB
        para -0.78 <= nu <= 10.

        Args:
            nu: parámetro de Fresnel-Kirchhoff (positivo si el obstáculo
                supera la línea de vista).

        Returns:
            Pérdida en dB (>= 0).
        """
        if nu <= -0.78:
            return 0.0
        x = nu - 0.1
        loss = 6.9 + 20 * np.log10(np.sqrt(x * x + 1) + x)
        return max(0.0, float(loss))

    @staticmethod
    def _fmt_ratio(ratio: float) -> str:
        return "inf" if np.isinf(ratio) else f"{ratio:.2f}"

    def check(self, obstacles: list[Obstacle]) -> list[ObstacleResult]:
        """
        Evalúa todos los obstáculos.

        Args:
            obstacles: lista de objetos Obstacle.

        Returns:
            Lista de ObstacleResult.
        """
        results = []
        for i, obstacle in enumerate(obstacles, start=1):
            # LOS exacta en la posición del obstáculo y radio de Fresnel
            # interpolado linealmente sobre la malla (sin depender de la
            # muestra más cercana).
            los_height = float(self._los_at(obstacle.position))
            radius = float(np.interp(obstacle.position, self.x, self.fresnel))

            # Despeje respecto a la LOS, en unidades de r1
            if radius <= 1e-9:
                clearance = np.inf if obstacle.height < los_height else -np.inf
            else:
                clearance = (los_height - obstacle.height) / radius

            # Penetración en el radio de la 1ª zona (0..100 %)
            if np.isinf(clearance):
                block_percent = 0.0 if clearance > 0 else 100.0
            else:
                block_percent = float(np.clip((1.0 - clearance) * 100.0, 0.0, 100.0))

            # ---------- Pérdida por difracción ----------
            d1 = obstacle.position
            d2 = self.distance_m - obstacle.position

            if d1 <= 0 or d2 <= 0 or self.wavelength <= 0:
                loss_db = 0.0
            else:
                # Altura del obstáculo sobre la línea de visión (LOS)
                h_los = obstacle.height - los_height
                # Parámetro de Fresnel-Kirchhoff
                nu = h_los * np.sqrt(2 * (d1 + d2) / (self.wavelength * d1 * d2))
                loss_db = self.knife_edge_loss(nu)

            # Clasificación según el despeje
            if clearance >= self.clearance_acceptable:
                state = "ACEPTABLE"
            elif clearance > 0:
                state = "CRITICO"
            else:
                state = "NO VIABLE"

            message = (
                f"{obstacle.name} → despeje {self._fmt_ratio(clearance)}·r1 "
                f"({block_percent:.1f}% de penetración, {state}) "
                f"| Difracción: {loss_db:.1f} dB"
            )

            results.append(ObstacleResult(
                index=i,
                name=obstacle.name,
                position=obstacle.position,
                height=obstacle.height,
                block_percent=block_percent,
                state=state,
                message=message,
                diffraction_loss_db=loss_db,
                clearance_ratio=float(clearance)
            ))

        return results
