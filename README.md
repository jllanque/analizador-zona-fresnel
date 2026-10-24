# Analizador de Zona de Fresnel

Aplicación de escritorio en Python (Tkinter + matplotlib) para analizar un radioenlace punto a punto:
calcula la primera zona de Fresnel, evalúa el despeje de obstáculos, estima la pérdida por difracción,
el presupuesto de enlace (link budget) y genera un informe PDF con vistas 2D y 3D.

## Problema que resuelve

Dado un enlace (frecuencia, distancia, alturas de antena y edificios) y una lista de obstáculos,
responde a: ¿hay despeje suficiente de la 1ª zona de Fresnel?, ¿cuánta pérdida añaden los obstáculos?
y ¿queda margen sobre la sensibilidad del receptor?

## Características

- Primera zona de Fresnel y zonas superiores (1 a 5) a lo largo del enlace.
- Clasificación de cada obstáculo por despeje (ACEPTABLE / CRITICO / NO VIABLE).
- Pérdida por difracción de filo de cuchillo por obstáculo.
- Presupuesto de enlace: FSL, potencia recibida y margen.
- Reflexión en obstáculos (opcional, modelo simplificado de un rebote).
- Gráfica 2D interactiva (zoom con la rueda, desplazamiento con el botón izquierdo, tooltip al pasar sobre un obstáculo),
  vista 3D y exportación a PDF.
- Obstáculos editables en la interfaz y persistentes en CSV.

## Arquitectura

```
main.py                  Entrada: carga config.json y abre la ventana
config.json              Parámetros de dibujo y criterio de despeje
fresnel_calculator.py    Longitud de onda y radio de la 1ª zona de Fresnel
obstacle_checker.py      LOS recta, despeje, clasificación y difracción
reflection_obstacle.py   Fasores de reflexión en obstáculos
link_engine.py           Orquesta Fresnel + obstáculos + reflexión
link_budget.py           FSL, potencia recibida y margen (sin GUI)
obstacle_repository.py   Lectura/escritura de obstáculos en CSV
visualization_engine.py  Dibujo 2D
visualization_3d.py      Dibujo 3D
export_service.py        Informe PDF
gui/main_window.py       Interfaz gráfica
models/                  Dataclasses Obstacle y ObstacleResult
data/                    CSV de obstáculos
examples/                Uso sin GUI y demo de reflexión en el suelo
tests/                   Pruebas unitarias y de integración
```

Flujo: `MainWindow` lee los parámetros → `LinkEngine.compute` (Fresnel, obstáculos, reflexión) →
`link_budget.compute_link_budget` → dibujo y resultados; el PDF reutiliza exactamente los valores del último cálculo.

## Requisitos e instalación

- Python 3.9 o superior (se usa la sintaxis `list[...]`).
- Tkinter (viene con Python en Windows y macOS; en Linux: paquete `python3-tk`).
- Dependencias: `numpy`, `matplotlib`, `reportlab`.

Probado con Python 3.12, numpy 2.4, matplotlib 3.10 y reportlab 4.4. No se han verificado versiones anteriores.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecución

Desde cualquier carpeta (`config.json` y `data/obstacles.csv` se buscan junto al código):

```bash
python main.py
```

Atajos: `Enter`/`F5` calcular, `Ctrl+O` cargar CSV, `Ctrl+S` guardar obstáculos, `Ctrl+E` limpiar.

Uso sin interfaz gráfica: `python examples/link_example.py`.

## Parámetros

**Interfaz**

| Campo | Significado |
|---|---|
| Frecuencia [GHz], Distancia [m] | Datos del enlace |
| Antena sobre edificio / Altura de edificio [m] | La altura total de cada extremo es edificio + antena |
| Despeje mínimo [×r₁] | Despeje a partir del cual un obstáculo es ACEPTABLE (0.6 por defecto); también dibuja la zona de despejamiento |
| Zonas de Fresnel | Cuántas zonas dibujar (1–5) |
| Potencia TX, Ganancias, Sensibilidad RX | Presupuesto de enlace (dBm / dBi) |
| Reflexiones | Incluye el factor de reflexión en la potencia recibida |

