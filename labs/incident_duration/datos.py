"""Datos sintéticos para predecir duración de incidentes operativos.

El módulo no contiene ni representa datos de una entidad financiera. Su único propósito es
crear un caso reproducible en el que cada feature esté disponible en el instante
de decisión y el resultado se conozca después.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


TARGET = "resolution_minutes"
TIME_COLUMN = "decision_time"
LABEL_AVAILABLE_COLUMN = "label_available_at"
LABEL_DELAY_HOURS = 24
ID_COLUMN = "incident_id"

NUMERIC_FEATURES = [
    "cpu_pct_5m",
    "io_latency_ms",
    "blocked_sessions",
    "replication_lag_seconds",
    "incidents_30d",
    "database_size_gb",
    "change_in_window",
    "hour_sin",
    "hour_cos",
]

CATEGORICAL_FEATURES = [
    "service_tier",
    "engine_family",
]

FEATURE_COLUMNS = [*NUMERIC_FEATURES, *CATEGORICAL_FEATURES]

# Estas columnas existen para que el laboratorio pueda demostrar qué NO debe
# entrar al modelo. Algunas nacen después del incidente y otras son metadatos.
FORBIDDEN_FEATURES = [
    TARGET,
    TIME_COLUMN,
    LABEL_AVAILABLE_COLUMN,
    ID_COLUMN,
    "resolved_at",
    "resolution_team",
    "final_root_cause",
    "post_incident_error_rate",
]


def make_synthetic_dataset(
    n_rows: int = 2_400,
    seed: int = 42,
) -> pd.DataFrame:
    """Genera incidentes sintéticos ordenables por su instante de decisión.

    La variable objetivo se limita a menos de 24 horas. Por tanto,
    ``label_available_at = decision_time + 24 h`` es una disponibilidad
    conservadora y no depende del valor del target, lo que evita censura
    informativa al construir las cohortes temporales.
    """
    if isinstance(n_rows, bool) or not isinstance(n_rows, (int, np.integer)):
        raise ValueError("n_rows debe ser un entero")
    if n_rows < 100:
        raise ValueError("n_rows debe ser al menos 100")

    rng = np.random.default_rng(seed)
    decision_time = pd.date_range(
        "2024-01-01T00:00:00Z",
        periods=int(n_rows),
        freq="6h",
    )
    hour = decision_time.hour.to_numpy()
    elapsed = np.linspace(0.0, 1.0, int(n_rows))

    service_tier = rng.choice(
        ["critical", "business", "standard"],
        size=n_rows,
        p=[0.24, 0.46, 0.30],
    )
    engine_family = rng.choice(
        ["oracle_rds", "oracle_onprem", "postgresql_rds"],
        size=n_rows,
        p=[0.37, 0.39, 0.24],
    )

    tier_load = np.select(
        [service_tier == "critical", service_tier == "business"],
        [13.0, 5.0],
        default=-3.0,
    )
    engine_io = np.select(
        [engine_family == "oracle_onprem", engine_family == "oracle_rds"],
        [4.5, 2.0],
        default=-1.0,
    )

    cpu_pct_5m = np.clip(rng.normal(57.0 + tier_load, 16.0, n_rows), 5.0, 99.5)
    io_latency_ms = np.clip(
        rng.gamma(shape=2.4, scale=5.0, size=n_rows) + engine_io,
        0.3,
        95.0,
    )
    blocked_sessions = rng.poisson(
        np.clip(1.6 + cpu_pct_5m / 34.0 + io_latency_ms / 18.0, 0.3, None)
    )
    replication_lag_seconds = np.clip(
        rng.lognormal(mean=2.0, sigma=0.85, size=n_rows)
        + (engine_family == "oracle_onprem") * 4.0,
        0.0,
        420.0,
    )
    incidents_30d = rng.poisson(
        1.5
        + (service_tier == "critical") * 1.9
        + (engine_family == "oracle_onprem") * 0.8
    )
    database_size_gb = np.clip(
        rng.lognormal(mean=6.25, sigma=0.72, size=n_rows),
        25.0,
        8_000.0,
    )
    change_in_window = rng.binomial(
        1,
        np.clip(0.14 + 0.08 * np.sin(2.0 * np.pi * elapsed), 0.03, 0.30),
        n_rows,
    )
    hour_sin = np.sin(2.0 * np.pi * hour / 24.0)
    hour_cos = np.cos(2.0 * np.pi * hour / 24.0)

    # Relación deliberadamente mixta: Ridge captura una parte y el bosque puede
    # capturar umbrales e interacciones. Ningún algoritmo gana por construcción.
    tier_effect = np.select(
        [service_tier == "critical", service_tier == "business"],
        [34.0, 14.0],
        default=0.0,
    )
    engine_effect = np.select(
        [engine_family == "oracle_onprem", engine_family == "oracle_rds"],
        [17.0, 6.0],
        default=0.0,
    )
    nonlinear_pressure = (
        np.maximum(cpu_pct_5m - 78.0, 0.0) * 2.5
        + np.maximum(io_latency_ms - 24.0, 0.0) * 2.0
        + (blocked_sessions >= 8) * 30.0
        + (change_in_window * (replication_lag_seconds > 35.0)) * 42.0
    )
    mild_process_improvement = -18.0 * elapsed
    noise_scale = 13.0 + 0.10 * io_latency_ms + 5.0 * change_in_window
    noise = rng.normal(0.0, noise_scale, n_rows)

    resolution_minutes = (
        28.0
        + tier_effect
        + engine_effect
        + 0.34 * cpu_pct_5m
        + 0.92 * io_latency_ms
        + 4.1 * blocked_sessions
        + 0.22 * replication_lag_seconds
        + 3.8 * incidents_30d
        + 0.008 * database_size_gb
        + 19.0 * change_in_window
        + 5.0 * hour_cos
        + nonlinear_pressure
        + mild_process_improvement
        + noise
    )
    resolution_minutes = np.clip(resolution_minutes, 8.0, 900.0).round(2)

    frame = pd.DataFrame(
        {
            ID_COLUMN: [f"INC-{index:06d}" for index in range(n_rows)],
            TIME_COLUMN: decision_time,
            LABEL_AVAILABLE_COLUMN: decision_time
            + pd.Timedelta(hours=LABEL_DELAY_HOURS),
            "service_tier": service_tier,
            "engine_family": engine_family,
            "cpu_pct_5m": cpu_pct_5m,
            "io_latency_ms": io_latency_ms,
            "blocked_sessions": blocked_sessions.astype(float),
            "replication_lag_seconds": replication_lag_seconds,
            "incidents_30d": incidents_30d.astype(float),
            "database_size_gb": database_size_gb,
            "change_in_window": change_in_window.astype(float),
            "hour_sin": hour_sin,
            "hour_cos": hour_cos,
            TARGET: resolution_minutes,
        }
    )

    # Información que solo aparece durante o después de resolver el incidente.
    frame["resolved_at"] = frame[TIME_COLUMN] + pd.to_timedelta(
        frame[TARGET], unit="m"
    )
    frame["resolution_team"] = np.where(
        frame[TARGET] > 150.0, "specialist_squad", "platform_operations"
    )
    frame["final_root_cause"] = np.select(
        [
            frame["change_in_window"].eq(1.0),
            frame["io_latency_ms"].gt(25.0),
            frame["blocked_sessions"].ge(8.0),
        ],
        ["change", "storage", "contention"],
        default="other",
    )
    frame["post_incident_error_rate"] = np.clip(
        0.003 + frame[TARGET] / 100_000.0 + rng.normal(0.0, 0.001, n_rows),
        0.0,
        None,
    )

    # Los faltantes se inyectan después de construir el target: son un problema
    # de calidad de captura, no una fuente oculta para generar la etiqueta.
    for column, rate in {
        "cpu_pct_5m": 0.025,
        "io_latency_ms": 0.035,
        "replication_lag_seconds": 0.030,
        "database_size_gb": 0.020,
        "engine_family": 0.015,
    }.items():
        missing = rng.random(n_rows) < rate
        frame.loc[missing, column] = np.nan

    return frame
