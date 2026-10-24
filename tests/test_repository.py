"""
tests/test_repository.py
Pruebas para ObstacleRepository (persistencia CSV).
"""

import os
import tempfile
import pytest
from models.obstacle import Obstacle
from obstacle_repository import ObstacleRepository


def test_save_and_load():
    """Guardar y luego cargar debe recuperar los mismos obstáculos."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
        tmp_path = tmp.name
    obs_list = [
        Obstacle("A", 100.0, 50.0),
        Obstacle("B", 200.0, 60.0, reflectivity=0.3)
    ]
    repo = ObstacleRepository(default_path=tmp_path)
    repo.save(obs_list)
    loaded = repo.load()
    assert len(loaded) == 2
    assert loaded[0].name == "A"
    assert loaded[0].position == 100.0
    assert loaded[0].height == 50.0
    assert loaded[0].reflectivity == 0.8
    assert loaded[1].name == "B"
    assert loaded[1].reflectivity == 0.3
    os.unlink(tmp_path)


def test_load_missing_file():
    """Si el archivo no existe, load() debe devolver lista vacía sin excepción."""
    repo = ObstacleRepository(default_path="no_existe.csv")
    assert repo.load() == []


def test_load_invalid_csv():
    """CSV con columnas incorrectas debe lanzar ValueError."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
        tmp.write("wrong,col,names\n1,2,3")
        tmp_path = tmp.name
    repo = ObstacleRepository(default_path=tmp_path)
    with pytest.raises(ValueError):
        repo.load()
    os.unlink(tmp_path)


def test_save_to_path_without_directory():
    """Una ruta sin directorio (p. ej. 'obs.csv') no debe fallar en makedirs."""
    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)
        try:
            repo = ObstacleRepository()
            repo.save([Obstacle("A", 1.0, 2.0)], "obs.csv")
            assert os.path.exists(os.path.join(tmpdir, "obs.csv"))
        finally:
            os.chdir(old_cwd)


def test_save_creates_missing_directory():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "sub", "obs.csv")
        ObstacleRepository().save([Obstacle("A", 1.0, 2.0)], path)
        assert os.path.exists(path)


def test_load_csv_with_bom():
    """Los CSV guardados por Excel con BOM deben cargarse."""
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
        tmp.write("name,position,height\nEdificio A,450.0,54.0\n".encode("utf-8-sig"))
        tmp_path = tmp.name
    loaded = ObstacleRepository().load(tmp_path)
    assert len(loaded) == 1 and loaded[0].name == "Edificio A"
    os.unlink(tmp_path)


def test_missing_or_blank_reflectivity_uses_model_default():
    default = Obstacle("x", 0, 0).reflectivity
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
        tmp.write("name,position,height,reflectivity\nA,1,2,\nB,3,4,0.2\n")
        path_blank = tmp.name
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
        tmp.write("name,position,height\nC,5,6\n")
        path_missing = tmp.name
    blank = ObstacleRepository().load(path_blank)
    missing = ObstacleRepository().load(path_missing)
    assert blank[0].reflectivity == default
    assert blank[1].reflectivity == 0.2
    assert missing[0].reflectivity == default
    os.unlink(path_blank)
    os.unlink(path_missing)


def test_non_numeric_value_raises_value_error_with_line():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
        tmp.write("name,position,height\nA,abc,2\n")
        path = tmp.name
    with pytest.raises(ValueError, match="Línea 2"):
        ObstacleRepository().load(path)
    os.unlink(path)
