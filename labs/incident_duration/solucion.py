"""Solución de referencia: regresión con validez temporal y holdout cerrado."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from datos import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    ID_COLUMN,
    LABEL_AVAILABLE_COLUMN,
    NUMERIC_FEATURES,
    TARGET,
    TIME_COLUMN,
    make_synthetic_dataset,
)


MetricValue = float | int | str | bool | None


@dataclass(frozen=True)
class SelectionResult:
    """Artefacto congelado después de seleccionar exclusivamente en validation."""

    selected_model: str
    selected_family: str
    selected_params: dict[str, Any]
    validation: dict[str, MetricValue]
    comparison: list[dict[str, Any]]
    validation_segment_errors: list[dict[str, MetricValue]]
    validation_residual_diagnostics: dict[str, MetricValue]
    sizes: dict[str, int]
    as_of: dict[str, str]
    pipeline: Pipeline = field(repr=False)


@dataclass(frozen=True)
class HoldoutResult:
    """Resultado que solo existe cuando se abre explícitamente el holdout."""

    selected_model: str
    metrics: dict[str, MetricValue]
    segment_errors: list[dict[str, MetricValue]]
    residual_diagnostics: dict[str, MetricValue]


def temporal_split(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Construye train, validation y holdout con corrección point-in-time.

    ``validation_start`` es el instante simulado de entrenamiento y
    ``holdout_start`` el de congelación. Una observación histórica solo puede
    entrar si su label ya estaba disponible en el ``as-of`` correspondiente.
    Las filas inmaduras de los bordes se purgan; no se reasignan hacia atrás.
    """
    required = {
        TIME_COLUMN,
        LABEL_AVAILABLE_COLUMN,
        TARGET,
        *FEATURE_COLUMNS,
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {sorted(missing)}")
    if len(frame) < 100:
        raise ValueError("Se requieren al menos 100 filas para tres cohortes")

    ordered = frame.copy()
    ordered[TIME_COLUMN] = pd.to_datetime(ordered[TIME_COLUMN], errors="coerce", utc=True)
    ordered[LABEL_AVAILABLE_COLUMN] = pd.to_datetime(
        ordered[LABEL_AVAILABLE_COLUMN], errors="coerce", utc=True
    )
    if ordered[[TIME_COLUMN, LABEL_AVAILABLE_COLUMN]].isna().any().any():
        raise ValueError("Las fechas de decisión y disponibilidad no admiten nulos")
    if (ordered[LABEL_AVAILABLE_COLUMN] < ordered[TIME_COLUMN]).any():
        raise ValueError("Un label no puede estar disponible antes de la decisión")

    ordered = ordered.sort_values(TIME_COLUMN, kind="stable").reset_index(drop=True)
    validation_start = ordered.iloc[int(len(ordered) * 0.65)][TIME_COLUMN]
    holdout_start = ordered.iloc[int(len(ordered) * 0.85)][TIME_COLUMN]

    train = ordered.loc[
        ordered[TIME_COLUMN].lt(validation_start)
        & ordered[LABEL_AVAILABLE_COLUMN].le(validation_start)
    ].copy()
    validation = ordered.loc[
        ordered[TIME_COLUMN].ge(validation_start)
        & ordered[TIME_COLUMN].lt(holdout_start)
        & ordered[LABEL_AVAILABLE_COLUMN].le(holdout_start)
    ].copy()
    holdout = ordered.loc[ordered[TIME_COLUMN].ge(holdout_start)].copy()

    if train.empty or validation.empty or holdout.empty:
        raise ValueError("Las fechas no dejan cohortes maduras y no vacías")
    if not (
        train[TIME_COLUMN].max() < validation[TIME_COLUMN].min()
        and validation[TIME_COLUMN].max() < holdout[TIME_COLUMN].min()
    ):
        raise AssertionError("El split temporal quedó solapado")
    if train[LABEL_AVAILABLE_COLUMN].max() > validation_start:
        raise AssertionError("Train contiene labels inmaduros en validation_start")
    if validation[LABEL_AVAILABLE_COLUMN].max() > holdout_start:
        raise AssertionError("Validation contiene labels inmaduros al congelar")

    return train, validation, holdout


def candidate_specs() -> list[dict[str, Any]]:
    """Declara modelos comparables antes de observar validation."""
    return [
        {"name": "dummy_median", "family": "dummy", "params": {}},
        {"name": "linear", "family": "linear", "params": {}},
        {"name": "ridge_alpha_0_1", "family": "ridge", "params": {"alpha": 0.1}},
        {"name": "ridge_alpha_10", "family": "ridge", "params": {"alpha": 10.0}},
        {
            "name": "random_forest_depth_6",
            "family": "random_forest",
            "params": {
                "n_estimators": 120,
                "max_depth": 6,
                "min_samples_leaf": 8,
                "random_state": 42,
                "n_jobs": 1,
            },
        },
        {
            "name": "random_forest_depth_10",
            "family": "random_forest",
            "params": {
                "n_estimators": 120,
                "max_depth": 10,
                "min_samples_leaf": 5,
                "random_state": 42,
                "n_jobs": 1,
            },
        },
    ]


def build_pipeline(
    model_family: str,
    params: dict[str, Any] | None = None,
) -> Pipeline:
    """Crea preprocesamiento y estimador dentro de un único Pipeline."""
    model_params = dict(params or {})
    if model_family == "dummy":
        if model_params:
            raise ValueError("dummy no admite parámetros en este laboratorio")
        estimator = DummyRegressor(strategy="median")
        scale_numeric = False
    elif model_family == "linear":
        if model_params:
            raise ValueError("linear no admite parámetros en este laboratorio")
        estimator = LinearRegression()
        scale_numeric = True
    elif model_family == "ridge":
        estimator = Ridge(**model_params)
        scale_numeric = True
    elif model_family == "random_forest":
        estimator = RandomForestRegressor(**model_params)
        scale_numeric = False
    else:
        raise ValueError(f"Familia de modelo desconocida: {model_family}")

    numeric_steps: list[tuple[str, Any]] = [
        ("imputer", SimpleImputer(strategy="median"))
    ]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))

    numeric_pipeline = Pipeline(steps=numeric_steps)
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline(steps=[("preprocess", preprocessor), ("model", estimator)])


