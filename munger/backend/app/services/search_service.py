"""Search service - full-text and semantic search across wiki pages, sources, and entities."""

import logging
import time
from typing import Optional

from sqlalchemy import select, func, or_, and_, desc, text
from sqlalchemy.orm import selectinload

from app.core.database import async_session_maker
from app.models.wiki import WikiPage
from app.models.source import Source
from app.models.entity import Entity
from app.schemas.search import SearchRequest, SearchResponse, SearchResult
from app.services.llm_service import LLMService
from app.services.vector_store import VectorStore, get_vector_store

logger = logging.getLogger(__name__)


class SearchService:
    """Full-text and semantic search across all content."""

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        vector_store: VectorStore | None = None,
    ):
        self.llm_service = llm_service
        self.vectors = vector_store or get_vector_store()

    # ------------------------------------------------------------------
    # Main search entry point
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        result_type: str = "all",
        page: int = 1,
        page_size: int = 20,
    ) -> SearchResponse:
        """Search across all content types.

        Args:
            query: The search query string.
            result_type: Filter by type - "wiki_page", "source", "entity", or "all".
            page: Page number (1-based).
            page_size: Results per page.

        Returns:
            SearchResponse with results and metadata.
        """
        start_time = time.time()

        if not query or not query.strip():
            return SearchResponse(
                query="",
                results=[],
                total=0,
                page=page,
                page_size=page_size,
                execution_time_ms=0.0,
            )

        query = query.strip()
        all_results = []

        # Search by type
        try:
            if result_type in ("all", "wiki_page"):
                wiki_results = await self.search_wiki(query)
                all_results.extend(wiki_results)
        except Exception as e:
            logger.warning(f"Wiki search failed: {e}")

        try:
            if result_type in ("all", "source"):
                source_results = await self.search_sources(query)
                all_results.extend(source_results)
        except Exception as e:
            logger.warning(f"Source search failed: {e}")

        try:
            if result_type in ("all", "entity"):
                entity_results = await self.search_entities(query)
                all_results.extend(entity_results)
        except Exception as e:
            logger.warning(f"Entity search failed: {e}")

        # Sort by score descending
        all_results.sort(key=lambda r: r.score, reverse=True)

        # Apply pagination
        total = len(all_results)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated = all_results[start_idx:end_idx]

        execution_time = (time.time() - start_time) * 1000

        return SearchResponse(
            query=query,
            results=paginated,
            total=total,
            page=page,
            page_size=page_size,
            execution_time_ms=round(execution_time, 2),
        )

    # ------------------------------------------------------------------
    # Type-specific searches
    # ------------------------------------------------------------------

    async def search_wiki(self, query: str) -> list[SearchResult]:
        """Search wiki pages by title and content."""
        async with async_session_maker() as session:
            search_term = f"%{query}%"

            result = await session.execute(
                select(WikiPage).where(
                    or_(
                        WikiPage.title.ilike(search_term),
                        WikiPage.content.ilike(search_term),
                        WikiPage.slug.ilike(search_term),
                    )
                )
                .order_by(desc(WikiPage.updated_at))
                .limit(50)
            )
            pages = result.scalars().all()

            results = []
            for page in pages:
                score = self._calculate_score(query, page.title, page.content)
                # Extract a content snippet
                snippet = self._extract_snippet(page.content, query)

                results.append(
                    SearchResult(
                        id=page.id,
                        title=page.title,
                        content=snippet,
                        result_type="wiki_page",
                        score=score,
                        slug=page.slug,
                        page_type=page.page_type,
                    )
                )

            return results

    async def search_sources(self, query: str) -> list[SearchResult]:
        """Search sources by title, content, and summary."""
        async with async_session_maker() as session:
            search_term = f"%{query}%"

            result = await session.execute(
                select(Source).where(
                    or_(
                        Source.title.ilike(search_term),
                        Source.content_text.ilike(search_term),
                        Source.content_summary.ilike(search_term),
                        Source.filename.ilike(search_term),
                    )
                )
                .order_by(desc(Source.created_at))
                .limit(50)
            )
            sources = result.scalars().all()

            results = []
            for source in sources:
                score = self._calculate_score(
                    query, source.title, source.content_text or ""
                )
                snippet = source.content_summary or self._extract_snippet(
                    source.content_text or "", query
                )
                if not snippet:
                    snippet = f"{source.file_type.upper()} file — {source.filename}"

                results.append(
                    SearchResult(
                        id=source.id,
                        title=source.title,
                        content=snippet,
                        result_type="source",
                        score=score,
                    )
                )

            return results

    async def search_entities(self, query: str) -> list[SearchResult]:
        """Search entities by name and description."""
        async with async_session_maker() as session:
            search_term = f"%{query}%"

            result = await session.execute(
                select(Entity).where(
                    or_(
                        Entity.name.ilike(search_term),
                        Entity.description.ilike(search_term),
                    )
                )
                .order_by(desc(Entity.mention_count))
                .limit(50)
            )
            entities = result.scalars().all()

            results = []
            for entity in entities:
                score = self._calculate_score(
                    query, entity.name, entity.description or ""
                )
                # Boost by mention count
                score = min(1.0, score + min(0.1, entity.mention_count * 0.01))

                snippet = entity.description or f"Type: {entity.entity_type}"

                results.append(
                    SearchResult(
                        id=entity.id,
                        title=entity.name,
                        content=snippet,
                        result_type="entity",
                        score=score,
                        entity_type=entity.entity_type,
                    )
                )

            return results

    # ------------------------------------------------------------------
    # Semantic search
    # ------------------------------------------------------------------

    async def semantic_search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Perform semantic search using vector embeddings.

        Falls back to full-text search if embeddings are not available.
        """
        if not self.llm_service:
            logger.warning("No LLM service for semantic search, falling back to text search")
            response = await self.search(query, page_size=limit)
            return response.results

        try:
            query_embedding = await self.llm_service.embed_text(query)
            if not query_embedding:
                raise RuntimeError("Empty embedding returned")

            chunk_hits = await self.vectors.search_chunks(query_embedding, limit=limit)

            if chunk_hits:
                async with async_session_maker() as session:
                    rows = await session.execute(
                        text(
                            """
                            SELECT id, source_id, content, doc_char_start, doc_char_end
                            FROM chunks
                            WHERE id = ANY(:ids)
                            """
                        ),
                        {"ids": [hit.id for hit in chunk_hits]},
                    )
                    rows_by_id = {row.id: row for row in rows.fetchall()}

                results: list[SearchResult] = []
                for hit in chunk_hits:
                    row = rows_by_id.get(hit.id)
                    if row is None:
                        continue
                    score = max(0.0, 1.0 - float(hit.distance))
                    excerpt = (row.content or "")[:300]
                    results.append(
                        SearchResult(
                            id=row.id,
                            title=f"Chunk {row.id}",
                            content=excerpt,
                            result_type="chunk",
                            score=score,
                            source_id=row.source_id,
                            chunk_id=row.id,
                            char_start=row.doc_char_start,
                            char_end=row.doc_char_end,
                            excerpt=excerpt,
                        )
                    )
                return results

            response = await self.search(query, page_size=limit)
            return response.results[:limit]

        except Exception as e:
            logger.warning(f"Semantic search failed, falling back to text: {e}")
            response = await self.search(query, page_size=limit)
            return response.results

    async def hybrid_search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """RRF fusion of pgvector chunk hits and wiki full-text search."""
        k = 60
        scores: dict[tuple[str, int], float] = {}
        payloads: dict[tuple[str, int], SearchResult] = {}

        chunk_hits = await self.semantic_search(query, limit=limit * 2)
        for rank, hit in enumerate(chunk_hits):
            if hit.result_type != "chunk":
                continue
            key = ("chunk", hit.id)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            payloads[key] = hit

        async with async_session_maker() as session:
            wiki_rows = await session.execute(
                text(
                    """
                    SELECT id, title, slug, content,
                           ts_rank(search_vector, plainto_tsquery('english', :q)) AS rank
                    FROM wiki_pages
                    WHERE search_vector @@ plainto_tsquery('english', :q)
                    ORDER BY rank DESC
                    LIMIT :lim
                    """
                ),
                {"q": query, "lim": limit * 2},
            )
            for rank, row in enumerate(wiki_rows.fetchall()):
                key = ("wiki_page", row.id)
                scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
                excerpt = (row.content or "")[:300]
                payloads[key] = SearchResult(
                    id=row.id,
                    title=row.title,
                    content=excerpt,
                    result_type="wiki_page",
                    score=float(row.rank or 0),
                    slug=row.slug,
                    excerpt=excerpt,
                )

        if not scores:
            response = await self.search(query, page_size=limit)
            return response.results[:limit]

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:limit]
        results: list[SearchResult] = []
        for key, rrf_score in ranked:
            hit = payloads[key]
            hit.score = rrf_score
            results.append(hit)
        return results

    # ------------------------------------------------------------------
    # Autocomplete suggestions
    # ------------------------------------------------------------------

    async def get_suggestions(self, partial: str) -> list[str]:
        """Get autocomplete suggestions based on partial query.

        Returns titles/names that match the partial string.
        """
        if not partial or len(partial) < 2:
            return []

        partial = partial.strip()
        search_term = f"%{partial}%"
        suggestions = []

        async with async_session_maker() as session:
            # Wiki page titles
            try:
                result = await session.execute(
                    select(WikiPage.title)
                    .where(WikiPage.title.ilike(search_term))
                    .order_by(WikiPage.title)
                    .limit(5)
                )
                suggestions.extend([row[0] for row in result.all()])
            except Exception as e:
                logger.debug(f"Wiki suggestions failed: {e}")

            # Entity names
            try:
                result = await session.execute(
                    select(Entity.name)
                    .where(Entity.name.ilike(search_term))
                    .order_by(desc(Entity.mention_count))
                    .limit(5)
                )
                suggestions.extend([row[0] for row in result.all()])
            except Exception as e:
                logger.debug(f"Entity suggestions failed: {e}")

            # Source titles
            try:
                result = await session.execute(
                    select(Source.title)
                    .where(Source.title.ilike(search_term))
                    .order_by(desc(Source.created_at))
                    .limit(3)
                )
                suggestions.extend([row[0] for row in result.all()])
            except Exception as e:
                logger.debug(f"Source suggestions failed: {e}")

        # Deduplicate and sort
        seen = set()
        unique = []
        for s in suggestions:
            lower = s.lower()
            if lower not in seen:
                seen.add(lower)
                unique.append(s)

        return unique[:10]

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    def _calculate_score(self, query: str, title: str, content: str) -> float:
        """Calculate a relevance score for a search result.

        Higher scores for:
        - Exact title matches
        - Title containing query
        - Content containing query multiple times
        """
        query_lower = query.lower()
        title_lower = title.lower()
        content_lower = content.lower()

        score = 0.0

        # Title exact match
        if title_lower == query_lower:
            score += 1.0
        # Title starts with query
        elif title_lower.startswith(query_lower):
            score += 0.8
        # Title contains query
        elif query_lower in title_lower:
            score += 0.6

        # Content frequency
        content_count = content_lower.count(query_lower)
        score += min(0.3, content_count * 0.05)

        return min(1.0, score)

    def _extract_snippet(self, content: str, query: str, max_length: int = 200) -> str:
        """Extract a relevant snippet from content around the query match."""
        if not content:
            return ""

        query_lower = query.lower()
        content_lower = content.lower()

        # Find query position
        pos = content_lower.find(query_lower)
        if pos == -1:
            # Return beginning of content
            snippet = content[:max_length]
        else:
            # Extract window around match
            start = max(0, pos - max_length // 2)
            end = min(len(content), pos + max_length // 2)
            snippet = content[start:end]

        # Clean up
        snippet = snippet.replace("\n", " ").strip()
        if len(snippet) > max_length:
            snippet = snippet[:max_length].rsplit(" ", 1)[0] + "..."

        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet
