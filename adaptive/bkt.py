"""Bayesian Knowledge Tracing calculations.

This module deliberately has no Django dependencies.  It accepts plain numeric
values and returns Python floats so it can be reused by views, jobs, and tests.
"""

from __future__ import annotations

import numpy as np


def _probability(value: float, name: str) -> float:
    """Return *value* as a validated probability."""
    probability = float(value)
    if not np.isfinite(probability) or not 0.0 <= probability <= 1.0:
        raise ValueError(f"{name} must be a finite value between 0 and 1")
    return probability


def _count(value: int, name: str) -> int:
    """Return *value* as a validated non-negative integer count."""
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer")
    count = int(value)
    if count < 0:
        raise ValueError(f"{name} must be non-negative")
    return count


def _log_power(probability: float, exponent: int) -> float:
    """Compute log(probability ** exponent) without underflow."""
    if exponent == 0:
        return 0.0
    if probability == 0.0:
        return -np.inf
    return float(exponent * np.log(probability))


def _log_probability(probability: float) -> float:
    if probability == 0.0:
        return -np.inf
    return float(np.log(probability))


def init_mastery(correct_count: int, total_count: int, p_guess: float) -> float:
    """Estimate initial mastery from an assessment result.

    With no assessment evidence, mastery starts at the neutral prior of 0.5.
    Otherwise the estimate is adjusted for the probability of guessing.
    """
    correct = _count(correct_count, "correct_count")
    total = _count(total_count, "total_count")
    guess = _probability(p_guess, "p_guess")

    if correct > total:
        raise ValueError("correct_count cannot exceed total_count")
    if total == 0:
        return 0.5

    accuracy = np.float64(correct) / np.float64(total)
    p_known = accuracy * (1.0 - guess) + guess * (1.0 - accuracy)
    return float(np.clip(p_known, 0.0, 1.0))


def update_mastery(
    p_known: float,
    n_correct: int,
    n_wrong: int,
    p_learn: float,
    p_slip: float,
    p_guess: float,
) -> float:
    """Update mastery after observing correct and incorrect responses.

    The Bayesian evidence update is followed by the BKT learning transition.
    Log-likelihoods keep the calculation stable for long sessions.
    """
    prior = _probability(p_known, "p_known")
    correct = _count(n_correct, "n_correct")
    wrong = _count(n_wrong, "n_wrong")
    learn = _probability(p_learn, "p_learn")
    slip = _probability(p_slip, "p_slip")
    guess = _probability(p_guess, "p_guess")

    log_known = (
        _log_probability(prior)
        + _log_power(1.0 - slip, correct)
        + _log_power(slip, wrong)
    )
    log_unknown = (
        _log_probability(1.0 - prior)
        + _log_power(guess, correct)
        + _log_power(1.0 - guess, wrong)
    )
    log_evidence = float(np.logaddexp(log_known, log_unknown))

    if np.isneginf(log_evidence):
        raise ValueError("the supplied parameters assign zero probability to this evidence")

    posterior = float(np.exp(log_known - log_evidence))
    updated = posterior + (1.0 - posterior) * learn
    return float(np.clip(updated, 0.0, 1.0))
