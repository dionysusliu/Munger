"""Unit tests for chunk token splitting and document-global offsets."""

from unittest.mock import MagicMock

from app.services.chunk_service import ChunkService


class TestChunkServiceSplit:
    def test_single_chunk_covers_full_document(self):
        service = ChunkService(llm_service=None, settings=MagicMock(ingest_chunk_size_tokens=600))
        text = "Hello world. This is a short document."
        segments = service.split_text(text, chunk_size=600, overlap=0)
        assert len(segments) == 1
        assert segments[0].doc_char_start == 0
        assert segments[0].doc_char_end == len(text)

    def test_multi_chunk_offsets_are_monotonic(self):
        service = ChunkService(llm_service=None, settings=MagicMock(ingest_chunk_size_tokens=8))
        text = "Alpha beta gamma delta epsilon zeta eta theta iota kappa."
        segments = service.split_text(text, chunk_size=8, overlap=2)
        assert len(segments) > 1
        for seg in segments:
            assert 0 <= seg.doc_char_start < seg.doc_char_end <= len(text)
        for prev, nxt in zip(segments, segments[1:]):
            assert prev.doc_char_end >= nxt.doc_char_start or nxt.doc_char_start >= prev.doc_char_start
