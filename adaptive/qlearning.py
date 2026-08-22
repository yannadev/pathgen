"""State mapping and action selection for Pathgen's Q-learning policy.

The module contains no Django imports.  Q-tables are ordinary mappings and can
optionally be loaded from or saved to the adjacent JSON file.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import TypeAlias

import numpy as np


ACTIONS = ("advance", "review", "retake")
MASTERY_LOW = 0
MASTERY_MEDIUM = 1
MASTERY_HIGH = 2
ATTEMPT_FIRST = 0
ATTEMPT_SECOND = 1
ATTEMPT_THIRD_OR_MORE = 2
DEFAULT_QTABLE_PATH = Path(__file__).with_name("qtable.json")

State: TypeAlias = tuple[int, int]
ActionValues: TypeAlias = Mapping[str, float]
QTable: TypeAlias = Mapping[State, ActionValues]


def _finite_number(value: float, name: str) -> float:
    number = float(value)
    if not np.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _validate_mastery(mastery: float) -> float:
    value = _finite_number(mastery, "mastery")
    if not 0.0 <= value <= 1.0:
        raise ValueError("mastery must be between 0 and 1")
    return value


def _validate_attempt_count(attempt_count: int) -> int:
    if isinstance(attempt_count, (bool, np.bool_)) or not isinstance(
        attempt_count, (int, np.integer)
    ):
        raise TypeError("attempt_count must be an integer")
    value = int(attempt_count)
    if value < 1:
        raise ValueError("attempt_count must be at least 1")
    return value


def _validate_state(state: State) -> State:
    if not isinstance(state, tuple) or len(state) != 2:
        raise ValueError("state must be a (mastery_bin, attempt_bin) tuple")
    mastery_bin, attempt_bin = state
    valid_bins = (0, 1, 2)
    if mastery_bin not in valid_bins or attempt_bin not in valid_bins:
        raise ValueError("state bins must each be 0, 1, or 2")
    return int(mastery_bin), int(attempt_bin)


def get_state(mastery: float, attempt_count: int) -> State:
    """Map mastery and attempt count to one of the nine policy states.

    Mastery below 0.4 is low, 0.4 through below 0.7 is medium, and
    0.7 or above is high. Attempts are grouped as first, second, and third+.
    """
    mastery_value = _validate_mastery(mastery)
    attempts = _validate_attempt_count(attempt_count)

    if mastery_value < 0.4:
        mastery_bin = MASTERY_LOW
    elif mastery_value < 0.7:
        mastery_bin = MASTERY_MEDIUM
    else:
        mastery_bin = MASTERY_HIGH

    if attempts == 1:
        attempt_bin = ATTEMPT_FIRST
    elif attempts == 2:
        attempt_bin = ATTEMPT_SECOND
    else:
        attempt_bin = ATTEMPT_THIRD_OR_MORE

    return mastery_bin, attempt_bin


def rule_based_action(mastery: float, attempt_count: int, session_score: float) -> str:
    """Return the deterministic fallback action used before policy learning.

    A score below 50 takes priority.  Passing learners with high mastery
    advance; learners below high mastery retake once, then review.  The final
    review branch covers inconsistent inputs such as high mastery with a score
    between 50 and 69.
    """
    mastery_value = _validate_mastery(mastery)
    attempts = _validate_attempt_count(attempt_count)
    score = _finite_number(session_score, "session_score")
    if not 0.0 <= score <= 100.0:
        raise ValueError("session_score must be between 0 and 100")

    if score < 50.0:
        return "retake" if attempts < 3 else "review"
    if mastery_value >= 0.7 and score >= 70.0:
        return "advance"
    if mastery_value < 0.7:
        return "retake" if attempts < 2 else "review"
    return "review"


def create_q_table(initial_value: float = 0.0) -> dict[State, dict[str, float]]:
    """Create all nine states with the same initial value for every action."""
    value = _finite_number(initial_value, "initial_value")
    return {
        (mastery_bin, attempt_bin): {action: value for action in ACTIONS}
        for mastery_bin in range(3)
        for attempt_bin in range(3)
    }


def _action_values(state: State, q_table: QTable) -> np.ndarray | None:
    values = q_table.get(state)
    if values is None:
        return None
    missing = set(ACTIONS).difference(values)
    extra = set(values).difference(ACTIONS)
    if missing or extra:
        raise ValueError(f"Q-table state {state} must contain exactly these actions: {ACTIONS}")
    result = np.asarray([values[action] for action in ACTIONS], dtype=float)
    if result.shape != (len(ACTIONS),) or not np.all(np.isfinite(result)):
        raise ValueError(f"Q-table state {state} contains invalid action values")
    return result


def get_action(
    state: State,
    q_table: QTable,
    epsilon: float = 0.1,
    *,
    mastery: float | None = None,
    attempt_count: int | None = None,
    session_score: float | None = None,
    rng: np.random.Generator | None = None,
) -> str:
    """Choose an action using the fallback policy or epsilon-greedy selection.

    A missing state or a state whose action values are all equal is considered
    unlearned and uses the rule-based fallback.  The three fallback inputs are
    therefore required in that case.
    """
    validated_state = _validate_state(state)
    epsilon_value = _finite_number(epsilon, "epsilon")
    if not 0.0 <= epsilon_value <= 1.0:
        raise ValueError("epsilon must be between 0 and 1")
    if not isinstance(q_table, Mapping):
        raise TypeError("q_table must be a mapping")

    values = _action_values(validated_state, q_table)
    if values is None or np.allclose(values, values[0]):
        if mastery is None or attempt_count is None or session_score is None:
            raise ValueError(
                "mastery, attempt_count, and session_score are required for an unlearned state"
            )
        return rule_based_action(mastery, attempt_count, session_score)

    generator = rng if rng is not None else np.random.default_rng()
    if not isinstance(generator, np.random.Generator):
        raise TypeError("rng must be a numpy.random.Generator")
    if generator.random() < epsilon_value:
        return str(generator.choice(ACTIONS))

    return ACTIONS[int(np.argmax(values))]


def load_q_table(path: str | Path = DEFAULT_QTABLE_PATH) -> dict[State, dict[str, float]]:
    """Load and validate a JSON Q-table, returning tuple state keys."""
    with Path(path).open(encoding="utf-8") as source:
        raw_table = json.load(source)
    if not isinstance(raw_table, dict):
        raise ValueError("Q-table JSON must contain an object")

    table: dict[State, dict[str, float]] = {}
    for raw_state, raw_values in raw_table.items():
        try:
            parts = tuple(int(part) for part in raw_state.split(","))
        except (AttributeError, TypeError, ValueError) as error:
            raise ValueError(f"invalid Q-table state key: {raw_state!r}") from error
        state = _validate_state(parts)  # type: ignore[arg-type]
        if state in table:
            raise ValueError(f"duplicate Q-table state: {state}")
        if not isinstance(raw_values, dict):
            raise ValueError(f"Q-table state {state} must contain an object")
        values = _action_values(state, {state: raw_values})
        assert values is not None
        table[state] = {action: float(values[index]) for index, action in enumerate(ACTIONS)}

    expected_states = set(create_q_table())
    if set(table) != expected_states:
        raise ValueError("Q-table must contain all nine mastery/attempt states")
    return table


def save_q_table(q_table: QTable, path: str | Path = DEFAULT_QTABLE_PATH) -> None:
    """Validate and save a complete Q-table in its JSON representation."""
    serializable: dict[str, dict[str, float]] = {}
    for state in create_q_table():
        values = _action_values(state, q_table)
        if values is None:
            raise ValueError("Q-table must contain all nine mastery/attempt states")
        serializable[f"{state[0]},{state[1]}"] = {
            action: float(values[index]) for index, action in enumerate(ACTIONS)
        }
    if len(q_table) != 9:
        raise ValueError("Q-table must contain exactly nine states")
    with Path(path).open("w", encoding="utf-8") as destination:
        json.dump(serializable, destination, indent=2)
        destination.write("\n")
