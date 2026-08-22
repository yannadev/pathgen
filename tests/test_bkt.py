import unittest

import numpy as np

from adaptive.bkt import init_mastery, update_mastery


class InitMasteryTests(unittest.TestCase):
    def test_no_assessment_evidence_uses_neutral_prior(self):
        self.assertEqual(init_mastery(0, 0, 0.25), 0.5)

    def test_initial_mastery_applies_guess_adjustment(self):
        self.assertAlmostEqual(init_mastery(4, 5, 0.25), 0.65)
        self.assertAlmostEqual(init_mastery(5, 5, 0.25), 0.75)
        self.assertAlmostEqual(init_mastery(0, 5, 0.25), 0.25)

    def test_initial_mastery_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            init_mastery(2, 1, 0.25)
        with self.assertRaises(ValueError):
            init_mastery(0, 0, 1.1)
        with self.assertRaises(TypeError):
            init_mastery(1.0, 2, 0.25)


class UpdateMasteryTests(unittest.TestCase):
    def test_update_matches_documented_bayesian_formula(self):
        likelihood_known = (1 - 0.1) ** 4 * 0.1
        likelihood_unknown = 0.25**4 * (1 - 0.25)
        posterior = (0.5 * likelihood_known) / (
            0.5 * likelihood_known + 0.5 * likelihood_unknown
        )
        expected = posterior + (1 - posterior) * 0.2

        self.assertAlmostEqual(
            update_mastery(0.5, 4, 1, 0.2, 0.1, 0.25),
            expected,
        )

    def test_update_is_stable_for_long_sessions(self):
        result = update_mastery(0.5, 1000, 1000, 0.2, 0.1, 0.25)
        self.assertTrue(np.isfinite(result))
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 1.0)

    def test_learning_transition_applies_with_no_new_evidence(self):
        self.assertAlmostEqual(update_mastery(0.5, 0, 0, 0.2, 0.1, 0.25), 0.6)

    def test_impossible_evidence_is_rejected(self):
        with self.assertRaises(ValueError):
            update_mastery(0.5, 0, 1, 0.2, 0.0, 1.0)

    def test_update_rejects_invalid_probabilities_and_counts(self):
        with self.assertRaises(ValueError):
            update_mastery(-0.1, 1, 0, 0.2, 0.1, 0.25)
        with self.assertRaises(ValueError):
            update_mastery(0.5, -1, 0, 0.2, 0.1, 0.25)


if __name__ == "__main__":
    unittest.main()
