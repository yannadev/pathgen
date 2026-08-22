"""Load Pathgen's versioned demo curriculum from ``seed_data``."""

import json
import uuid
from collections import defaultdict
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from curriculum.models import (
    Activity,
    ActivityQuestion,
    AssessmentQuestion,
    ExerciseQuestion,
    Lesson,
)


SEED_NAMESPACE = uuid.UUID("b5e10d9b-df62-5fac-9c2d-f3302a6c0b5c")
SEED_FILES = {
    "lessons": "lessons.json",
    "assessment_questions": "assessment_questions.json",
    "exercise_questions": "exercise_questions.json",
    "activities": "activities.json",
    "activity_questions": "activity_questions.json",
}


def seed_uuid(key):
    return uuid.uuid5(SEED_NAMESPACE, key)


class Command(BaseCommand):
    help = "Load or update Pathgen curriculum data from seed_data JSON files."

    def _load_seed_file(self, name):
        path = Path(settings.BASE_DIR) / "seed_data" / SEED_FILES[name]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise CommandError(f"Seed file is missing: {path}") from error
        except json.JSONDecodeError as error:
            raise CommandError(f"Invalid JSON in {path}: {error}") from error

        if not isinstance(data, list):
            raise CommandError(f"{path.name} must contain a JSON array.")
        return data

    @staticmethod
    def _require(row, field, collection_name):
        value = row.get(field)
        if value is None or value == "":
            raise CommandError(f"{collection_name} entry is missing {field!r}.")
        return value

    def _validate_question(self, row, collection_name, *, require_activity=False):
        key = self._require(row, "key", collection_name)
        options = self._require(row, "options_jsonb", collection_name)
        correct_index = row.get("correct_answer_index")
        if not isinstance(options, list) or len(options) != 4:
            raise CommandError(f"{collection_name} {key!r} must have exactly four options.")
        if not isinstance(correct_index, int) or correct_index not in range(4):
            raise CommandError(
                f"{collection_name} {key!r} must have a correct_answer_index from 0 to 3."
            )
        self._require(row, "question_text", collection_name)
        self._require(row, "hint_text", collection_name) if collection_name != "assessment_questions" else None
        if require_activity and not isinstance(row.get("order_index"), int):
            raise CommandError(f"{collection_name} {key!r} must have an integer order_index.")

    @staticmethod
    def _record_result(counts, model_name, created):
        counts[model_name]["created" if created else "updated"] += 1

    def handle(self, *args, **options):
        seed_data = {name: self._load_seed_file(name) for name in SEED_FILES}
        counts = defaultdict(lambda: {"created": 0, "updated": 0})

        lesson_slugs = set()
        for row in seed_data["lessons"]:
            slug = self._require(row, "slug", "lessons")
            if slug in lesson_slugs:
                raise CommandError(f"Duplicate lesson slug: {slug}")
            lesson_slugs.add(slug)
            if not isinstance(row.get("order_index"), int):
                raise CommandError(f"Lesson {slug!r} must have an integer order_index.")
            if not isinstance(row.get("content_jsonb"), list):
                raise CommandError(f"Lesson {slug!r} content_jsonb must be a JSON array.")

        question_keys = set()
        for collection_name in (
            "assessment_questions",
            "exercise_questions",
            "activity_questions",
        ):
            for row in seed_data[collection_name]:
                self._validate_question(
                    row,
                    collection_name,
                    require_activity=collection_name == "activity_questions",
                )
                key = row["key"]
                if key in question_keys:
                    raise CommandError(f"Duplicate seed question key: {key}")
                question_keys.add(key)

        with transaction.atomic():
            lessons_by_slug = {}
            for row in seed_data["lessons"]:
                lesson, created = Lesson.objects.update_or_create(
                    slug=row["slug"],
                    defaults={
                        "title": self._require(row, "title", "lessons"),
                        "description": row.get("description"),
                        "order_index": row["order_index"],
                        "content_jsonb": row["content_jsonb"],
                    },
                )
                lessons_by_slug[lesson.slug] = lesson
                self._record_result(counts, "lessons", created)

            for row in seed_data["lessons"]:
                prerequisite_slug = row.get("prerequisite_lesson_slug")
                try:
                    prerequisite = (
                        lessons_by_slug[prerequisite_slug]
                        if prerequisite_slug is not None
                        else None
                    )
                except KeyError as error:
                    raise CommandError(
                        f"Lesson {row['slug']!r} references unknown prerequisite "
                        f"{prerequisite_slug!r}."
                    ) from error
                lesson = lessons_by_slug[row["slug"]]
                if lesson.prerequisite_lesson_id != getattr(prerequisite, "id", None):
                    lesson.prerequisite_lesson = prerequisite
                    lesson.save(update_fields=["prerequisite_lesson"])

            for row in seed_data["assessment_questions"]:
                try:
                    lesson = lessons_by_slug[row["lesson_slug"]]
                except KeyError as error:
                    raise CommandError(
                        f"Assessment question {row['key']!r} references unknown lesson "
                        f"{row.get('lesson_slug')!r}."
                    ) from error
                _, created = AssessmentQuestion.objects.update_or_create(
                    id=seed_uuid(row["key"]),
                    defaults={
                        "lesson": lesson,
                        "question_text": row["question_text"],
                        "options_jsonb": row["options_jsonb"],
                        "correct_answer_index": row["correct_answer_index"],
                        "has_image": bool(row.get("has_image", False)),
                        "image_url": row.get("image_url"),
                    },
                )
                self._record_result(counts, "assessment_questions", created)

            for row in seed_data["exercise_questions"]:
                try:
                    lesson = lessons_by_slug[row["lesson_slug"]]
                except KeyError as error:
                    raise CommandError(
                        f"Exercise question {row['key']!r} references unknown lesson "
                        f"{row.get('lesson_slug')!r}."
                    ) from error
                _, created = ExerciseQuestion.objects.update_or_create(
                    id=seed_uuid(row["key"]),
                    defaults={
                        "lesson": lesson,
                        "question_text": row["question_text"],
                        "options_jsonb": row["options_jsonb"],
                        "correct_answer_index": row["correct_answer_index"],
                        "hint_text": row["hint_text"],
                    },
                )
                self._record_result(counts, "exercise_questions", created)

            activities_by_order = {}
            activity_keys = set()
            for row in seed_data["activities"]:
                key = self._require(row, "key", "activities")
                if key in activity_keys:
                    raise CommandError(f"Duplicate activity key: {key}")
                activity_keys.add(key)
                try:
                    lesson_1 = lessons_by_slug[row["lesson_1_slug"]]
                    lesson_2 = lessons_by_slug[row["lesson_2_slug"]]
                except KeyError as error:
                    raise CommandError(
                        f"Activity {key!r} references an unknown lesson."
                    ) from error
                if lesson_2.order_index != lesson_1.order_index + 1:
                    raise CommandError(
                        f"Activity {key!r} must reference consecutive lessons."
                    )
                activity, created = Activity.objects.update_or_create(
                    id=seed_uuid(key),
                    defaults={
                        "title": self._require(row, "title", "activities"),
                        "description": row.get("description"),
                        "order_index": self._require(row, "order_index", "activities"),
                        "lesson_1": lesson_1,
                        "lesson_2": lesson_2,
                    },
                )
                if activity.order_index in activities_by_order:
                    raise CommandError(
                        f"Duplicate activity order_index: {activity.order_index}"
                    )
                activities_by_order[activity.order_index] = activity
                self._record_result(counts, "activities", created)

            for row in seed_data["activity_questions"]:
                try:
                    activity = activities_by_order[row["activity_order_index"]]
                except KeyError as error:
                    raise CommandError(
                        f"Activity question {row['key']!r} references unknown activity "
                        f"order {row.get('activity_order_index')!r}."
                    ) from error
                _, created = ActivityQuestion.objects.update_or_create(
                    id=seed_uuid(row["key"]),
                    defaults={
                        "activity": activity,
                        "question_text": row["question_text"],
                        "options_jsonb": row["options_jsonb"],
                        "correct_answer_index": row["correct_answer_index"],
                        "media_jsonb": row.get("media_jsonb"),
                        "order_index": row["order_index"],
                        "hint_text": row["hint_text"],
                    },
                )
                self._record_result(counts, "activity_questions", created)

        summary = ", ".join(
            f"{name}: {result['created']} created, {result['updated']} updated"
            for name, result in counts.items()
        )
        self.stdout.write(self.style.SUCCESS(f"Content seed complete. {summary}"))
