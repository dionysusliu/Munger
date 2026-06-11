"""Graph GC (SP2.4): prune orphan entities + HITL-confirmed deletion of low-value ones.

The subtraction half of the self-improving KB. Conservative by design:
- prune_orphans() deletes only provably-unreferenced entities (0 mentions, 0 relationships,
  not a canonical root).
- gc_candidates() only LISTS low-value entities (never auto-deleted; human-touched excluded).
- delete_entities() refuses canonical roots; cleans RESTRICT children (mentions, the
  entity's wiki page + links); relationships/edges/labels go via FK CASCADE.
Salience/communities go stale after deletion — re-run POST /api/graph/recompute."""

from __future__ import annotations

from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.database import async_session_maker

_ORPHANS_SQL = """
    SELECT e.id FROM entities e
    WHERE NOT EXISTS (SELECT 1 FROM entity_mentions m WHERE m.entity_id = e.id)
      AND NOT EXISTS (SELECT 1 FROM entity_relationships r
                      WHERE r.source_entity_id = e.id OR r.target_entity_id = e.id)
      AND NOT EXISTS (SELECT 1 FROM entities c WHERE c.canonical_entity_id = e.id)
      AND NOT EXISTS (SELECT 1 FROM labeled_pairs lp
                      WHERE lp.entity_a_id = e.id OR lp.entity_b_id = e.id)
"""


class GraphGCService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    async def find_orphans(self) -> list[int]:
        """Entities referenced by NOTHING: no mentions, no relationships, no merge members,
        and never human-labeled (labeled_pairs would CASCADE away silently otherwise)."""
        async with async_session_maker() as s:
            rows = (await s.execute(text(_ORPHANS_SQL))).all()
        return [r[0] for r in rows]

    async def delete_entities(self, entity_ids: list[int]) -> dict:
        """Hard-delete entities safely. Refuses canonical roots (unmerge them first).

        Order per entity: wiki_links of its page -> wiki page -> mentions -> entity row.
        entity_relationships / entity_edges / labeled_pairs cascade on the entity delete.
        """
        if not entity_ids:
            return {"deleted": 0, "deleted_ids": [], "skipped_canonical_roots": []}
        async with async_session_maker() as s:
            root_rows = (await s.execute(
                text("SELECT DISTINCT canonical_entity_id FROM entities "
                     "WHERE canonical_entity_id = ANY(:ids)"),
                {"ids": entity_ids},
            )).all()
            roots = {r[0] for r in root_rows}
            deletable = [e for e in entity_ids if e not in roots]
            if deletable:
                # Capture wiki_page_ids before nulling the FK (entities.wiki_page_id has no
                # ondelete so deleting the page while the entity still references it violates FK).
                page_rows = (await s.execute(text(
                    "SELECT wiki_page_id FROM entities "
                    "WHERE id = ANY(:ids) AND wiki_page_id IS NOT NULL"
                ), {"ids": deletable})).all()
                page_ids = [r[0] for r in page_rows]
                # NULL the FK first so we can delete the pages safely.
                await s.execute(text(
                    "UPDATE entities SET wiki_page_id = NULL WHERE id = ANY(:ids)"
                ), {"ids": deletable})
                if page_ids:
                    await s.execute(text(
                        "DELETE FROM wiki_links WHERE from_page_id = ANY(:pids) "
                        "OR to_page_id = ANY(:pids)"
                    ), {"pids": page_ids})
                    await s.execute(text(
                        "DELETE FROM wiki_pages WHERE id = ANY(:pids)"
                    ), {"pids": page_ids})
                await s.execute(text(
                    "DELETE FROM entity_mentions WHERE entity_id = ANY(:ids)"), {"ids": deletable})
                await s.execute(text(
                    "DELETE FROM entities WHERE id = ANY(:ids)"), {"ids": deletable})
            await s.commit()
        return {"deleted": len(deletable), "deleted_ids": deletable,
                "skipped_canonical_roots": sorted(roots)}

    async def prune_orphans(self) -> dict:
        """Auto-safe prune: delete all provably-unreferenced entities."""
        orphans = await self.find_orphans()
        out = await self.delete_entities(orphans)
        return {"orphans_found": len(orphans), "deleted": out["deleted"]}

    async def gc_candidates(self, max_mentions: int = 1, limit: int = 100) -> list[dict]:
        """LIST low-value deletion candidates (HITL — never auto-deleted).

        Excluded forever: anything human-touched (labeled_pairs or a method='human'
        relationship) and canonical roots. Ordered worst-salience-first."""
        async with async_session_maker() as s:
            rows = (await s.execute(text("""
                SELECT e.id, e.name, e.entity_type, e.mention_count, COALESCE(e.salience, 0.0)
                FROM entities e
                WHERE e.mention_count <= :mm
                  AND NOT EXISTS (SELECT 1 FROM entities c WHERE c.canonical_entity_id = e.id)
                  AND NOT EXISTS (SELECT 1 FROM labeled_pairs lp
                                  WHERE lp.entity_a_id = e.id OR lp.entity_b_id = e.id)
                  AND NOT EXISTS (SELECT 1 FROM entity_relationships r
                                  WHERE r.method = 'human'
                                    AND (r.source_entity_id = e.id OR r.target_entity_id = e.id))
                ORDER BY COALESCE(e.salience, 0.0) ASC, e.mention_count ASC, e.id ASC
                LIMIT :lim
            """), {"mm": max_mentions, "lim": limit})).all()
        return [{"entity_id": r[0], "name": r[1], "entity_type": r[2],
                 "mention_count": r[3], "salience": float(r[4])} for r in rows]