def _validated_regression_inputs(
    y_true: pd.Series | np.ndarray,
    predictions: pd.Series | np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    try:
        observed = np.asarray(y_true, dtype=float)
        predicted = np.asarray(predictions, dtype=float)
    except (TypeError, ValueError) as error:
        raise ValueError("y_true y predictions deben ser vectores numéricos") from error
    if observed.ndim != 1 or predicted.ndim != 1:
        raise ValueError("y_true y predictions deben ser unidimensionales")
    if len(observed) == 0 or len(observed) != len(predicted):
        raise ValueError("Los vectores deben tener igual longitud no vacía")
    if not np.isfinite(observed).all() or not np.isfinite(predicted).all():
        raise ValueError("Los vectores solo pueden contener valores finitos")
    return observed, predicted


def _safe_r2(observed: np.ndarray, predicted: np.ndarray) -> float | None:
    if len(observed) < 2 or np.isclose(np.var(observed), 0.0):
        return None
    residual_sum = float(np.square(observed - predicted).sum())
    total_sum = float(np.square(observed - observed.mean()).sum())
    return float(1.0 - residual_sum / total_sum)


def evaluate_regression(
    y_true: pd.Series | np.ndarray,
    predictions: pd.Series | np.ndarray,
) -> dict[str, MetricValue]:
    """Calcula métricas globales; residual positivo significa subpredicción."""
    observed, predicted = _validated_regression_inputs(y_true, predictions)
    residual = observed - predicted
    absolute_error = np.abs(residual)
    return {
        "n": int(len(observed)),
        "mae": float(absolute_error.mean()),
        "rmse": float(np.sqrt(np.square(residual).mean())),
        "r2": _safe_r2(observed, predicted),
        "median_absolute_error": float(np.median(absolute_error)),
        "p90_absolute_error": float(np.quantile(absolute_error, 0.90)),
        "mean_residual_observed_minus_predicted": float(residual.mean()),
        "negative_prediction_rate": float(np.mean(predicted < 0.0)),
    }


def _safe_correlation(left: np.ndarray, right: np.ndarray) -> float | None:
    if len(left) < 2 or np.isclose(np.std(left), 0.0) or np.isclose(np.std(right), 0.0):
        return None
    return float(np.corrcoef(left, right)[0, 1])


def residual_diagnostics(
    y_true: pd.Series | np.ndarray,
    predictions: pd.Series | np.ndarray,
) -> dict[str, MetricValue]:
    """Resume sesgo, dispersión y señales simples de heterocedasticidad."""
    observed, predicted = _validated_regression_inputs(y_true, predictions)
    residual = observed - predicted
    absolute_residual = np.abs(residual)
    return {
        "residual_definition": "observed_minus_predicted",
        "mean_residual": float(residual.mean()),
        "median_residual": float(np.median(residual)),
        "residual_std": float(np.std(residual, ddof=0)),
        "residual_q05": float(np.quantile(residual, 0.05)),
        "residual_q95": float(np.quantile(residual, 0.95)),
        "max_absolute_residual": float(absolute_residual.max()),
        "corr_residual_prediction": _safe_correlation(residual, predicted),
        "corr_absolute_residual_prediction": _safe_correlation(
            absolute_residual, predicted
        ),
        "negative_prediction_rate": float(np.mean(predicted < 0.0)),
    }


def segment_errors(
    frame: pd.DataFrame,
    predictions: pd.Series | np.ndarray,
    segment_columns: tuple[str, ...] = ("service_tier", "engine_family"),
) -> pd.DataFrame:
    """Calcula MAE/RMSE/R²/sesgo por cada valor de cada segmentación."""
    if TARGET not in frame:
        raise ValueError(f"Falta la columna objetivo {TARGET}")
    missing = set(segment_columns).difference(frame.columns)
    if missing:
        raise ValueError(f"Faltan columnas de segmento: {sorted(missing)}")
    observed, predicted = _validated_regression_inputs(frame[TARGET], predictions)

    rows: list[dict[str, MetricValue]] = []
    for column in segment_columns:
        labels = frame[column].astype("object").where(frame[column].notna(), "<MISSING>")
        working = pd.DataFrame(
            {
                "segment": labels.astype(str).to_numpy(),
                "observed": observed,
                "predicted": predicted,
            }
        )
        for segment, group in working.groupby("segment", sort=True, dropna=False):
            metrics = evaluate_regression(group["observed"], group["predicted"])
            rows.append(
                {
                    "segment_by": column,
                    "segment": str(segment),
                    **metrics,
                }
            )
    return pd.DataFrame(rows)


def _validate_development_cohorts(
    train: pd.DataFrame,
    validation: pd.DataFrame,
) -> None:
    required = {TIME_COLUMN, LABEL_AVAILABLE_COLUMN, TARGET, *FEATURE_COLUMNS}
    for name, cohort in (("train", train), ("validation", validation)):
        missing = required.difference(cohort.columns)
        if missing:
            raise ValueError(f"{name} no contiene {sorted(missing)}")
        if cohort.empty:
            raise ValueError(f"{name} no puede estar vacío")
        if not np.isfinite(cohort[TARGET].to_numpy(dtype=float)).all():
            raise ValueError(f"{name} contiene targets no finitos")

    train_end = pd.to_datetime(train[TIME_COLUMN], utc=True).max()
    validation_start = pd.to_datetime(validation[TIME_COLUMN], utc=True).min()
    train_labels_as_of = pd.to_datetime(train[LABEL_AVAILABLE_COLUMN], utc=True).max()
    if train_end >= validation_start:
        raise ValueError("Train y validation deben estar ordenados y no solaparse")
    if train_labels_as_of > validation_start:
        raise ValueError("Train contiene labels no disponibles al iniciar validation")
    if ID_COLUMN in train and ID_COLUMN in validation:
        overlap = set(train[ID_COLUMN]).intersection(validation[ID_COLUMN])
        if overlap:
            raise ValueError("Train y validation comparten incident_id")


def train_and_select(
    train: pd.DataFrame,
    validation: pd.DataFrame,
) -> SelectionResult:
    """Ajusta en train y selecciona por MAE de validation, nunca por holdout."""
    _validate_development_cohorts(train, validation)
    records: list[dict[str, Any]] = []
    fitted: dict[str, Pipeline] = {}
    validation_predictions: dict[str, np.ndarray] = {}

    for spec in candidate_specs():
        pipeline = build_pipeline(spec["family"], spec["params"])
        pipeline.fit(train[FEATURE_COLUMNS], train[TARGET])
        predicted = np.asarray(pipeline.predict(validation[FEATURE_COLUMNS]), dtype=float)
        metrics = evaluate_regression(validation[TARGET], predicted)
        records.append(
            {
                "model": spec["name"],
                "family": spec["family"],
                "params": dict(spec["params"]),
                **metrics,
            }
        )
        fitted[spec["name"]] = pipeline
        validation_predictions[spec["name"]] = predicted

    dummy_mae = next(float(row["mae"]) for row in records if row["family"] == "dummy")
    for row in records:
        mae = float(row["mae"])
        row["mae_improvement_vs_dummy"] = float(dummy_mae - mae)
        row["mae_improvement_pct_vs_dummy"] = (
            float(100.0 * (dummy_mae - mae) / dummy_mae) if dummy_mae > 0 else None
        )

    ranked = sorted(
        records,
        key=lambda row: (float(row["mae"]), float(row["rmse"]), str(row["model"])),
    )
    best = ranked[0]
    selected_name = str(best["model"])
    selected_prediction = validation_predictions[selected_name]

    # Los hiperparámetros ya están congelados. El refit usa todo el período de
    # desarrollo cuyos labels estaban disponibles al inicio del holdout.
    development = pd.concat([train, validation], ignore_index=True)
    final_pipeline = clone(fitted[selected_name]).fit(
        development[FEATURE_COLUMNS], development[TARGET]
    )

    validation_start = pd.to_datetime(validation[TIME_COLUMN], utc=True).min()
    frozen_at = pd.to_datetime(validation[LABEL_AVAILABLE_COLUMN], utc=True).max()
    return SelectionResult(
        selected_model=selected_name,
        selected_family=str(best["family"]),
        selected_params=dict(best["params"]),
        validation=evaluate_regression(validation[TARGET], selected_prediction),
        comparison=ranked,
        validation_segment_errors=segment_errors(
            validation, selected_prediction
        ).to_dict(orient="records"),
        validation_residual_diagnostics=residual_diagnostics(
            validation[TARGET], selected_prediction
        ),
        sizes={"train": int(len(train)), "validation": int(len(validation))},
        as_of={
            "validation_start": validation_start.isoformat(),
            "model_frozen_at": frozen_at.isoformat(),
        },
        pipeline=final_pipeline,
    )


def evaluate_holdout(
    selection: SelectionResult,
    holdout: pd.DataFrame,
) -> HoldoutResult:
    """Abre y evalúa el holdout; llamar solo tras congelar el artefacto."""
    required = {TARGET, *FEATURE_COLUMNS}
    missing = required.difference(holdout.columns)
    if missing:
        raise ValueError(f"Holdout incompleto: {sorted(missing)}")
    if holdout.empty:
        raise ValueError("Holdout no puede estar vacío")
    predictions = np.asarray(
        selection.pipeline.predict(holdout[FEATURE_COLUMNS]), dtype=float
    )
    return HoldoutResult(
        selected_model=selection.selected_model,
        metrics=evaluate_regression(holdout[TARGET], predictions),
        segment_errors=segment_errors(holdout, predictions).to_dict(orient="records"),
        residual_diagnostics=residual_diagnostics(holdout[TARGET], predictions),
    )


def run_lab(
    seed: int = 42,
    n_rows: int = 2_400,
    *,
    open_holdout: bool = False,
) -> tuple[SelectionResult, HoldoutResult | None]:
    """Ejecuta el flujo; por defecto no calcula ni muestra ninguna métrica final."""
    frame = make_synthetic_dataset(n_rows=n_rows, seed=seed)
    train, validation, sealed_holdout = temporal_split(frame)
    selection = train_and_select(train, validation)

    excluded_immature = len(frame) - len(train) - len(validation) - len(sealed_holdout)
    holdout_start = pd.to_datetime(sealed_holdout[TIME_COLUMN], utc=True).min()
    selection = replace(
        selection,
        sizes={
            **selection.sizes,
            "holdout_reserved": int(len(sealed_holdout)),
            "excluded_immature": int(excluded_immature),
            "total": int(len(frame)),
        },
        as_of={
            **selection.as_of,
            "holdout_start": holdout_start.isoformat(),
            "model_frozen_at": holdout_start.isoformat(),
        },
    )
    if not open_holdout:
        return selection, None
    return selection, evaluate_holdout(selection, sealed_holdout)


def _selection_payload(selection: SelectionResult) -> dict[str, Any]:
    return {
        "selected_model": selection.selected_model,
        "selected_family": selection.selected_family,
        "selected_params": selection.selected_params,
        "validation": selection.validation,
        "comparison": selection.comparison,
        "validation_segment_errors": selection.validation_segment_errors,
        "validation_residual_diagnostics": selection.validation_residual_diagnostics,
        "sizes": selection.sizes,
        "as_of": selection.as_of,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-rows", type=int, default=2_400)
    parser.add_argument(
        "--open-holdout",
        action="store_true",
        help="Evalúa una sola vez el holdout después de congelar modelo e hiperparámetros.",
    )
    args = parser.parse_args()
    selection, holdout = run_lab(
        seed=args.seed,
        n_rows=args.n_rows,
        open_holdout=args.open_holdout,
    )
    payload: dict[str, Any] = {
        "holdout_status": "OPENED" if holdout is not None else "CLOSED",
        "selection": _selection_payload(selection),
    }
    if holdout is not None:
        payload["holdout"] = {
            "selected_model": holdout.selected_model,
            "metrics": holdout.metrics,
            "segment_errors": holdout.segment_errors,
            "residual_diagnostics": holdout.residual_diagnostics,
        }
    else:
        payload["next_step"] = (
            "Congele el análisis y use --open-holdout solo para la evaluación final."
        )
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
