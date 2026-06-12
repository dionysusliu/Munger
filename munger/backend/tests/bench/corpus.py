"""Deterministic synthetic corpus for pipeline benchmarks.

Provides ``build_corpus(seed)`` which generates a fixed ~5 500-token systems-paper
text with 30 embedded entity names and returns a ``Corpus`` dataclass that can
emit per-window extraction scripts (with real, window-relative char offsets).

Also provides ``BenchScriptedLLMService``, a thin wrapper around
``ScriptedLLMService`` that adds a ``stats`` dict so ``pipeline_step`` can
record ``llm_calls`` / ``llm_ms`` per step.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

from tests.fixtures.fake_llm import ScriptedLLMService

# ---------------------------------------------------------------------------
# Entity vocabulary
# ---------------------------------------------------------------------------

ENTITY_POOL: list[str] = [
    "Chordal Routing",
    "Finger Cache",
    "Consistent Hashing-X",
    "Distributed Hash Table",
    "Chord Protocol",
    "Virtual Node Ring",
    "Replication Factor",
    "Gossip Protocol",
    "Merkle Trie",
    "Bloom Filter",
    "Key-Value Store",
    "Node Stabilization",
    "Lookup Latency",
    "Successor Pointer",
    "Predecessor List",
    "Chord Node",
    "Hash Space",
    "Key Migration",
    "Join Protocol",
    "Fail-over Handler",
    "Load Balancer",
    "Partition Tolerance",
    "Replication Log",
    "Hash Ring",
    "Node Churn",
    "Token Ring",
    "Range Partition",
    "Data Migration",
    "Hot Spot",
    "Cache Coherence",
    "Write-Ahead Log",
    "Consistent Snapshot",
    "Vector Clock",
    "Epoch Manager",
    "Shard Monitor",
    "Heartbeat Protocol",
    "Leader Election",
    "Fault Boundary",
]

assert len(ENTITY_POOL) >= 30, "Entity pool must have at least 30 entries"

_ENTITY_TYPE_MAP: dict[str, str] = {
    "Chordal Routing": "mechanism",
    "Finger Cache": "mechanism",
    "Consistent Hashing-X": "model",
    "Distributed Hash Table": "model",
    "Chord Protocol": "model",
    "Virtual Node Ring": "mechanism",
    "Replication Factor": "concept",
    "Gossip Protocol": "mechanism",
    "Merkle Trie": "model",
    "Bloom Filter": "model",
    "Key-Value Store": "model",
    "Node Stabilization": "mechanism",
    "Lookup Latency": "concept",
    "Successor Pointer": "mechanism",
    "Predecessor List": "mechanism",
    "Chord Node": "concept",
    "Hash Space": "concept",
    "Key Migration": "mechanism",
    "Join Protocol": "mechanism",
    "Fail-over Handler": "mechanism",
    "Load Balancer": "mechanism",
    "Partition Tolerance": "concept",
    "Replication Log": "mechanism",
    "Hash Ring": "model",
    "Node Churn": "concept",
    "Token Ring": "model",
    "Range Partition": "mechanism",
    "Data Migration": "mechanism",
    "Hot Spot": "concept",
    "Cache Coherence": "concept",
    "Write-Ahead Log": "mechanism",
    "Consistent Snapshot": "mechanism",
    "Vector Clock": "mechanism",
    "Epoch Manager": "mechanism",
    "Shard Monitor": "mechanism",
    "Heartbeat Protocol": "mechanism",
    "Leader Election": "mechanism",
    "Fault Boundary": "concept",
}


def _entity_type(name: str) -> str:
    return _ENTITY_TYPE_MAP.get(name, "concept")


# ---------------------------------------------------------------------------
# Sentence templates
# ---------------------------------------------------------------------------

_ENTITY_TEMPLATES: list[str] = [
    "{E} is a core component that enables efficient data distribution across the cluster.",
    "The design of {E} minimises cross-node communication under high write throughput.",
    "{E} coordinates replicated state using a lease-based membership protocol.",
    "By leveraging {E}, the system achieves O(log N) lookup complexity at scale.",
    "Performance of {E} was evaluated under both read-heavy and write-heavy workloads.",
    "{E} handles failure detection by maintaining a live list of successor pointers.",
    "Our implementation extends {E} with lazy propagation to cut synchronisation overhead.",
    "Integrating {E} into the control plane reduces tail latency at the 99th percentile.",
    "The {E} design draws from prior work on consistent hashing and ring-based routing.",
    "{E} provides linearisable reads without sacrificing availability during network splits.",
    "Optimising {E} for SSD workloads required careful tuning of the write-buffer size.",
    "Adopting {E} eliminates global coordination bottlenecks present in the original design.",
    "Through {E}, the cluster self-heals after transient node failures within seconds.",
    "{E} uses Merkle-tree verification to detect and repair divergent replicas efficiently.",
    "Empirical results confirm that {E} scales linearly to clusters of thousands of nodes.",
]

_FILLER_SENTENCES: list[str] = [
    "Distributed systems must balance consistency, availability, and partition tolerance.",
    "Our benchmarking methodology follows established practices in the systems community.",
    "All experiments ran on a 64-node cluster with 10 GbE networking and NVMe storage.",
    "The implementation achieves sub-millisecond p99 latency under nominal load.",
    "Replication factors of three are standard in production deployments.",
    "The client library abstracts cluster topology via a simple key-value interface.",
    "Heartbeat intervals of 100 ms provide timely failure detection without excess overhead.",
    "Load shedding is applied when the request queue exceeds a configurable high-water mark.",
    "The system uses exponential backoff with jitter to prevent thundering-herd on recovery.",
    "Compaction is scheduled during low-traffic windows to reclaim space from tombstoned keys.",
    "Write-ahead logging ensures durability by persisting mutations before acknowledging clients.",
    "Snapshot isolation is implemented via multi-version concurrency control with GC.",
    "Network communication is secured with TLS 1.3 and mutual certificate authentication.",
    "The gossip protocol propagates membership changes with O(log N) message complexity.",
    "Quorum reads and writes with configurable replication factors enforce consistency.",
    "All measurements were taken over a 24-hour period to capture diurnal traffic patterns.",
    "Data migration during scale-out is throttled to avoid impacting foreground traffic.",
    "The monitoring dashboard exposes per-shard throughput, latency histograms, and errors.",
    "Fault injection testing uncovered edge cases in the leader failover path.",
    "The administrative API lets operators trigger manual rebalancing and rolling upgrades.",
    "B+ tree indexes enable efficient range scans over the sorted key space.",
    "Lamport timestamps establish a total order of events across the distributed system.",
    "Split-brain detection relies on a lease-based coordinator with a configurable timeout.",
    "The system automatically re-balances keys when nodes join or leave the cluster.",
    "Hash functions are chosen for uniform key distribution to prevent hot-spot formation.",
    "Metrics are exported to Prometheus every 15 seconds for real-time observability.",
    "The engineering team conducted extensive chaos testing before the production rollout.",
    "Memory pressure triggers LRU eviction of cold keys to a compressed secondary tier.",
    "Cross-datacenter replication is asynchronous to avoid increasing write latency.",
    "An adaptive scheduler prioritises latency-sensitive reads over background compaction.",
]


# ---------------------------------------------------------------------------
# BenchScriptedLLMService — adds stats tracking to ScriptedLLMService
# ---------------------------------------------------------------------------

class BenchScriptedLLMService(ScriptedLLMService):
    """ScriptedLLMService extended with a ``stats`` dict for pipeline_step telemetry.

    ``pipeline_step`` snapshots ``llm.stats["calls"]`` before and after each
    step body.  Objects without ``.stats`` are silently skipped.  Adding the
    dict here makes map_chunks / summarize_source / generate_wiki_pages all
    report ``llm_calls`` in their ``pipeline_step_complete`` events.

    We also track ``extract_calls`` (chat_structured invocations) separately
    so the bench can assert ``extract_calls == ceil(n_chunks / 2)``.
    """

    def __init__(self, scripts: list[Any]):
        super().__init__(scripts)
        self.stats: dict[str, int] = {"calls": 0, "ms": 0}
        self.extract_calls: int = 0  # chat_structured() calls (one per window)

    async def chat(self, messages: list[dict], **kwargs) -> str:
        result = await super().chat(messages, **kwargs)
        self.stats["calls"] += 1
        return result

    async def chat_structured(self, messages: list[dict], response_model: type, **kwargs):
        result = await super().chat_structured(messages, response_model, **kwargs)
        self.stats["calls"] += 1
        self.extract_calls += 1
        return result

    async def summarize(self, text: str, max_length: int = 1000) -> str:
        result = await super().summarize(text, max_length)
        self.stats["calls"] += 1
        return result

    async def generate_wiki_page(self, title: str, content: str, page_type: str = "entity") -> str:
        result = await super().generate_wiki_page(title, content, page_type)
        self.stats["calls"] += 1
        return result


# ---------------------------------------------------------------------------
# Corpus dataclass
# ---------------------------------------------------------------------------

@dataclass
class Corpus:
    """Synthetic paper text + entity manifest for the pipeline bench.

    Attributes
    ----------
    text:
        Full document text (~5 500 tokens).  Deterministic for a given seed.
    entities:
        The 30 entity names embedded verbatim in ``text``.
    """

    text: str
    entities: list[str]

    def extraction_script_for(self, window_texts: list[str]) -> list[dict]:
        """Return one extraction dict per window with WINDOW-RELATIVE offsets.

        ``map_window`` passes the slice ``source_text[run_first.doc_char_start :
        run_last.doc_char_end]`` to ``_extract_chunk`` as ``virtual_chunk.content``.
        ``_extract_chunk`` then adds ``run_first.doc_char_start`` (the "offset
        base") to every ``char_start`` / ``char_end`` to make them doc-global.
        Therefore this function must return offsets measured from position 0
        *within* each window text — exactly what ``str.find`` gives.
        """
        results = []
        for window_text in window_texts:
            found: list[dict] = []
            seen: set[str] = set()
            for name in self.entities:
                pos = window_text.find(name)
                if pos != -1 and name not in seen:
                    found.append(
                        {
                            "name": name,
                            "type": _entity_type(name),
                            "description": "A distributed-systems component.",
                            "char_start": pos,
                            "char_end": pos + len(name),
                        }
                    )
                    seen.add(name)

            # Emit up to 3 relationships between consecutive found entities.
            rels: list[dict] = []
            for i in range(min(3, len(found) - 1)):
                rels.append(
                    {
                        "source": found[i]["name"],
                        "target": found[i + 1]["name"],
                        "type": "uses",
                        "description": "component dependency",
                    }
                )

            results.append({"entities": found, "relationships": rels})
        return results


# ---------------------------------------------------------------------------
# Text generation helpers
# ---------------------------------------------------------------------------

def _make_para(rng: random.Random, entity_names: list[str], n_filler: int) -> str:
    """Build one paragraph that mentions every entity in *entity_names* once.

    Entity sentences come first (so entities appear near the window start and
    are consistently demuxed to the window's first chunk — required for
    deterministic co-mention relationships across windows).
    Filler sentences follow without shuffling.
    """
    sentences: list[str] = []

    # Entity-mentioning sentences first (deterministic chunk-0 assignment)
    for name in entity_names:
        tmpl = rng.choice(_ENTITY_TEMPLATES)
        sentences.append(tmpl.format(E=name))

    # Filler sentences
    chosen = rng.sample(_FILLER_SENTENCES, min(n_filler, len(_FILLER_SENTENCES)))
    sentences.extend(chosen)

    return " ".join(sentences)


def _generate_corpus_text(rng: random.Random, entities: list[str]) -> str:
    """Generate the full document with entities embedded in a fixed layout.

    Entity assignment
    -----------------
    popular   = entities[0:5]   — mentioned in the abstract + all 6 body sections
    common    = entities[5:15]  — each mentioned in 4 of the 6 body sections
    rare      = entities[15:25] — each mentioned in exactly 2 body sections
    singleton = entities[25:30] — mentioned only in the final "Remarks" paragraph

    Design rationale
    ----------------
    * Popular entities appear near the START of every paragraph so they are
      consistently assigned to the first chunk of each map window, giving them
      multiple shared chunks and thus satisfying ingest_comention_min_chunks=2.
    * Singleton entities appear only once (last paragraph) → mention_count=2
      after reduce_entities (initial=1 then +1 = 2), which is below the bench
      threshold of ingest_wiki_min_mentions=3 → no wiki page.
    """
    popular = entities[0:5]
    common = entities[5:15]
    rare = entities[15:25]
    singleton = entities[25:30]

    N_SECTIONS = 6

    # Assign common: entity i appears in 4 sections (indices i%6, (i+1)%6, (i+2)%6, (i+3)%6)
    common_schedule: list[list[str]] = [[] for _ in range(N_SECTIONS)]
    for i, ent in enumerate(common):
        for delta in range(4):
            sec = (i + delta) % N_SECTIONS
            common_schedule[sec].append(ent)

    # Assign rare: entity i appears in 2 sections
    rare_schedule: list[list[str]] = [[] for _ in range(N_SECTIONS)]
    for i, ent in enumerate(rare):
        s1 = i % N_SECTIONS
        s2 = (i + N_SECTIONS // 2) % N_SECTIONS
        rare_schedule[s1].append(ent)
        if s2 != s1:
            rare_schedule[s2].append(ent)

    parts: list[str] = []

    # Title + abstract
    parts.append(
        "Distributed Hash Tables and Ring-Based Architectures: A Comprehensive Survey\n\n"
        "Abstract. " + _make_para(rng, popular[:3], n_filler=8)
    )

    section_names = [
        "Introduction",
        "Architectural Background",
        "System Design",
        "Implementation Details",
        "Experimental Evaluation",
        "Discussion and Related Work",
    ]

    for sec_i, sec_name in enumerate(section_names):
        sec_common = common_schedule[sec_i]
        sec_rare = rare_schedule[sec_i]

        # Para 1: popular[0:3] + first 2 common for this section
        p1_ents = list(popular[:3]) + sec_common[:2]
        # Para 2: popular[3:5] + next 2 common + first rare
        p2_ents = list(popular[3:]) + sec_common[2:4] + sec_rare[:1]
        # Para 3: popular[0:2] + remaining rare (if any)
        p3_ents = list(popular[:2]) + sec_rare[1:]
        # Para 4 (extra): popular[2:4] + last common slot
        p4_ents = list(popular[2:4]) + sec_common[4:6]

        # Filter empty entity lists (some sections may have fewer rare entities)
        def _para_safe(ents: list[str], filler: int) -> str:
            if not ents:
                ents = list(popular[:2])
            return _make_para(rng, ents, n_filler=filler)

        section_body = "\n\n".join(
            [
                _para_safe(p1_ents, 6),
                _para_safe(p2_ents, 7),
                _para_safe(p3_ents, 7),
                _para_safe(p4_ents, 8),
            ]
        )
        parts.append(f"\n\n{sec_i + 1}. {sec_name}\n\n{section_body}")

    # Final remarks: popular[0:2] + ALL singleton entities
    # Singleton entities appear ONLY here → 1 extraction → mention_count=2 < 3 → no wiki page
    final_para = _make_para(rng, list(popular[:2]) + list(singleton), n_filler=10)
    parts.append(f"\n\n7. Final Remarks\n\n{final_para}")

    return "".join(parts)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_corpus(seed: int = 7) -> Corpus:
    """Return a fully deterministic synthetic corpus.

    Same *seed* always produces identical ``text`` bytes and entity list.
    """
    rng = random.Random(seed)
    entities: list[str] = rng.sample(ENTITY_POOL, 30)
    text = _generate_corpus_text(rng, entities)
    return Corpus(text=text, entities=entities)
