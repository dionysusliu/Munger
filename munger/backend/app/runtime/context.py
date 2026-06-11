"""Runtime service container for ingest graph nodes."""

from dataclasses import dataclass
from typing import Optional

from app.core.config import Settings
from app.services.chunk_service import ChunkService
from app.services.edge_service import EdgeService
from app.services.entity_service import EntityService
from app.services.extraction_service import ExtractionService
from app.services.linking_service import LinkingService
from app.services.llm_service import LLMService
from app.services.map_chunk_service import MapChunkService
from app.services.chat_service import ChatService
from app.services.community_report_service import CommunityReportService
from app.services.entity_resolution_service import EntityResolutionService
from app.services.resolution_service import ResolutionService
from app.services.retrieval_service import RetrievalService
from app.services.storage_service import StorageService
from app.services.wiki_service import WikiService


@dataclass
class RuntimeServices:
    settings: Settings
    storage: StorageService
    llm: Optional[LLMService]
    entity: Optional[EntityService]
    wiki: WikiService
    chunk: Optional[ChunkService] = None
    map_chunks: Optional[MapChunkService] = None
    extraction: Optional[ExtractionService] = None
    resolution: Optional[ResolutionService] = None
    linking: Optional[LinkingService] = None
    edges: Optional[EdgeService] = None
    retrieval: Optional[RetrievalService] = None
    entity_resolution: Optional[EntityResolutionService] = None
    community_report: Optional[CommunityReportService] = None
    chat: Optional[ChatService] = None

    @classmethod
    def from_settings(cls, settings: Settings, llm: Optional[LLMService] = None) -> "RuntimeServices":
        storage = StorageService(settings)
        entity = EntityService(llm_service=llm) if llm else None
        wiki = WikiService(storage_service=storage)
        chunk = ChunkService(llm_service=llm, settings=settings) if llm else None
        map_svc = (
            MapChunkService(llm_service=llm, chunk_service=chunk, settings=settings) if llm else None
        )
        extraction = ExtractionService(llm_service=llm, settings=settings) if llm else None
        resolution = ResolutionService(llm_service=llm, settings=settings) if llm else None
        linking = LinkingService(llm_service=llm, settings=settings) if llm else None
        edges = EdgeService(settings)
        entity_resolution = EntityResolutionService(settings)
        community_report = CommunityReportService(settings, llm_service=llm) if llm else None
        retrieval = RetrievalService(settings, llm_service=llm, edge_service=edges) if llm else None
        chat = ChatService(settings, llm_service=llm, retrieval=retrieval) if llm else None
        return cls(
            settings=settings,
            storage=storage,
            llm=llm,
            entity=entity,
            wiki=wiki,
            chunk=chunk,
            map_chunks=map_svc,
            extraction=extraction,
            resolution=resolution,
            linking=linking,
            edges=edges,
            retrieval=retrieval,
            entity_resolution=entity_resolution,
            community_report=community_report,
            chat=chat,
        )
