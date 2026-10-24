"""
main.py
=======

Punto de entrada del proyecto: carga config.json y abre la ventana principal.
Se puede ejecutar desde cualquier carpeta:  python main.py
"""

import json
import os

from gui.main_window import MainWindow

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def main():
    config_path = os.path.join(BASE_DIR, "config.json")
    with open(config_path, "r", encoding="utf-8") as file:
        config = json.load(file)

    app = MainWindow(config)
    app.run()


if __name__ == "__main__":
    main()