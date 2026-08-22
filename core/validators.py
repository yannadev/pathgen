"""Reusable model validators."""

from django.core.exceptions import ValidationError


def validate_four_options(value):
    if not isinstance(value, list) or len(value) != 4:
        raise ValidationError("Options must be a JSON array containing exactly four items.")

    if any(not isinstance(option, str) or not option.strip() for option in value):
        raise ValidationError("Every option must be a non-empty string.")
