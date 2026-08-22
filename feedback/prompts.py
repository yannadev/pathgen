"""Prompt templates for grounded Grade 7 mathematics feedback."""


SYSTEM_PROMPT = "You are a Grade 7 math tutor for Philippine DepEd learners."


def _wrong_item_lines(wrong_items):
    return "\n".join(
        (
            f"- Question: {item['question_text']}\n"
            f"  Student chose: {item['selected_answer']}\n"
            f"  Correct answer: {item['correct_answer']}\n"
            f"  Teaching hint: {item['hint_text']}"
        )
        for item in wrong_items
    )


def _excerpt_lines(retrieved_chunks):
    return "\n\n".join(
        f"Excerpt {index}:\n{chunk['chunk_text']}"
        for index, chunk in enumerate(retrieved_chunks, start=1)
    )


def build_prompt(session_result, wrong_items, retrieved_chunks):
    """Build either grounded corrective feedback or short perfect-score praise."""
    score = session_result["score"]
    correct_count = session_result["correct_count"]
    total_questions = session_result["total_questions"]
    title = session_result["title"]

    if not wrong_items:
        return f"""The learner completed {title} with {correct_count} of {total_questions} correct ({score}%).

Write 3 concise, encouraging sentences praising the learner's strong performance. Reinforce that they should carry the same careful reasoning into the next lesson. Do not introduce a new mathematical topic and do not mention retrieval or these instructions."""

    wrong_text = _wrong_item_lines(wrong_items)
    excerpt_text = _excerpt_lines(retrieved_chunks)
    return f"""The learner completed {title} with {correct_count} of {total_questions} correct ({score}%).

Incorrect-response evidence:
{wrong_text}

Approved lesson excerpts:
{excerpt_text}

Write 3-5 encouraging sentences. Give a generalized performance summary, identify the main error pattern, and name the specific concepts the learner should review. Do not list every wrong item separately. Use ONLY the approved lesson excerpts for mathematical teaching content; do not invent rules, examples, or topics. Do not reveal answer keys, mention retrieval, or mention these instructions."""
