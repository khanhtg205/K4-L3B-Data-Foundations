from __future__ import annotations

import math
import re


class FixedSizeChunker:
    """
    Split text into fixed-size chunks with optional overlap.

    Rules:
        - Each chunk is at most chunk_size characters long.
        - Consecutive chunks share overlap characters.
        - The last chunk contains whatever remains.
        - If text is shorter than chunk_size, return [text].
    """

    def __init__(self, chunk_size: int = 500, overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        if len(text) <= self.chunk_size:
            return [text]

        step = self.chunk_size - self.overlap
        chunks: list[str] = []
        for start in range(0, len(text), step):
            chunk = text[start : start + self.chunk_size]
            chunks.append(chunk)
            if start + self.chunk_size >= len(text):
                break
        return chunks


class SentenceChunker:
    """
    Split text into chunks of at most max_sentences_per_chunk sentences.

    Sentence detection: split on ". ", "! ", "? " or ".\n".
    Strip extra whitespace from each chunk.
    """

    def __init__(self, max_sentences_per_chunk: int = 3) -> None:
        self.max_sentences_per_chunk = max(1, max_sentences_per_chunk)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        # Split on whitespace/newline preceded by sentence-ending punctuation (.!?), keeping punctuation
        raw_sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        sentences = [s.strip() for s in raw_sentences if s.strip()]

        if not sentences:
            return []

        chunks: list[str] = []
        for i in range(0, len(sentences), self.max_sentences_per_chunk):
            group = sentences[i : i + self.max_sentences_per_chunk]
            chunks.append(" ".join(group).strip())
        return chunks


class RecursiveChunker:
    """
    Recursively split text using separators in priority order.

    Default separator priority:
        ["\n\n", "\n", ". ", " ", ""]
    """

    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators: list[str] | None = None, chunk_size: int = 500) -> None:
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text:
            return []
        return self._split(text, self.separators)

    def _split(self, current_text: str, remaining_separators: list[str]) -> list[str]:
        if not current_text:
            return []
        if len(current_text) <= self.chunk_size:
            return [current_text]
        if not remaining_separators:
            # Fallback when no separators left: slice by chunk_size
            return [
                current_text[i : i + self.chunk_size]
                for i in range(0, len(current_text), self.chunk_size)
            ]

        sep = remaining_separators[0]
        next_separators = remaining_separators[1:]

        if sep == "":
            pieces = list(current_text)
        else:
            pieces = current_text.split(sep)

        # If separator did not split the text, try the next separator
        if len(pieces) <= 1:
            return self._split(current_text, next_separators)

        # Deep recursion: further split pieces that exceed chunk_size
        sub_pieces: list[str] = []
        for p in pieces:
            if len(p) > self.chunk_size:
                sub_pieces.extend(self._split(p, next_separators))
            else:
                sub_pieces.append(p)

        # Merge up: combine adjacent pieces up to chunk_size
        merged: list[str] = []
        current_chunk = ""
        for p in sub_pieces:
            if not p:
                continue
            if not current_chunk:
                current_chunk = p
            else:
                candidate = current_chunk + (sep if sep else "") + p
                if len(candidate) <= self.chunk_size:
                    current_chunk = candidate
                else:
                    merged.append(current_chunk)
                    current_chunk = p

        if current_chunk:
            merged.append(current_chunk)

        return merged if merged else [current_text]


class HeadingChunker:
    r"""
    Split Markdown text into chunks based on heading sections (## and ###).
    (Mandatory Strategy for Variant K4-L3B)

    Algorithm:
        1. Split text at heading boundaries (^#+\s+).
        2. Keep each heading with its section body.
        3. If a section exceeds max_chunk_size, split by paragraphs while re-injecting 
           the section heading at the top of each sub-chunk to preserve context.
    """

    def __init__(self, max_chunk_size: int = 800, chunk_size: int | None = None) -> None:
        self.max_chunk_size = chunk_size if chunk_size is not None else max_chunk_size

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        # Split text at heading lines (lines starting with #, ##, ###)
        sections = re.split(r"(?m)(?=^#+\s+)", text.strip())
        chunks: list[str] = []

        for sec in sections:
            sec = sec.strip()
            if not sec:
                continue

            if len(sec) <= self.max_chunk_size:
                chunks.append(sec)
            else:
                # Subdivide oversized section while preserving heading context
                lines = sec.split("\n", 1)
                heading = lines[0].strip()
                body = lines[1].strip() if len(lines) > 1 else ""

                paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
                if not paragraphs:
                    chunks.append(sec[:self.max_chunk_size])
                    continue

                current_chunk = heading
                for para in paragraphs:
                    candidate = f"{current_chunk}\n\n{para}"
                    if len(candidate) <= self.max_chunk_size:
                        current_chunk = candidate
                    else:
                        if current_chunk != heading:
                            chunks.append(current_chunk)
                        current_chunk = f"{heading} (cont.)\n\n{para}"

                if current_chunk and current_chunk != heading:
                    chunks.append(current_chunk)

        return chunks


