"""Runtime exceptions for ingest graph orchestration."""


class MapIncompleteError(Exception):
    """Raised when not all chunks reached map_status=done before reduce."""

    def __init__(self, source_id: int, pending_chunk_ids: list[int], wave: int):
        self.source_id = source_id
        self.pending_chunk_ids = pending_chunk_ids
        self.wave = wave
        super().__init__(
            f"Source {source_id} map incomplete after wave {wave}: "
            f"chunks {pending_chunk_ids} not done"
        )
