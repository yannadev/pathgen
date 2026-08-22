import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from curriculum.models import Lesson
from feedback.chunker import MAX_TOKENS, chunk_content, estimate_tokens
from feedback.clients import EMBEDDING_DIMENSIONS, embed_many, generate_text
from feedback.generator import generate_feedback
from feedback.prompts import build_prompt
from feedback.retriever import build_query, cosine_similarity, retrieve


class ChunkerTests(SimpleTestCase):
    def test_structure_aware_chunks_stay_bounded_and_preserve_examples(self):
        worked_example = "Worked example: " + ("x" * 2100)
        content = [
            {"type": "heading", "text": "Integer operations"},
            {"type": "paragraph", "text": "a" * 1200},
            {"type": "heading", "text": "Worked examples"},
            {"type": "example", "text": worked_example},
            {"type": "paragraph", "text": "b" * 1000},
        ]

        chunks = chunk_content(content)

        self.assertIn(worked_example, chunks)
        self.assertEqual(sum(worked_example in chunk for chunk in chunks), 1)
        self.assertTrue(
            all(
                estimate_tokens(chunk) <= MAX_TOKENS
                for chunk in chunks
                if chunk != worked_example
            )
        )

    def test_chunker_rejects_unstructured_content(self):
        with self.assertRaises(TypeError):
            chunk_content("not-a-list")


@override_settings(
    OPENAI_API_KEY="test-openai-key",
    EMBEDDING_MODEL="text-embedding-3-small",
    GROQ_API_KEY="test-groq-key",
    GROQ_MODEL="gpt-oss-120b",
)
class ClientTests(SimpleTestCase):
    @patch("feedback.clients.OpenAI")
    def test_embed_many_preserves_provider_index_order(self, mock_openai):
        first = [0.1] * EMBEDDING_DIMENSIONS
        second = [0.2] * EMBEDDING_DIMENSIONS
        mock_openai.return_value.embeddings.create.return_value = SimpleNamespace(
            data=[
                SimpleNamespace(index=1, embedding=second),
                SimpleNamespace(index=0, embedding=first),
            ]
        )

        vectors = embed_many(["first", "second"])

        self.assertEqual(vectors, [first, second])
        mock_openai.return_value.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input=["first", "second"],
        )

    @patch("feedback.clients.Groq")
    def test_generate_text_uses_documented_model_and_temperature(self, mock_groq):
        mock_groq.return_value.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="  Keep going.  "))]
        )

        result = generate_text(system_prompt="Tutor", user_prompt="Help")

        self.assertEqual(result, "Keep going.")
        call = mock_groq.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(call["model"], "gpt-oss-120b")
        self.assertEqual(call["temperature"], 0.2)


class RetrieverTests(SimpleTestCase):
    def test_query_cosine_and_top_four_are_lesson_scoped(self):
        wrong = [{"question_text": "Add integers", "hint_text": "Check signs"}]
        chunks = [
            {
                "id": f"lesson-a:{index}",
                "lesson_id": "lesson-a",
                "chunk_text": f"Chunk {index}",
                "vector": vector,
            }
            for index, vector in enumerate(
                ([1, 0], [0.9, 0.1], [0.8, 0.2], [0.7, 0.3], [0, 1])
            )
        ]
        chunks.append(
            {
                "id": "lesson-b:0",
                "lesson_id": "lesson-b",
                "chunk_text": "Wrong lesson",
                "vector": [1, 0],
            }
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "index.json"
            path.write_text(json.dumps(chunks), encoding="utf-8")

            results = retrieve(
                ["lesson-a"],
                wrong,
                index_path=path,
                embed_fn=lambda _query: [1, 0],
            )

        self.assertEqual(build_query(wrong), "Add integers Check signs")
        self.assertEqual(cosine_similarity([1, 0], [1, 0]), 1.0)
        self.assertEqual(
            [chunk["id"] for chunk in results],
            ["lesson-a:0", "lesson-a:1", "lesson-a:2", "lesson-a:3"],
        )

    def test_missing_index_raises_for_orchestrator_to_degrade(self):
        with self.assertRaises(FileNotFoundError):
            retrieve(
                ["lesson-a"],
                [{"question_text": "Question", "hint_text": "Hint"}],
                index_path="missing-index.json",
                embed_fn=lambda _query: [1, 0],
            )


class PromptAndGeneratorTests(SimpleTestCase):
    session_result = {
        "title": "Integer exercise",
        "score": 50,
        "correct_count": 1,
        "total_questions": 2,
    }

    def test_corrective_prompt_contains_evidence_and_grounding_guard(self):
        prompt = build_prompt(
            self.session_result,
            [
                {
                    "question_text": "What is -2 + -3?",
                    "selected_answer": "1",
                    "correct_answer": "-5",
                    "hint_text": "Add absolute values and keep the sign.",
                }
            ],
            [{"chunk_text": "For equal signs, add absolute values."}],
        )

        self.assertIn("Student chose: 1", prompt)
        self.assertIn("Correct answer: -5", prompt)
        self.assertIn("Use ONLY the approved lesson excerpts", prompt)
        self.assertIn("3-5 encouraging sentences", prompt)

    @patch("feedback.generator.generate_text", return_value="Excellent work.")
    @patch("feedback.generator.retrieve")
    def test_perfect_score_skips_retrieval(self, mock_retrieve, _mock_generate):
        result = generate_feedback(
            session_result={**self.session_result, "score": 100, "correct_count": 2},
            wrong_items=[],
            lesson_ids=["lesson-a"],
        )

        self.assertEqual(result, "Excellent work.")
        mock_retrieve.assert_not_called()


class BuildRAGIndexCommandTests(TestCase):
    def test_command_resolves_database_uuid_and_writes_embedded_chunks(self):
        lesson = Lesson.objects.create(
            slug="test-lesson",
            title="Test lesson",
            order_index=1,
            content_jsonb=[],
        )
        seed_rows = [
            {
                "slug": lesson.slug,
                "content_jsonb": [
                    {"type": "heading", "text": "A heading"},
                    {"type": "paragraph", "text": "a" * 1300},
                ],
            }
        ]
        output = StringIO()
        with TemporaryDirectory() as directory:
            source_path = Path(directory) / "lessons.json"
            output_path = Path(directory) / "lesson_embeddings.json"
            source_path.write_text(json.dumps(seed_rows), encoding="utf-8")
            with patch(
                "feedback.management.commands.build_rag_index.embed_many",
                return_value=[[0.25] * EMBEDDING_DIMENSIONS],
            ) as mock_embed:
                call_command(
                    "build_rag_index",
                    source=source_path,
                    output=output_path,
                    stdout=output,
                )
            index = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(len(index), 1)
        self.assertEqual(index[0]["lesson_id"], str(lesson.id))
        self.assertEqual(index[0]["id"], "test-lesson:0")
        self.assertEqual(len(index[0]["vector"]), EMBEDDING_DIMENSIONS)
        mock_embed.assert_called_once()
        self.assertIn("Built 1 embeddings", output.getvalue())
