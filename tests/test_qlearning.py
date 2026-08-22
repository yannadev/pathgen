import tempfile
import unittest
from pathlib import Path

import numpy as np

from adaptive.qlearning import (
    ACTIONS,
    create_q_table,
    get_action,
    get_state,
    load_q_table,
    rule_based_action,
    save_q_table,
)


class StateMappingTests(unittest.TestCase):
    def test_mastery_boundaries_and_attempt_bins(self):
        self.assertEqual(get_state(0.0, 1), (0, 0))
        self.assertEqual(get_state(0.3999, 2), (0, 1))
        self.assertEqual(get_state(0.4, 3), (1, 2))
        self.assertEqual(get_state(0.6999, 10), (1, 2))
        self.assertEqual(get_state(0.7, 1), (2, 0))
        self.assertEqual(get_state(1.0, 2), (2, 1))

    def test_invalid_state_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            get_state(1.01, 1)
        with self.assertRaises(ValueError):
            get_state(0.5, 0)
        with self.assertRaises(TypeError):
            get_state(0.5, 1.5)


class RuleFallbackTests(unittest.TestCase):
    def test_high_mastery_and_passing_score_advances(self):
        self.assertEqual(rule_based_action(0.7, 1, 70), "advance")

    def test_low_mastery_retakes_first_attempt_then_reviews(self):
        self.assertEqual(rule_based_action(0.6, 1, 65), "retake")
        self.assertEqual(rule_based_action(0.6, 2, 65), "review")

    def test_very_low_score_rule_has_priority(self):
        self.assertEqual(rule_based_action(0.9, 2, 49), "retake")
        self.assertEqual(rule_based_action(0.9, 3, 49), "review")

    def test_high_mastery_without_passing_score_reviews(self):
        self.assertEqual(rule_based_action(0.9, 1, 60), "review")


class QTableTests(unittest.TestCase):
    def test_initial_table_has_nine_states_and_three_actions(self):
        table = create_q_table()
        self.assertEqual(len(table), 9)
        self.assertTrue(all(tuple(values) == ACTIONS for values in table.values()))

    def test_default_json_table_loads(self):
        self.assertEqual(load_q_table(), create_q_table())

    def test_table_round_trip(self):
        table = create_q_table()
        table[(2, 0)]["advance"] = 1.5
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "qtable.json"
            save_q_table(table, path)
            self.assertEqual(load_q_table(path), table)

    def test_unlearned_state_uses_rule_fallback(self):
        action = get_action(
            (2, 0),
            create_q_table(),
            mastery=0.8,
            attempt_count=1,
            session_score=85,
        )
        self.assertEqual(action, "advance")

    def test_unlearned_state_requires_fallback_context(self):
        with self.assertRaises(ValueError):
            get_action((0, 0), create_q_table())

    def test_exploitation_selects_highest_q_value(self):
        table = create_q_table()
        table[(1, 1)] = {"advance": 0.1, "review": 0.8, "retake": -0.2}
        self.assertEqual(get_action((1, 1), table, epsilon=0), "review")

    def test_equal_best_q_values_use_documented_action_order(self):
        table = create_q_table()
        table[(1, 1)] = {"advance": 0.8, "review": 0.8, "retake": 0.2}

        self.assertEqual(get_action((1, 1), table, epsilon=0), "advance")

    def test_learned_state_does_not_require_fallback_context(self):
        table = create_q_table()
        table[(2, 0)] = {"advance": 1.0, "review": 0.0, "retake": 0.0}

        self.assertEqual(get_action((2, 0), table, epsilon=0), "advance")

    def test_exploration_is_seedable_and_returns_known_action(self):
        table = create_q_table()
        table[(1, 1)] = {"advance": 0.1, "review": 0.8, "retake": -0.2}
        first = get_action(
            (1, 1), table, epsilon=1, rng=np.random.default_rng(42)
        )
        second = get_action(
            (1, 1), table, epsilon=1, rng=np.random.default_rng(42)
        )
        self.assertIn(first, ACTIONS)
        self.assertEqual(first, second)

    def test_malformed_tables_and_invalid_epsilon_are_rejected(self):
        table = create_q_table()
        table[(0, 0)] = {"advance": 0.1, "review": 0.2}
        with self.assertRaises(ValueError):
            get_action((0, 0), table)

        with self.assertRaises(ValueError):
            get_action((0, 0), create_q_table(), epsilon=1.1)

    def test_loading_an_incomplete_json_table_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "incomplete.json"
            path.write_text('{"0,0": {"advance": 0, "review": 0, "retake": 0}}')

            with self.assertRaises(ValueError):
                load_q_table(path)


if __name__ == "__main__":
    unittest.main()
