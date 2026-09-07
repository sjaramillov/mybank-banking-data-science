"""Pruebas de contratos metodológicos del laboratorio de clasificación."""

from __future__ import annotations

import importlib
import os
import unittest

import numpy as np
import pandas as pd

from datos import (
    FEATURE_COLUMNS,
    FORBIDDEN_FEATURES,
    LABEL_AVAILABLE_COLUMN,
    LABEL_HORIZON_DAYS,
    TARGET,
    TIME_COLUMN,
    make_synthetic_dataset,
)


LAB_MODULE = os.environ.get("LAB_MODULE", "solucion")
lab = importlib.import_module(LAB_MODULE)


class BankingClassificationLabTests(unittest.TestCase):
    def test_features_exclude_future_information_and_identifiers(self) -> None:
        self.assertTrue(set(FEATURE_COLUMNS).isdisjoint(FORBIDDEN_FEATURES))

    def test_dataset_makes_label_availability_explicit(self) -> None:
        frame = make_synthetic_dataset(n_rows=1_000, seed=3)
        expected = frame[TIME_COLUMN] + pd.Timedelta(days=LABEL_HORIZON_DAYS)
        pd.testing.assert_series_equal(
            frame[LABEL_AVAILABLE_COLUMN],
            expected.rename(LABEL_AVAILABLE_COLUMN),
        )

    def test_temporal_split_is_ordered_purged_and_nonempty(self) -> None:
        frame = make_synthetic_dataset(n_rows=2_000, seed=7).sample(
            frac=1.0, random_state=99
        )
        train, validation, holdout = lab.temporal_split(frame)

        validation_start = validation[TIME_COLUMN].min()
        test_start = holdout[TIME_COLUMN].min()

        self.assertGreater(len(train), 0)
        self.assertGreater(len(validation), 0)
        self.assertGreater(len(holdout), 0)
        self.assertLess(train[TIME_COLUMN].max(), validation_start)
        self.assertLess(validation[TIME_COLUMN].max(), test_start)
        self.assertLessEqual(
            train[LABEL_AVAILABLE_COLUMN].max(), validation_start
        )
        self.assertLessEqual(
            validation[LABEL_AVAILABLE_COLUMN].max(), test_start
        )
        self.assertLess(
            len(train) + len(validation) + len(holdout), len(frame)
        )

    def test_pipeline_handles_missing_and_unseen_category(self) -> None:
        frame = make_synthetic_dataset(n_rows=2_000, seed=11)
        train, validation, _ = lab.temporal_split(frame)
        pipeline = lab.build_pipeline().fit(
            train[FEATURE_COLUMNS], train[TARGET]
        )

        sample = validation[FEATURE_COLUMNS].head(3).copy()
        sample.loc[sample.index[0], "channel"] = "new_channel"
        sample.loc[sample.index[1], "declared_income"] = np.nan
        probability = pipeline.predict_proba(sample)[:, 1]

        self.assertEqual(len(probability), 3)
        self.assertTrue(np.all((probability >= 0.0) & (probability <= 1.0)))

    def test_threshold_selection_is_exact_and_respects_capacity(self) -> None:
        y_true = np.array([0, 0, 0, 1, 1, 1])
        probabilities = np.array([0.05, 0.15, 0.65, 0.45, 0.75, 0.95])
        best, table = lab.select_threshold(
            y_true,
            probabilities,
            cost_fn=100.0,
            cost_fp=5.0,
            max_alerts=2,
        )

        self.assertIsNotNone(best)
        assert best is not None
        feasible = table.loc[table["alerts"] <= 2]
        self.assertLessEqual(int(best["alerts"]), 2)
        self.assertEqual(float(best["cost"]), float(feasible["cost"].min()))
        self.assertAlmostEqual(float(best["threshold"]), 0.75)
        self.assertEqual(int(best["tp"]), 2)
        self.assertEqual(int(best["fp"]), 0)
        self.assertEqual(int(best["fn"]), 1)
        self.assertEqual(float(best["cost"]), 100.0)
        self.assertEqual(
            len(table), len(np.unique(np.r_[0.0, probabilities, np.nextafter(1.0, np.inf)]))
        )

        no_alerts, _ = lab.select_threshold(
            y_true,
            probabilities,
            cost_fn=100.0,
            cost_fp=5.0,
            max_alerts=0,
        )
        self.assertIsNotNone(no_alerts)
        assert no_alerts is not None
        self.assertEqual(int(no_alerts["alerts"]), 0)
        self.assertGreater(float(no_alerts["threshold"]), 1.0)

    def test_threshold_inputs_are_validated(self) -> None:
        valid_y = np.array([0, 1])
        valid_p = np.array([0.1, 0.9])
        invalid_calls = [
            lambda: lab.select_threshold(
                [0, 1, 0], valid_p, cost_fn=1, cost_fp=1
            ),
            lambda: lab.select_threshold(
                [0, 2], valid_p, cost_fn=1, cost_fp=1
            ),
            lambda: lab.select_threshold(
                valid_y, [0.1, np.nan], cost_fn=1, cost_fp=1
            ),
            lambda: lab.select_threshold(
                valid_y, [0.1, 1.2], cost_fn=1, cost_fp=1
            ),
            lambda: lab.select_threshold(
                valid_y, valid_p, cost_fn=-1, cost_fp=1
            ),
            lambda: lab.select_threshold(
                valid_y, valid_p, cost_fn=1, cost_fp=1, max_alerts=-1
            ),
            lambda: lab.select_threshold(
                valid_y, valid_p, cost_fn=1, cost_fp=1, max_alerts=1.5
            ),
        ]
        for invalid_call in invalid_calls:
            with self.subTest(call=invalid_call):
                with self.assertRaises(ValueError):
                    invalid_call()

    def test_calibration_table_preserves_all_observations(self) -> None:
        y_true = np.array([0, 0, 1, 1, 1])
        probabilities = np.array([0.05, 0.15, 0.25, 0.75, 1.0])
        table = lab.calibration_table(y_true, probabilities, n_bins=5)

        self.assertEqual(int(table["n"].sum()), len(y_true))
        self.assertTrue(
            {
                "mean_probability",
                "event_rate",
                "gap_observed_minus_predicted",
            }.issubset(table.columns)
        )

    def test_evaluate_reports_design_budget_without_promising_it(self) -> None:
        metrics = lab.evaluate(
            np.array([1, 0, 0, 0]),
            np.array([0.9, 0.8, 0.7, 0.1]),
            0.5,
            cost_fn=100.0,
            cost_fp=5.0,
            reference_prevalence=0.25,
            design_max_alert_rate=0.25,
        )

        self.assertEqual(metrics["alerts"], 3)
        self.assertAlmostEqual(float(metrics["alert_rate"]), 0.75)
        self.assertEqual(metrics["design_capacity_reference"], 1)
        self.assertIs(metrics["design_budget_breached"], True)
        self.assertEqual(metrics["tp"], 1)
        self.assertEqual(metrics["fp"], 2)
        self.assertEqual(metrics["fn"], 0)
        self.assertEqual(metrics["tn"], 1)
        self.assertEqual(metrics["cost"], 10.0)
        self.assertAlmostEqual(float(metrics["brier"]), 0.2875)
        self.assertAlmostEqual(float(metrics["brier_baseline"]), 0.1875)
        self.assertIn("log_loss_baseline", metrics)

    def test_default_flow_keeps_holdout_closed(self) -> None:
        selection, holdout = lab.run_lab(seed=42, open_holdout=False)

        self.assertIsNone(holdout)
        self.assertLessEqual(
            int(selection.validation["alerts"]),
            int(selection.validation["design_capacity_reference"]),
        )
        self.assertIs(selection.validation["design_budget_breached"], False)
        self.assertIn("brier_baseline", selection.validation)
        self.assertIn("log_loss_baseline", selection.validation)
        self.assertGreater(selection.sizes["excluded_immature"], 0)


if __name__ == "__main__":
    unittest.main()
