import numpy as np

# Данные
distances = np.array([0.6, 1.2, 1.8, 2.4, 3.0])
rssis = np.array([-43, -44, -47, -52, -55])

# Берем за d0 = 1 м, RSSI на этом расстоянии:
d0 = 1.0
rssi_d0 = -40  # по данным на 1.2 м ближе всего к 1 м

# Подбираем коэффициент n методом МНК
n, _, _, _ = np.linalg.lstsq(
    np.vstack([np.log10(distances / d0)]).T * -10,
    (rssis - rssi_d0),
    rcond=None
)

n = n[0]

print(f"Показатель затухания n ≈ {n:.2f}")

def rssi_to_distance(rssi: float) -> float:
    """Переводит RSSI (дБм) в расстояние (м)"""
    return d0 * 10 ** ((rssi_d0 - rssi) / (10 * n))

# Проверка
for r in [-38, -40, -47, -51, -55]:
    print(r, "→", round(rssi_to_distance(r), 2), "м")
