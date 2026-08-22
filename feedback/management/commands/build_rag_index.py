"""Build the local lesson-content embedding index."""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from curriculum.models import Lesson
from feedback.chunker import chunk_content
from feedback.clients import embed_many


class Command(BaseCommand):
    help = "Chunk seeded lessons, embed them with OpenAI, and write the RAG index."

    def add_arguments(self, parser):
        parser.add_argument("--source", type=Path, help="Optional lessons JSON path.")
        parser.add_argument("--output", type=Path, help="Optional index output path.")

    def handle(self, *args, **options):
        source_path = options.get("source") or (
            Path(settings.BASE_DIR) / "seed_data" / "lessons.json"
        )
        output_path = options.get("output") or (
            Path(settings.BASE_DIR) / "seed_data" / "lesson_embeddings.json"
        )
        try:
            lesson_rows = json.loads(source_path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise CommandError(f"Lesson seed file is missing: {source_path}") from error
        except json.JSONDecodeError as error:
            raise CommandError(f"Invalid JSON in {source_path}: {error}") from error
        if not isinstance(lesson_rows, list) or not lesson_rows:
            raise CommandError("Lesson seed file must contain a non-empty JSON array.")

        slugs = [row.get("slug") for row in lesson_rows if isinstance(row, dict)]
        if len(slugs) != len(lesson_rows) or any(not slug for slug in slugs):
            raise CommandError("Every lesson seed row must contain a slug.")
        if len(slugs) != len(set(slugs)):
            raise CommandError("Lesson seed file contains duplicate slugs.")

        lessons_by_slug = Lesson.objects.in_bulk(slugs, field_name="slug")
        missing_slugs = [slug for slug in slugs if slug not in lessons_by_slug]
        if missing_slugs:
            raise CommandError(
                "Seed the database before building RAG. Missing lessons: "
                + ", ".join(missing_slugs)
            )

        metadata = []
        for row in lesson_rows:
            content = row.get("content_jsonb")
            if not isinstance(content, list):
                raise CommandError(
                    f"Lesson {row['slug']!r} content_jsonb must be a JSON array."
                )
            chunks = chunk_content(content)
            if not chunks:
                raise CommandError(f"Lesson {row['slug']!r} produced no RAG chunks.")
            lesson = lessons_by_slug[row["slug"]]
            metadata.extend(
                {
                    "id": f"{lesson.slug}:{chunk_index}",
                    "lesson_id": str(lesson.id),
                    "lesson_slug": lesson.slug,
                    "chunk_index": chunk_index,
                    "chunk_text": chunk_text,
                }
                for chunk_index, chunk_text in enumerate(chunks)
            )

        try:
            vectors = embed_many(item["chunk_text"] for item in metadata)
        except Exception as error:
            raise CommandError(f"Embedding generation failed: {error}") from error
        if len(vectors) != len(metadata):
            raise CommandError("Embedding count does not match the chunk count.")

        index = [
            {**item, "vector": vector}
            for item, vector in zip(metadata, vectors, strict=True)
        ]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Built {len(index)} embeddings for {len(lesson_rows)} lessons: "
                f"{output_path}"
            )
        )
