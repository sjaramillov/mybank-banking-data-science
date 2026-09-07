"""Baseline reproducible: validez temporal y decisión antes que sofisticación."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field, replace

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from datos import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    FORBIDDEN_FEATURES,
    LABEL_AVAILABLE_COLUMN,
    NUMERIC_FEATURES,
    TARGET,
    TIME_COLUMN,
    make_synthetic_dataset,
)


MetricValue = float | int | bool


@dataclass(frozen=True)
class SelectionResult:
    """Artefacto congelado antes de abrir el holdout."""

    threshold: float
    validation: dict[str, MetricValue]
    validation_calibration: list[dict[str, float | int]]
    sizes: dict[str, int]
    as_of: dict[str, str]
    reference_prevalence: float
    cost_fn: float
    cost_fp: float
    design_max_alert_rate: float
    pipeline: Pipeline = field(repr=False)


@dataclass(frozen=True)
class HoldoutResult:
    """Resultado producido únicamente tras autorización explícita."""

    metrics: dict[str, MetricValue]
    calibration: list[dict[str, float | int]]


def temporal_split(
    frame: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Crea cohortes temporales y purga labels aún no disponibles en cada as-of.

    ``validation_start`` simula el momento de entrenamiento. Solo entran a train
    labels disponibles a esa fecha. ``test_start`` simula el momento de congelar
    modelo y threshold; solo entran a validation labels disponibles a esa fecha.
    Las filas inmaduras se excluyen deliberadamente.
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
    if len(frame) < 10:
        raise ValueError("Se requieren al menos 10 filas para construir tres cohortes")

    ordered = frame.copy()
    ordered[TIME_COLUMN] = pd.to_datetime(ordered[TIME_COLUMN], errors="coerce")
    ordered[LABEL_AVAILABLE_COLUMN] = pd.to_datetime(
        ordered[LABEL_AVAILABLE_COLUMN], errors="coerce"
    )
    if ordered[[TIME_COLUMN, LABEL_AVAILABLE_COLUMN]].isna().any().any():
        raise ValueError("Las fechas de decisión y disponibilidad no admiten nulos")
    if (ordered[LABEL_AVAILABLE_COLUMN] < ordered[TIME_COLUMN]).any():
        raise ValueError("Un label no puede estar disponible antes de decision_date")

    ordered = ordered.sort_values(TIME_COLUMN, kind="stable").reset_index(drop=True)
    validation_start = ordered.iloc[int(len(ordered) * 0.65)][TIME_COLUMN]
    test_start = ordered.iloc[int(len(ordered) * 0.85)][TIME_COLUMN]

    train = ordered.loc[
        ordered[TIME_COLUMN].lt(validation_start)
        & ordered[LABEL_AVAILABLE_COLUMN].le(validation_start)
    ].copy()
    validation = ordered.loc[
        ordered[TIME_COLUMN].ge(validation_start)
        & ordered[TIME_COLUMN].lt(test_start)
        & ordered[LABEL_AVAILABLE_COLUMN].le(test_start)
    ].copy()
    test = ordered.loc[ordered[TIME_COLUMN].ge(test_start)].copy()

    if train.empty or validation.empty or test.empty:
        raise ValueError(
            "Las fechas no dejan cohortes maduras; amplíe el rango temporal"
        )
    if not (
        train[TIME_COLUMN].max() < validation[TIME_COLUMN].min()
        and validation[TIME_COLUMN].max() < test[TIME_COLUMN].min()
    ):
        raise AssertionError("El split temporal quedó solapado")
    if train[LABEL_AVAILABLE_COLUMN].max() > validation_start:
        raise AssertionError("Train contiene labels inmaduros en validation_start")
    if validation[LABEL_AVAILABLE_COLUMN].max() > test_start:
        raise AssertionError("Validation contiene labels inmaduros en test_start")

    return train, validation, test


def build_pipeline() -> Pipeline:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("model", LogisticRegression(max_iter=2_000)),
        ]
    )


def _validated_binary_inputs(
    y_true: pd.Series | np.ndarray,
    probabilities: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    raw_observed = np.asarray(y_true)
    if raw_observed.ndim != 1:
        raise ValueError("y_true debe ser un vector unidimensional")
    if pd.isna(raw_observed).any() or not np.isin(raw_observed, [0, 1]).all():
        raise ValueError("y_true debe contener exclusivamente 0 y 1, sin nulos")

    try:
        scores = np.asarray(probabilities, dtype=float)
    except (TypeError, ValueError) as error:
        raise ValueError("probabilities debe ser un vector numérico") from error
    if scores.ndim != 1:
        raise ValueError("probabilities debe ser un vector unidimensional")
    if len(raw_observed) != len(scores) or len(scores) == 0:
        raise ValueError("y_true y probabilities deben tener igual longitud no vacía")
    if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError("probabilities debe contener valores finitos en [0, 1]")

    return raw_observed.astype(int), scores


def _validated_cost(value: float, name: str) -> float:
    numeric = float(value)
    if not np.isfinite(numeric) or numeric < 0:
        raise ValueError(f"{name} debe ser finito y no negativo")
    return numeric


def threshold_table(
    y_true: pd.Series | np.ndarray,
    probabilities: np.ndarray,
    *,
    cost_fn: float,
    cost_fp: float,
) -> pd.DataFrame:
    """Evalúa cada política distinta inducida por los scores observados."""
    observed, scores = _validated_binary_inputs(y_true, probabilities)
    false_negative_cost = _validated_cost(cost_fn, "cost_fn")
    false_positive_cost = _validated_cost(cost_fp, "cost_fp")

    # Las predicciones solo cambian al cruzar un score observado. El valor >1
    # representa explícitamente la política factible de cero alertas.
    candidates = np.unique(np.r_[0.0, scores, np.nextafter(1.0, np.inf)])
    rows: list[dict[str, float | int]] = []

    for threshold in candidates:
        predicted = (scores >= threshold).astype(int)
        tn, fp, fn, tp = confusion_matrix(
            observed, predicted, labels=[0, 1]
        ).ravel()
        rows.append(
            {
                "threshold": float(threshold),
                "tp": int(tp),
                "fp": int(fp),
                "fn": int(fn),
                "tn": int(tn),
                "alerts": int(tp + fp),
                "cost": float(
                    fn * false_negative_cost + fp * false_positive_cost
                ),
            }
        )

    return pd.DataFrame(rows)


def select_threshold(
    y_true: pd.Series | np.ndarray,
    probabilities: np.ndarray,
    *,
    cost_fn: float,
    cost_fp: float,
    max_alerts: int | None = None,
) -> tuple[dict[str, float | int] | None, pd.DataFrame]:
    if max_alerts is not None:
        if isinstance(max_alerts, bool) or not isinstance(max_alerts, (int, np.integer)):
            raise ValueError("max_alerts debe ser un entero no negativo")
        if max_alerts < 0:
            raise ValueError("max_alerts debe ser un entero no negativo")

    table = threshold_table(
        y_true,
        probabilities,
        cost_fn=cost_fn,
        cost_fp=cost_fp,
    )
    feasible = table if max_alerts is None else table.loc[table["alerts"] <= max_alerts]
    if feasible.empty:
        return None, table

    best = feasible.sort_values(
        ["cost", "alerts", "threshold"],
        ascending=[True, True, False],
    ).iloc[0]
    return best.to_dict(), table


def calibration_table(
    y_true: pd.Series | np.ndarray,
    probabilities: np.ndarray,
    *,
    n_bins: int = 10,
) -> pd.DataFrame:
    """Resume calibración en intervalos fijos; no ajusta un calibrador."""
    observed, scores = _validated_binary_inputs(y_true, probabilities)
    if isinstance(n_bins, bool) or not isinstance(n_bins, (int, np.integer)):
        raise ValueError("n_bins debe ser un entero positivo")
    if n_bins <= 0:
        raise ValueError("n_bins debe ser un entero positivo")

    bin_ids = np.minimum((scores * n_bins).astype(int), n_bins - 1)
    rows: list[dict[str, float | int]] = []
    for bin_id in range(n_bins):
        mask = bin_ids == bin_id
        if not mask.any():
            continue
        mean_probability = float(scores[mask].mean())
        event_rate = float(observed[mask].mean())
        rows.append(
            {
                "bin": int(bin_id),
                "lower": float(bin_id / n_bins),
                "upper": float((bin_id + 1) / n_bins),
                "n": int(mask.sum()),
                "mean_probability": mean_probability,
                "event_rate": event_rate,
                "gap_observed_minus_predicted": event_rate - mean_probability,
            }
        )
    return pd.DataFrame(rows)


def evaluate(
    y_true: pd.Series | np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    *,
    cost_fn: float,
    cost_fp: float,
    reference_prevalence: float,
    design_max_alert_rate: float,
) -> dict[str, MetricValue]:
    observed, scores = _validated_binary_inputs(y_true, probabilities)
    false_negative_cost = _validated_cost(cost_fn, "cost_fn")
    false_positive_cost = _validated_cost(cost_fp, "cost_fp")
    threshold_value = float(threshold)
    if not np.isfinite(threshold_value):
        raise ValueError("threshold debe ser finito")
    if not 0 <= reference_prevalence <= 1:
        raise ValueError("reference_prevalence debe estar en [0, 1]")
    if not 0 <= design_max_alert_rate <= 1:
        raise ValueError("design_max_alert_rate debe estar en [0, 1]")

    predicted = (scores >= threshold_value).astype(int)
    tn, fp, fn, tp = confusion_matrix(
        observed, predicted, labels=[0, 1]
    ).ravel()
    alerts = int(tp + fp)
    capacity_reference = int(len(observed) * design_max_alert_rate)

    epsilon = np.finfo(float).eps
    baseline_probability = float(
        np.clip(reference_prevalence, epsilon, 1.0 - epsilon)
    )
    baseline_scores = np.full(len(observed), baseline_probability)
    model_brier = float(brier_score_loss(observed, scores))
    baseline_brier = float(brier_score_loss(observed, baseline_scores))
    model_log_loss = float(log_loss(observed, scores, labels=[0, 1]))
    baseline_log_loss = float(
        log_loss(observed, baseline_scores, labels=[0, 1])
    )
    has_both_classes = np.unique(observed).size == 2

    return {
        "n": int(len(observed)),
        "prevalence": float(observed.mean()),
        "reference_prevalence_train": float(reference_prevalence),
        "roc_auc": (
            float(roc_auc_score(observed, scores)) if has_both_classes else float("nan")
        ),
        "average_precision": float(average_precision_score(observed, scores)),
        "log_loss": model_log_loss,
        "log_loss_baseline": baseline_log_loss,
        "log_loss_improvement": baseline_log_loss - model_log_loss,
        "brier": model_brier,
        "brier_baseline": baseline_brier,
        "brier_skill": (
            1.0 - model_brier / baseline_brier
            if baseline_brier > 0
            else float("nan")
        ),
        "threshold": threshold_value,
        "precision": float(precision_score(observed, predicted, zero_division=0)),
        "recall": float(recall_score(observed, predicted, zero_division=0)),
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
        "alerts": alerts,
        "alert_rate": float(alerts / len(observed)),
        "design_capacity_reference": capacity_reference,
        "design_budget_breached": bool(alerts > capacity_reference),
        "cost": float(fn * false_negative_cost + fp * false_positive_cost),
    }


def train_and_select(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    *,
    cost_fn: float = 2_000_000,
    cost_fp: float = 25_000,
    max_alert_rate: float = 0.12,
) -> SelectionResult:
    """Entrena y congela pipeline/threshold sin acceder al holdout."""
    if not 0 <= max_alert_rate <= 1:
        raise ValueError("max_alert_rate debe estar en [0, 1]")
    _validated_cost(cost_fn, "cost_fn")
    _validated_cost(cost_fp, "cost_fp")
    if set(FEATURE_COLUMNS) & FORBIDDEN_FEATURES:
        raise AssertionError("La lista de features contiene columnas prohibidas")

    validation_start = validation[TIME_COLUMN].min()
    if train[LABEL_AVAILABLE_COLUMN].max() > validation_start:
        raise ValueError("Train incluye labels no disponibles en validation_start")

    pipeline = build_pipeline()
    pipeline.fit(train[FEATURE_COLUMNS], train[TARGET])
    validation_probability = pipeline.predict_proba(validation[FEATURE_COLUMNS])[:, 1]

    design_capacity = int(len(validation) * max_alert_rate)
    best, _ = select_threshold(
        validation[TARGET],
        validation_probability,
        cost_fn=cost_fn,
        cost_fp=cost_fp,
        max_alerts=design_capacity,
    )
    if best is None:
        raise RuntimeError("Ninguna política satisface el presupuesto de diseño")

    selected_threshold = float(best["threshold"])
    reference_prevalence = float(train[TARGET].mean())
    validation_metrics = evaluate(
        validation[TARGET],
        validation_probability,
        selected_threshold,
        cost_fn=cost_fn,
        cost_fp=cost_fp,
        reference_prevalence=reference_prevalence,
        design_max_alert_rate=max_alert_rate,
    )
    calibration = calibration_table(
        validation[TARGET], validation_probability
    ).to_dict(orient="records")

    return SelectionResult(
        threshold=selected_threshold,
        validation=validation_metrics,
        validation_calibration=calibration,
        sizes={"train": len(train), "validation": len(validation)},
        as_of={"validation_start": validation_start.isoformat()},
        reference_prevalence=reference_prevalence,
        cost_fn=float(cost_fn),
        cost_fp=float(cost_fp),
        design_max_alert_rate=float(max_alert_rate),
        pipeline=pipeline,
    )


def evaluate_holdout(
    selection: SelectionResult,
    holdout: pd.DataFrame,
) -> HoldoutResult:
    """Abre el holdout con pipeline y threshold ya congelados."""
    probability = selection.pipeline.predict_proba(
        holdout[FEATURE_COLUMNS]
    )[:, 1]
    metrics = evaluate(
        holdout[TARGET],
        probability,
        selection.threshold,
        cost_fn=selection.cost_fn,
        cost_fp=selection.cost_fp,
        reference_prevalence=selection.reference_prevalence,
        design_max_alert_rate=selection.design_max_alert_rate,
    )
    calibration = calibration_table(
        holdout[TARGET], probability
    ).to_dict(orient="records")
    return HoldoutResult(metrics=metrics, calibration=calibration)


def run_lab(
    *,
    seed: int = 42,
    cost_fn: float = 2_000_000,
    cost_fp: float = 25_000,
    max_alert_rate: float = 0.12,
    open_holdout: bool = False,
) -> tuple[SelectionResult, HoldoutResult | None]:
    frame = make_synthetic_dataset(seed=seed)
    train, validation, holdout_frame = temporal_split(frame)
    selection = train_and_select(
        train,
        validation,
        cost_fn=cost_fn,
        cost_fp=cost_fp,
        max_alert_rate=max_alert_rate,
    )
    selection = replace(
        selection,
        sizes={
            **selection.sizes,
            "holdout_reserved": len(holdout_frame),
            "excluded_immature": len(frame)
            - len(train)
            - len(validation)
            - len(holdout_frame),
        },
        as_of={
            **selection.as_of,
            "test_start": holdout_frame[TIME_COLUMN].min().isoformat(),
        },
    )

    holdout = (
        evaluate_holdout(selection, holdout_frame) if open_holdout else None
    )
    return selection, holdout


def _selection_payload(selection: SelectionResult) -> dict[str, object]:
    return {
        "threshold": selection.threshold,
        "validation": selection.validation,
        "validation_calibration": selection.validation_calibration,
        "sizes": selection.sizes,
        "as_of": selection.as_of,
        "design_policy": {
            "max_alert_rate": selection.design_max_alert_rate,
            "meaning": (
                "presupuesto de diseño en validation; un threshold fijo no "
                "garantiza la misma tasa fuera de muestra"
            ),
        },
        "holdout_opened": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--open-holdout",
        action="store_true",
        help="evalúa una sola vez el último periodo con la política congelada",
    )
    args = parser.parse_args()

    selection, holdout = run_lab(open_holdout=args.open_holdout)
    payload = _selection_payload(selection)
    if holdout is not None:
        payload["holdout_opened"] = True
        payload["holdout"] = {
            "metrics": holdout.metrics,
            "calibration": holdout.calibration,
        }

    print(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=True))
    if holdout is None:
        print(
            "\nHoldout reservado. Use --open-holdout solo después de congelar "
            "las decisiones del experimento."
        )


if __name__ == "__main__":
    main()
