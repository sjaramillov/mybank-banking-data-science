"""Contrato de datos y generador sintético del laboratorio de clasificación."""

from __future__ import annotations

import numpy as np
import pandas as pd


TARGET = "default_90d"
TIME_COLUMN = "decision_date"
LABEL_AVAILABLE_COLUMN = "label_available_at"
ID_COLUMN = "customer_id"
LABEL_HORIZON_DAYS = 90

NUMERIC_FEATURES = [
    "declared_income",
    "debt_to_income",
    "historical_arrears",
    "customer_tenure_months",
]
CATEGORICAL_FEATURES = ["product_type", "channel"]
FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# Son columnas útiles para auditoría o para construir el split, pero no predictores.
FORBIDDEN_FEATURES = {
    TARGET,
    TIME_COLUMN,
    LABEL_AVAILABLE_COLUMN,
    ID_COLUMN,
    "collection_result",
    "balance_30d",
}


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-values))


def make_synthetic_dataset(n_rows: int = 8_000, seed: int = 42) -> pd.DataFrame:
    """Crea solicitudes sintéticas con label a 90 días, drift leve y faltantes.

    Una observación por día garantiza que incluso ``n_rows=1_000`` tenga espacio
    para dos ventanas de maduración de 90 días y tres cohortes no vacías.
    """
    if n_rows < 1_000:
        raise ValueError("n_rows debe ser al menos 1.000 para este laboratorio")

    rng = np.random.default_rng(seed)
    dates = pd.date_range(end="2025-12-31", periods=n_rows, freq="D")
    customer_id = np.array(
        [f"C{value:05d}" for value in rng.integers(0, 4_000, n_rows)]
    )

    income = rng.lognormal(mean=np.log(4_500_000), sigma=0.55, size=n_rows)
    debt_to_income = np.clip(rng.beta(2.2, 3.8, n_rows), 0.02, 0.98)
    arrears = np.clip(rng.poisson(0.35, n_rows), 0, 5).astype(float)
    tenure = rng.integers(0, 181, n_rows).astype(float)
    product = rng.choice(
        ["consumer", "credit_card", "microcredit"],
        size=n_rows,
        p=[0.48, 0.37, 0.15],
    )
    channel = rng.choice(
        ["branch", "mobile", "web"],
        size=n_rows,
        p=[0.24, 0.51, 0.25],
    )

    # El riesgo base aumenta en el tiempo sin incluir tiempo como predictor.
    # Es un cambio deliberado de prior/concepto, no covariate drift.
    time_index = np.linspace(0.0, 1.0, n_rows)
    log_odds = (
        -4.15
        + 0.85 * arrears
        + 2.6 * (debt_to_income - 0.35)
        - 0.006 * tenure
        - 0.22 * np.log(income / 4_500_000)
        + 0.45 * (product == "microcredit")
        + 0.18 * (product == "credit_card")
        + 0.20 * (channel == "web")
        + 0.35 * time_index
    )
    probability = _sigmoid(log_odds)
    target = rng.binomial(1, probability, n_rows)

    frame = pd.DataFrame(
        {
            TIME_COLUMN: dates,
            LABEL_AVAILABLE_COLUMN: dates
            + pd.Timedelta(days=LABEL_HORIZON_DAYS),
            ID_COLUMN: customer_id,
            "declared_income": income,
            "debt_to_income": debt_to_income,
            "historical_arrears": arrears,
            "customer_tenure_months": tenure,
            "product_type": product,
            "channel": channel,
            TARGET: target,
        }
    )

    # Trampas temporales: contienen información posterior a decision_date.
    frame["collection_result"] = np.where(
        frame[TARGET].eq(1), "delinquent", "current"
    )
    frame["balance_30d"] = (
        frame["declared_income"]
        * rng.uniform(0.05, 0.8, n_rows)
        * np.where(frame[TARGET].eq(1), 1.5, 1.0)
    )

    for column, rate in {
        "declared_income": 0.025,
        "debt_to_income": 0.015,
        "customer_tenure_months": 0.01,
        "channel": 0.008,
    }.items():
        missing = rng.random(n_rows) < rate
        frame.loc[missing, column] = np.nan

    return frame
