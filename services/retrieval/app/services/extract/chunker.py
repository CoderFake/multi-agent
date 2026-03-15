"""
Text chunker for embedding — overlapping fixed-size chunks.

Usage:
    from app.services.extract.chunker import chunk_text
    chunks = chunk_text(text, chunk_size=512, overlap=50)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from app.config.settings import settings


@dataclass
class TextChunk:
    """A chunk of text ready for embedding."""
    text: str
    chunk_index: int
    start_char: int
    end_char: int


def _split_into_sentences(text: str) -> List[str]:
    """Split text by sentence boundaries (period, newline) while keeping content."""
    # Split by newlines first, then by sentence-ending punctuation
    parts = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Split on sentence boundaries but keep the delimiter
        sentences = re.split(r'(?<=[.!?])\s+', line)
        parts.extend(s.strip() for s in sentences if s.strip())
    return parts


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> List[TextChunk]:
    """
    Split text into overlapping chunks.

    Uses sentence-aware splitting to avoid cutting mid-sentence when possible.
    Falls back to character-based splitting if sentences are too long.
    """
    if chunk_size is None:
        chunk_size = settings.CHUNK_SIZE
    if overlap is None:
        overlap = settings.CHUNK_OVERLAP

    if not text or not text.strip():
        return []

    text = text.strip()

    # If text is shorter than chunk_size, return as single chunk
    if len(text) <= chunk_size:
        return [TextChunk(text=text, chunk_index=0, start_char=0, end_char=len(text))]

    sentences = _split_into_sentences(text)
    if not sentences:
        return [TextChunk(text=text, chunk_index=0, start_char=0, end_char=len(text))]

    chunks: List[TextChunk] = []
    current_sentences: List[str] = []
    current_len = 0
    char_pos = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        # If single sentence exceeds chunk_size, split by characters
        if sentence_len > chunk_size:
            # Flush current buffer first
            if current_sentences:
                chunk_text_str = " ".join(current_sentences)
                chunks.append(TextChunk(
                    text=chunk_text_str,
                    chunk_index=len(chunks),
                    start_char=char_pos - current_len,
                    end_char=char_pos,
                ))

            # Character-split the long sentence
            for i in range(0, sentence_len, chunk_size - overlap):
                end = min(i + chunk_size, sentence_len)
                chunks.append(TextChunk(
                    text=sentence[i:end],
                    chunk_index=len(chunks),
                    start_char=char_pos + i,
                    end_char=char_pos + end,
                ))

            char_pos += sentence_len + 1
            current_sentences = []
            current_len = 0
            continue

        # Would exceed chunk_size? Flush and start new chunk with overlap
        if current_len + sentence_len + 1 > chunk_size and current_sentences:
            chunk_text_str = " ".join(current_sentences)
            chunks.append(TextChunk(
                text=chunk_text_str,
                chunk_index=len(chunks),
                start_char=char_pos - current_len,
                end_char=char_pos,
            ))

            # Overlap: keep last few sentences that fit in overlap window
            overlap_sentences: List[str] = []
            overlap_len = 0
            for s in reversed(current_sentences):
                if overlap_len + len(s) + 1 > overlap:
                    break
                overlap_sentences.insert(0, s)
                overlap_len += len(s) + 1

            current_sentences = overlap_sentences
            current_len = overlap_len

        current_sentences.append(sentence)
        current_len += sentence_len + 1
        char_pos += sentence_len + 1

    # Flush remaining
    if current_sentences:
        chunk_text_str = " ".join(current_sentences)
        chunks.append(TextChunk(
            text=chunk_text_str,
            chunk_index=len(chunks),
            start_char=char_pos - current_len,
            end_char=char_pos,
        ))

    return chunks
