from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from adaptive.models import BKTModelParameters


class SeedBKTParametersCommandTests(TestCase):
    def test_command_creates_expected_parameters_and_is_idempotent(self):
        output = StringIO()

        call_command("seed_bkt_parameters", stdout=output)
        call_command("seed_bkt_parameters", stdout=output)

        self.assertEqual(BKTModelParameters.objects.count(), 1)
        parameters = BKTModelParameters.objects.get()
        self.assertEqual(parameters.p_learn, Decimal("0.2000"))
        self.assertEqual(parameters.p_slip, Decimal("0.1000"))
        self.assertEqual(parameters.p_guess, Decimal("0.2500"))
