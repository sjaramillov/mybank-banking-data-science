"""Pruebas de contratos metodológicos, no de una cifra favorable en holdout."""

from __future__ import annotations

import importlib
import math
import os
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from datos import (
    FEATURE_COLUMNS,
    FORBIDDEN_FEATURES,
    LABEL_AVAILABLE_COLUMN,
    LABEL_DELAY_HOURS,
    TARGET,
    TIME_COLUMN,
    make_synthetic_dataset,
)


LAB_MODULE = os.environ.get("LAB_MODULE", "solucion")
lab = importlib.import_module(LAB_MODULE)


class BankingRegressionLabTests(unittest.TestCase):
    def test_features_exclude_future_information_and_identifiers(self) -> None:
        self.assertTrue(set(FEATURE_COLUMNS).isdisjoint(FORBIDDEN_FEATURES))
        self.assertIn("resolved_at", FORBIDDEN_FEATURES)
        self.assertIn("final_root_cause", FORBIDDEN_FEATURES)

    def test_dataset_makes_label_availability_explicit(self) -> None:
        frame = make_synthetic_dataset(n_rows=1_000, seed=3)
        expected = frame[TIME_COLUMN] + pd.Timedelta(hours=LABEL_DELAY_HOURS)
        pd.testing.assert_series_equal(
            frame[LABEL_AVAILABLE_COLUMN],
            expected.rename(LABEL_AVAILABLE_COLUMN),
        )
        self.assertTrue(
            (frame["resolved_at"] <= frame[LABEL_AVAILABLE_COLUMN]).all()
        )

    def test_temporal_split_is_ordered_purged_and_nonempty(self) -> None:
        frame = make_synthetic_dataset(n_rows=2_000, seed=7).sample(
            frac=1.0, random_state=99
        )
        train, validation, holdout = lab.temporal_split(frame)
        validation_start = validation[TIME_COLUMN].min()
        holdout_start = holdout[TIME_COLUMN].min()

        self.assertGreater(len(train), 0)
        self.assertGreater(len(validation), 0)
        self.assertGreater(len(holdout), 0)
        self.assertLess(train[TIME_COLUMN].max(), validation_start)
        self.assertLess(validation[TIME_COLUMN].max(), holdout_start)
        self.assertLessEqual(
            train[LABEL_AVAILABLE_COLUMN].max(), validation_start
        )
        self.assertLessEqual(
            validation[LABEL_AVAILABLE_COLUMN].max(), holdout_start
        )
        self.assertLess(len(train) + len(validation) + len(holdout), len(frame))

    def test_all_model_families_handle_missing_and_unseen_category(self) -> None:
        frame = make_synthetic_dataset(n_rows=900, seed=11)
        train, validation, _ = lab.temporal_split(frame)
        sample = validation[FEATURE_COLUMNS].head(3).copy()
        sample.loc[sample.index[0], "engine_family"] = "new_engine"
        sample.loc[sample.index[1], "io_latency_ms"] = np.nan

        families_seen: set[str] = set()
        for spec in lab.candidate_specs():
            family = str(spec["family"])
            if family in families_seen:
                continue
            families_seen.add(family)
            with self.subTest(family=family):
                pipeline = lab.build_pipeline(family, spec["params"]).fit(
                    train[FEATURE_COLUMNS], train[TARGET]
                )
                prediction = pipeline.predict(sample)
                self.assertEqual(len(prediction), 3)
                self.assertTrue(np.isfinite(prediction).all())

        self.assertEqual(
            families_seen,
            {"dummy", "linear", "ridge", "random_forest"},
        )

    def test_metrics_match_hand_calculation(self) -> None:
        metrics = lab.evaluate_regression(
            np.array([100.0, 120.0]),
            np.array([90.0, 140.0]),
        )
        self.assertEqual(metrics["n"], 2)
        self.assertAlmostEqual(float(metrics["mae"]), 15.0)
        self.assertAlmostEqual(float(metrics["rmse"]), math.sqrt(250.0))
        self.assertAlmostEqual(float(metrics["r2"]), -1.5)
        self.assertAlmostEqual(
            float(metrics["mean_residual_observed_minus_predicted"]), -5.0
        )
        self.assertAlmostEqual(float(metrics["median_absolute_error"]), 15.0)
        self.assertAlmostEqual(float(metrics["p90_absolute_error"]), 19.0)

    def test_metric_inputs_reject_invalid_vectors(self) -> None:
        invalid_calls = [
            lambda: lab.evaluate_regression([], []),
            lambda: lab.evaluate_regression([1.0, 2.0], [1.0]),
            lambda: lab.evaluate_regression([[1.0]], [1.0]),
            lambda: lab.evaluate_regression([1.0, np.nan], [1.0, 2.0]),
            lambda: lab.evaluate_regression([1.0, 2.0], [1.0, np.inf]),
        ]
        for invalid_call in invalid_calls:
            with self.subTest(call=invalid_call):
                with self.assertRaises(ValueError):
                    invalid_call()

    def test_segment_errors_preserve_each_population(self) -> None:
        frame = pd.DataFrame(
            {
                TARGET: [10.0, 20.0, 30.0, 40.0],
                "service_tier": ["critical", "critical", "standard", None],
                "engine_family": ["a", "b", "a", "b"],
            }
        )
        table = lab.segment_errors(frame, np.array([12.0, 18.0, 31.0, 35.0]))
        for segment_by in ("service_tier", "engine_family"):
            subset = table.loc[table["segment_by"] == segment_by]
            self.assertEqual(int(subset["n"].sum()), len(frame))
            self.assertTrue({"mae", "rmse", "r2"}.issubset(subset.columns))
        self.assertIn("<MISSING>", set(table["segment"]))

    def test_residual_sign_is_explicit_and_diagnostics_are_finite(self) -> None:
        diagnostics = lab.residual_diagnostics(
            np.array([1.0, 3.0, 5.0]),
            np.array([2.0, 3.0, 4.0]),
        )
        self.assertEqual(
            diagnostics["residual_definition"], "observed_minus_predicted"
        )
        self.assertAlmostEqual(float(diagnostics["mean_residual"]), 0.0)
        self.assertAlmostEqual(float(diagnostics["corr_residual_prediction"]), 1.0)
        self.assertAlmostEqual(float(diagnostics["max_absolute_residual"]), 1.0)

    def test_selection_is_the_lowest_validation_mae_with_declared_tiebreak(self) -> None:
        frame = make_synthetic_dataset(n_rows=1_200, seed=17)
        train, validation, _ = lab.temporal_split(frame)
        selection = lab.train_and_select(train, validation)
        expected = min(
            selection.comparison,
            key=lambda row: (
                float(row["mae"]),
                float(row["rmse"]),
                str(row["model"]),
            ),
        )
        self.assertEqual(selection.selected_model, expected["model"])
        self.assertEqual(selection.selected_family, expected["family"])
        self.assertEqual(selection.selected_params, expected["params"])
        self.assertEqual(selection.validation["mae"], expected["mae"])
        self.assertTrue(
            any(row["family"] == "dummy" for row in selection.comparison)
        )

    def test_default_flow_never_invokes_holdout_evaluation(self) -> None:
        with patch.object(
            lab,
            "evaluate_holdout",
            side_effect=AssertionError("El holdout no debía abrirse"),
        ):
            selection, holdout = lab.run_lab(
                seed=42,
                n_rows=1_200,
                open_holdout=False,
            )
        self.assertIsNone(holdout)
        self.assertGreater(selection.sizes["holdout_reserved"], 0)
        self.assertGreater(selection.sizes["excluded_immature"], 0)

    def test_overlapping_development_cohorts_are_rejected(self) -> None:
        frame = make_synthetic_dataset(n_rows=800, seed=21)
        train, validation, _ = lab.temporal_split(frame)
        contaminated = validation.copy()
        contaminated.loc[contaminated.index[0], TIME_COLUMN] = train[TIME_COLUMN].max()
        with self.assertRaises(ValueError):
            lab.train_and_select(train, contaminated)


if __name__ == "__main__":
    unittest.main()
