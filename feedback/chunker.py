"""Structure-aware lesson chunking for the local RAG index."""

from dataclasses import dataclass


MIN_TOKENS = 300
MAX_TOKENS = 500


def estimate_tokens(text):
    """Estimate tokens using the documented four-characters-per-token rule."""
    if not isinstance(text, str):
        raise TypeError("Chunk text must be a string.")
    return (len(text) + 3) // 4 if text else 0


@dataclass(frozen=True)
class _Block:
    text: str
    block_type: str
    tokens: int


def _content_blocks(content_jsonb):
    if not isinstance(content_jsonb, list):
        raise TypeError("Lesson content must be a list of structured blocks.")

    blocks = []
    for block in content_jsonb:
        if not isinstance(block, dict):
            raise TypeError("Every lesson content block must be an object.")
        text = block.get("text", "")
        if not isinstance(text, str):
            raise TypeError("Lesson block text must be a string.")
        text = text.strip()
        if not text:
            continue
        blocks.append(
            _Block(
                text=text,
                block_type=block.get("type", "paragraph"),
                tokens=estimate_tokens(text),
            )
        )
    return blocks


def _join(blocks):
    return "\n\n".join(block.text for block in blocks)


def chunk_content(content_jsonb, *, min_tokens=MIN_TOKENS, max_tokens=MAX_TOKENS):
    """Split structured lesson blocks into roughly 300-500 token chunks.

    Blocks remain atomic, so worked examples are never split. A single example
    above the maximum is emitted as its own chunk. Headings become preferred
    boundaries once the current chunk has reached the minimum size.
    """
    if min_tokens <= 0 or max_tokens < min_tokens:
        raise ValueError("Chunk token bounds are invalid.")

    chunk_blocks = []
    current = []
    current_tokens = 0

    def flush():
        nonlocal current, current_tokens
        if current:
            chunk_blocks.append(current)
            current = []
            current_tokens = 0

    blocks = _content_blocks(content_jsonb)
    remaining_tokens = [0] * (len(blocks) + 1)
    for index in range(len(blocks) - 1, -1, -1):
        remaining_tokens[index] = remaining_tokens[index + 1] + blocks[index].tokens

    for index, block in enumerate(blocks):
        if block.block_type == "example" and block.tokens > max_tokens:
            flush()
            chunk_blocks.append([block])
            continue

        natural_heading_break = (
            block.block_type == "heading"
            and current_tokens >= min_tokens
            and remaining_tokens[index] >= min_tokens
        )
        exceeds_maximum = current and current_tokens + block.tokens > max_tokens
        if natural_heading_break or (exceeds_maximum and current_tokens >= min_tokens):
            flush()

        current.append(block)
        current_tokens += block.tokens

    flush()

    # Avoid tiny trailing fragments by moving complete blocks from the prior
    # chunk while keeping that prior chunk at or above the target minimum.
    for index in range(len(chunk_blocks) - 1, 0, -1):
        current_chunk = chunk_blocks[index]
        previous_chunk = chunk_blocks[index - 1]
        current_size = sum(block.tokens for block in current_chunk)
        previous_size = sum(block.tokens for block in previous_chunk)
        while current_size < min_tokens and len(previous_chunk) > 1:
            candidate = previous_chunk[-1]
            if previous_size - candidate.tokens < min_tokens:
                break
            previous_chunk.pop()
            current_chunk.insert(0, candidate)
            previous_size -= candidate.tokens
            current_size += candidate.tokens

    return [_join(blocks) for blocks in chunk_blocks]