**`config.json`**

| Clave | Significado |
|---|---|
| `samples` | Puntos a lo largo del enlace (resolución de las curvas) |
| `clearance_acceptable` | Despeje aceptable por defecto (×r₁) |
| `building_width_ratio`, `obstacle_width_ratio` | Ancho de edificios y obstáculos como fracción de la distancia |
| `plot_margin` | Margen vertical de la gráfica (m) |
| `*_color` | Colores RGB (0–1) de edificios y estados |
| `theme` | `light` o `dark` (solo gráfica) |

**`data/obstacles.csv`**: columnas `name, position, height` y opcional `reflectivity` (0–1; por defecto 0.8).
`position` es la distancia al transmisor y debe estar entre 0 y la distancia del enlace.

## Fórmulas

- Longitud de onda: λ = c / f, con c = 3·10⁸ m/s.
- Radio de la zona de Fresnel n: rₙ = √(n·λ·d₁·d₂ / (d₁ + d₂)).
- Línea de vista recta entre las puntas de antena (alturas totales sobre el suelo).
- Despeje: c = (h_LOS − h_obstáculo) / r₁. Clasificación: ACEPTABLE si c ≥ 0.6, CRITICO si 0 < c < 0.6, NO VIABLE si c ≤ 0.
  El criterio del 60 % de la 1ª zona de Fresnel es el habitual para considerar despreciable la difracción.
  El porcentaje de penetración que se muestra es (1 − c)·100, acotado a 0–100 %.
- Parámetro de Fresnel-Kirchhoff: ν = h·√(2(d₁+d₂) / (λ·d₁·d₂)), con h la altura del obstáculo sobre la LOS.
- Pérdida de filo de cuchillo (aproximación UIT-R P.526): J(ν) = 6.9 + 20·log₁₀(√((ν−0.1)²+1) + ν − 0.1) para ν > −0.78; 0 dB en caso contrario.
  Frente a la integral de Fresnel exacta, el error es de 0.12 dB como máximo entre ν = −0.78 y 10.
- Pérdida en espacio libre: FSL = 20·log₁₀(d[km]) + 20·log₁₀(f[MHz]) + 32.44.
- Potencia recibida: P_rx = P_tx + G_tx + G_rx − FSL − ΣL_difracción + G_reflexión; margen = P_rx − sensibilidad.
- Reflexión: G = 20·log₁₀|1 + Σᵢ(−ρᵢ)·e^(−jφᵢ)|, con φᵢ = 2πΔᵢ/λ y Δᵢ la diferencia de camino TX→obstáculo→RX frente al camino directo.

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest
```

## Limitaciones conocidas

- **Tierra plana**: no se considera la curvatura terrestre ni el factor k. Es adecuado para enlaces cortos;
  a partir de unos 15–20 km el abultamiento ya no es despreciable frente al radio de Fresnel.
- No hay perfil de terreno: el suelo es plano y solo existen los obstáculos que se definan.
- La pérdida total por difracción es la **suma** de las pérdidas de filo simple de cada obstáculo;
  es una aproximación (no se usan métodos multi-obstáculo como Deygout o Epstein-Petersen).
- La reflexión es heurística: el reflector es la cima del obstáculo, sin comprobar la geometría especular
  ni corregir la amplitud por la mayor distancia recorrida.
- El presupuesto no incluye pérdidas de cable, atmosféricas, por lluvia ni de polarización.
- La difracción se calcula en la posición del obstáculo como borde delgado; no se modelan obstáculos con anchura.

## Referencias

- Recomendación UIT-R P.526, *Propagación por difracción*.
- Recomendación UIT-R P.525, *Cálculo de la atenuación en el espacio libre*.
- A. Vigants, "Space Diversity Engineering", *Bell System Technical Journal*, vol. 54 (criterios de despeje de la 1ª zona de Fresnel).

## Licencia

Distribuido bajo licencia MIT. Ver el archivo [LICENSE](LICENSE).
