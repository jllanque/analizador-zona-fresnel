"""
obstacle_repository.py
======================

Repositorio para cargar y guardar obstáculos desde/hacia CSV.
Soporta el campo reflectivity (coeficiente de reflexión).
"""

import csv
import os
from typing import Optional

from models.obstacle import Obstacle

# Ruta del CSV por defecto, anclada a la carpeta del proyecto (no al directorio de trabajo)
DEFAULT_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "obstacles.csv")


class ObstacleRepository:
    """
    Maneja la persistencia de obstáculos en formato CSV.
    """

    REQUIRED_COLUMNS = ("name", "position", "height")

    def __init__(self, default_path: str = DEFAULT_CSV):
        """
        Args:
            default_path: Ruta al archivo CSV por defecto.
        """
        self.default_path = default_path

    def load(self, path: Optional[str] = None) -> list[Obstacle]:
        """
        Carga los obstáculos desde un archivo CSV.

        Args:
            path: Ruta al archivo. Si es None, usa default_path.

        Returns:
            Lista de objetos Obstacle. Si el archivo no existe, retorna lista vacía.

        Raises:
            ValueError: faltan columnas obligatorias o hay valores no numéricos.
        """
        if path is None:
            path = self.default_path

        obstacles = []
        try:
            # utf-8-sig: tolera el BOM que añade Excel al guardar CSV
            with open(path, "r", encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file)
                if reader.fieldnames is None:
                    return obstacles
                missing = [c for c in self.REQUIRED_COLUMNS if c not in reader.fieldnames]
                if missing:
                    raise ValueError(
                        "El archivo CSV debe tener las columnas: name, position, height "
                        f"(opcional: reflectivity). Faltan: {', '.join(missing)}"
                    )
                for line_no, row in enumerate(reader, start=2):
                    obstacles.append(self._row_to_obstacle(row, line_no))
        except FileNotFoundError:
            # Si no existe, devolvemos lista vacía (sin lanzar excepción)
            pass
        return obstacles

    @staticmethod
    def _row_to_obstacle(row: dict, line_no: int) -> Obstacle:
        try:
            kwargs = dict(
                name=row["name"],
                position=float(row["position"]),
                height=float(row["height"]),
            )
            raw = row.get("reflectivity")
            # Columna ausente o vacía -> valor por defecto del modelo
            if raw is not None and raw.strip() != "":
                kwargs["reflectivity"] = float(raw)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Línea {line_no} del CSV inválida: {e}") from e
        return Obstacle(**kwargs)

    def save(self, obstacles: list[Obstacle], path: Optional[str] = None) -> None:
        """
        Guarda la lista de obstáculos en un archivo CSV.

        Args:
            obstacles: Lista de objetos Obstacle.
            path: Ruta al archivo. Si es None, usa default_path.
        """
        if path is None:
            path = self.default_path

        # Crear el directorio si la ruta lo incluye
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

        with open(path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["name", "position", "height", "reflectivity"])
            for obs in obstacles:
                writer.writerow([obs.name, obs.position, obs.height, obs.reflectivity])