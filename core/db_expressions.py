"""Cross-database expressions used by model constraints."""

from django.db import models


class JsonArrayLength(models.Func):
    """Return a JSON array's length on SQLite and PostgreSQL."""

    function = "json_array_length"
    output_field = models.IntegerField()
    arity = 1

    def as_postgresql(self, compiler, connection, **extra_context):
        return super().as_sql(
            compiler,
            connection,
            function="jsonb_array_length",
            **extra_context,
        )
