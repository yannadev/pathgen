"""Seed the single global BKT parameter record."""

from decimal import Decimal
from uuid import UUID

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from adaptive.models import BKTModelParameters


PARAMETER_ID = UUID("242cc025-318e-52df-9ff7-f687fbf85407")
DEFAULT_PARAMETERS = {
    "p_learn": Decimal("0.2"),
    "p_slip": Decimal("0.1"),
    "p_guess": Decimal("0.25"),
}


class Command(BaseCommand):
    help = "Create or update the single global BKT model parameter record."

    @transaction.atomic
    def handle(self, *args, **options):
        existing = list(
            BKTModelParameters.objects.select_for_update().order_by("created_at", "id")
        )
        if len(existing) > 1:
            raise CommandError(
                "Expected one global BKT parameter record, "
                f"but found {len(existing)}. Resolve duplicates before seeding."
            )

        if existing:
            parameters = existing[0]
            created = False
            for field, value in DEFAULT_PARAMETERS.items():
                setattr(parameters, field, value)
            parameters.save(update_fields=[*DEFAULT_PARAMETERS, "updated_at"])
        else:
            parameters = BKTModelParameters.objects.create(
                id=PARAMETER_ID,
                **DEFAULT_PARAMETERS,
            )
            created = True

        verb = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} BKT parameters: p_learn={parameters.p_learn}, "
                f"p_slip={parameters.p_slip}, p_guess={parameters.p_guess}"
            )
        )
