import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase

from feedback.chunker import chunk_content, estimate_tokens
from feedback.retriever import build_query, cosine_similarity, retrieve


class ChunkerBoundaryTests(SimpleTestCase):
    def test_estimate_tokens_rounds_up_using_documented_ratio(self):
        self.assertEqual(estimate_tokens(""), 0)
        self.assertEqual(estimate_tokens("abc"), 1)
        self.assertEqual(estimate_tokens("abcd"), 1)
        self.assertEqual(estimate_tokens("abcde"), 2)

    def test_heading_starts_a_natural_chunk_boundary_after_minimum(self):
        first_paragraph = "a" * 1200
        second_paragraph = "b" * 1200
        chunks = chunk_content(
            [
                {"type": "heading", "text": "Integers"},
                {"type": "paragraph", "text": first_paragraph},
                {"type": "heading", "text": "Comparing integers"},
                {"type": "paragraph", "text": second_paragraph},
            ]
        )

        self.assertEqual(len(chunks), 2)
        self.assertIn("Integers", chunks[0])
        self.assertNotIn("Comparing integers", chunks[0])
        self.assertIn("Comparing integers", chunks[1])

    def test_trailing_fragment_is_rebalanced_without_splitting_blocks(self):
        first_block = "a" * 1200
        second_block = "b" * 800
        trailing_block = "c" * 800
        chunks = chunk_content(
            [
                {"type": "paragraph", "text": first_block},
                {"type": "paragraph", "text": second_block},
                {"type": "paragraph", "text": trailing_block},
            ]
        )

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0], first_block)
        self.assertIn(second_block, chunks[1])
        self.assertIn(trailing_block, chunks[1])

    def test_invalid_bounds_and_non_string_text_are_rejected(self):
        with self.assertRaises(ValueError):
            chunk_content([], min_tokens=0)
        with self.assertRaises(ValueError):
            chunk_content([], min_tokens=500, max_tokens=300)
        with self.assertRaises(TypeError):
            chunk_content([{"type": "paragraph", "text": 42}])


class RetrieverValidationTests(SimpleTestCase):
    wrong_questions = [{"question_text": "Add signed numbers", "hint_text": "Check signs"}]

    def _write_index(self, chunks):
        directory = TemporaryDirectory()
        path = Path(directory.name) / "index.json"
        path.write_text(json.dumps(chunks), encoding="utf-8")
        self.addCleanup(directory.cleanup)
        return path

    def test_query_skips_blank_parts_and_requires_meaningful_content(self):
        self.assertEqual(
            build_query(
                [
                    {"question_text": "  Compare integers  ", "hint_text": ""},
                    {"question_text": "", "hint_text": "Use the number line."},
                ]
            ),
            "Compare integers Use the number line.",
        )
        with self.assertRaises(ValueError):
            build_query([{"question_text": "", "hint_text": ""}])

    def test_cosine_similarity_rejects_zero_and_mismatched_vectors(self):
        with self.assertRaises(ValueError):
            cosine_similarity([0, 0], [1, 0])
        with self.assertRaises(ValueError):
            cosine_similarity([1, 0], [1, 0, 0])

    def test_retrieval_orders_score_ties_by_chunk_id_and_respects_top_k(self):
        path = self._write_index(
            [
                {
                    "id": "lesson-a:2",
                    "lesson_id": "lesson-a",
                    "chunk_text": "Second matching chunk",
                    "vector": [1, 0],
                },
                {
                    "id": "lesson-a:1",
                    "lesson_id": "lesson-a",
                    "chunk_text": "First matching chunk",
                    "vector": [1, 0],
                },
                {
                    "id": "lesson-b:0",
                    "lesson_id": "lesson-b",
                    "chunk_text": "Other lesson",
                    "vector": [1, 0],
                },
            ]
        )

        results = retrieve(
            ["lesson-a"],
            self.wrong_questions,
            top_k=1,
            index_path=path,
            embed_fn=lambda _query: [1, 0],
        )

        self.assertEqual([chunk["id"] for chunk in results], ["lesson-a:1"])

    def test_retrieval_rejects_empty_scope_invalid_top_k_and_bad_chunks(self):
        path = self._write_index(
            [
                {
                    "id": "lesson-a:0",
                    "lesson_id": "lesson-a",
                    "chunk_text": "Chunk",
                    "vector": [1, 0],
                }
            ]
        )
        with self.assertRaises(ValueError):
            retrieve([], self.wrong_questions, index_path=path)
        with self.assertRaises(ValueError):
            retrieve(["lesson-a"], self.wrong_questions, top_k=0, index_path=path)
        with self.assertRaises(ValueError):
            retrieve(["lesson-b"], self.wrong_questions, index_path=path)

        broken_path = self._write_index(
            [{"id": "lesson-a:0", "lesson_id": "lesson-a", "vector": [1, 0]}]
        )
        with self.assertRaises(ValueError):
            retrieve(
                ["lesson-a"],
                self.wrong_questions,
                index_path=broken_path,
                embed_fn=lambda _query: [1, 0],
            )


if __name__ == "__main__":
    unittest.main()
