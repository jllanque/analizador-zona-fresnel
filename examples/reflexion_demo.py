"""
examples/reflexion_demo.py
==========================

Demostración gráfica del efecto de la reflexión en el SUELO (modelo de dos
rayos) sobre la potencia recibida. Script independiente: no usa los módulos
del proyecto.

    python examples/reflexion_demo.py
"""

import numpy as np
import matplotlib.pyplot as plt

C = 3e8


def two_ray_power(d, ht, hr, lam, R):
    """
    Ganancia (dB) por la interferencia del rayo reflejado en el suelo,
    respecto al espacio libre:  20*log10 |1 + R*exp(-j*phi)|.
    """
    d_reflect = np.sqrt((ht + hr) ** 2 + d ** 2)
    delta = d_reflect - d
    phi = 2 * np.pi * delta / lam
    return 20 * np.log10(np.abs(1 + R * np.exp(-1j * phi)))


def main():
    freq_hz = 900e6
    lam = C / freq_hz
    distancia = 5000.0      # m
    ht = hr = 30.0          # m
    R = -1.0                # reflexión total con inversión de fase

    # 1. Perfil del enlace con la trayectoria reflejada en el suelo
    x = np.linspace(0, distancia, 200)
    y_directa = ht + (hr - ht) * (x / distancia)
    x_ref = ht / (ht + hr) * distancia          # punto de reflexión (exacto)
    y_ref = np.where(x <= x_ref,
                     ht * (1 - x / x_ref),
                     hr * (x - x_ref) / (distancia - x_ref))

    plt.figure(figsize=(10, 5))
    plt.plot(x, y_directa, 'r-', label='Trayectoria directa (LOS)')
    plt.plot(x, y_ref, 'b--', label='Trayectoria reflejada en el suelo')
    plt.axhspan(-0.1 * max(ht, hr), 0, color='saddlebrown', alpha=0.4, label='Suelo')
    plt.ylim(-0.1 * max(ht, hr), max(ht, hr) * 1.2)
    plt.xlabel('Distancia (m)')
    plt.ylabel('Altura (m)')
    plt.title('Modelo de dos rayos – Perfil del enlace con reflexión en el suelo')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # 2. Potencia relativa vs distancia
    distancias = np.linspace(100, 10000, 500)
    ganancia = two_ray_power(distancias, ht, hr, lam, R)
    plt.figure(figsize=(10, 5))
    plt.plot(distancias / 1000, ganancia, 'b-', linewidth=1)
    plt.axhline(y=0, color='k', linestyle='--', alpha=0.5, label='Espacio libre (0 dB)')
    plt.xlabel('Distancia entre antenas (km)')
    plt.ylabel('Potencia recibida relativa (dB)')
    plt.title('Efecto de la reflexión en el suelo – Modelo de dos rayos')
    plt.ylim(-30, 10)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    # 3. Potencia relativa vs frecuencia (distancia fija)
    frecuencias = np.linspace(100, 2000, 500)   # MHz
    ganancia_f = two_ray_power(distancia, ht, hr, C / (frecuencias * 1e6), R)
    plt.figure(figsize=(10, 5))
    plt.semilogx(frecuencias, ganancia_f, 'r-', linewidth=1)
    plt.axhline(y=0, color='k', linestyle='--', alpha=0.5, label='Espacio libre')
    plt.xlabel('Frecuencia (MHz)')
    plt.ylabel('Potencia recibida relativa (dB)')
    plt.title('Desvanecimiento por frecuencia debido a la reflexión (distancia fija)')
    plt.ylim(-30, 10)
    plt.grid(True)
    plt.legend()
    plt.tight_layout()

    plt.show()


if __name__ == "__main__":
    main()