class SemanticChunker:
    """
    Split text into chunks based on semantic similarity between consecutive sentences.
    (Custom Advanced Strategy for Member 4 / Report Lead)

    Algorithm:
        1. Split text into individual sentences.
        2. Compute embedding vector for each sentence using an embedder.
        3. Compute cosine similarity between adjacent sentences s[i] and s[i+1].
        4. Detect semantic breakpoints where similarity drops below threshold or max_chunk_size is reached.
        5. Group coherent sentences between breakpoints into chunks.
    """

    def __init__(
        self,
        embedder: object = None,
        similarity_threshold: float = 0.65,
        max_chunk_size: int = 800,
        min_sentences_per_chunk: int = 1,
    ) -> None:
        if embedder is None:
            from src.embeddings import MockEmbedder
            self.embedder = MockEmbedder()
        else:
            self.embedder = embedder
        self.similarity_threshold = similarity_threshold
        self.max_chunk_size = max_chunk_size
        self.min_sentences_per_chunk = min_sentences_per_chunk

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        raw_sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        sentences = [s.strip() for s in raw_sentences if s.strip()]

        if not sentences:
            return []
        if len(sentences) == 1:
            return sentences

        # Compute embeddings for each sentence
        embeddings = [self.embedder(s) for s in sentences]

        chunks: list[str] = []
        current_sentences: list[str] = [sentences[0]]
        current_len = len(sentences[0])

        for i in range(len(sentences) - 1):
            next_sent = sentences[i + 1]
            sim = compute_similarity(embeddings[i], embeddings[i + 1])

            is_semantic_drop = sim < self.similarity_threshold
            is_size_exceeded = (current_len + len(next_sent) + 1) > self.max_chunk_size

            if len(current_sentences) >= self.min_sentences_per_chunk and (is_semantic_drop or is_size_exceeded):
                chunks.append(" ".join(current_sentences).strip())
                current_sentences = [next_sent]
                current_len = len(next_sent)
            else:
                current_sentences.append(next_sent)
                current_len += len(next_sent) + 1

        if current_sentences:
            chunks.append(" ".join(current_sentences).strip())

        return chunks


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def compute_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """
    Compute cosine similarity between two vectors.

    cosine_similarity = dot(a, b) / (||a|| * ||b||)

    Returns 0.0 if either vector has zero magnitude.
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    norm_a = math.sqrt(sum(x * x for x in vec_a))
    norm_b = math.sqrt(sum(y * y for y in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return _dot(vec_a, vec_b) / (norm_a * norm_b)


class ChunkingStrategyComparator:
    """Run all built-in chunking strategies and compare their results."""

    def compare(self, text: str, chunk_size: int = 200) -> dict:
        fixed = FixedSizeChunker(chunk_size=chunk_size, overlap=20).chunk(text)
        by_sentences = SentenceChunker(max_sentences_per_chunk=3).chunk(text)
        recursive = RecursiveChunker(chunk_size=chunk_size).chunk(text)

        strategies = {
            "fixed_size": fixed,
            "by_sentences": by_sentences,
            "recursive": recursive,
        }

        result = {}
        for name, chunks in strategies.items():
            count = len(chunks)
            avg_len = sum(len(c) for c in chunks) / count if count > 0 else 0.0
            result[name] = {
                "count": count,
                "avg_length": avg_len,
                "chunks": chunks,
            }
        return result
