# Batching

**Batching** is a sequential execution optimization methodology that coalesces multiple independent or related tasks into a single, larger operation to amortize fixed overhead and improve system throughput. It is one of the eight core methodologies systematized in the [[SynCord]] framework (OSDI '22) and is widely documented across performance-critical systems research.

## Overview
In systems where fine-grained task invocation incurs high per-call costs (e.g., lock acquisition, context switches, I/O setup, or network headers), executing tasks individually becomes a bottleneck. Batching addresses this by temporarily accumulating work, applying transformation rules, and executing the aggregated unit. A manual review of 10 years of [[OSDI]] & [[SOSP]] literature (206 performance optimization papers) identified batching in 52 papers, confirming it as one of the most prevalent sequential optimization patterns.

## How It Works: The Causal Chain
The performance gains from batching follow a deterministic causal mechanism. Each step triggers the next, transforming a high-overhead sequential flow into an optimized execution path:

1. **High Per-Call Overhead Detected** → Each individual task incurs expensive fixed costs on invocation.
2. **Task Accumulation & Deferral** → Incoming requests are queued rather than executed immediately. Batching inherently [[Deferring|defers]] earlier tasks to reach a size, time, or epoch threshold.
3. **Stale Task Filtering** → During batch formation, outdated, redundant, or superseded tasks are identified and dropped. This applies the [[Remove a Task|Remove]] principle to eliminate unnecessary work.
4. **Coalescing & Reordering** → Remaining tasks are merged and arranged to align with underlying hardware access patterns. This maximizes [[Spatial Locality]] and [[Temporal Locality]], operationalizing the [[Reorder Tasks|Reorder]] principle.
5. **Bulk Execution Substitution** → The aggregated unit replaces many fine-grained calls with a single optimized operation, applying the [[Replace with a Faster One|Replace]] principle.
6. **Outcome Realization** → 
   - **Fewer total tasks** are dispatched to the execution engine.
   - The **batched task completes faster** due to reduced synchronization contention, amortized setup costs, and cache/disk-friendly access patterns.

```
Before: a → b → c → d → e → f (per-task overhead × 6)
After:  [a c e] → batched execution (overhead × 1, stale tasks removed, locality optimized)
```

## Core Optimization Principles Applied
Batching is a practical synthesis of three foundational sequential optimization principles:
- **Remove:** Discards stale or redundant sub-tasks before execution.
- **Replace:** Substitutes many expensive fine-grained invocations with a single bulk operation.
- **Reorder:** Defers and groups tasks to improve memory, storage, or lock acquisition locality.

## Common Implementation Patterns
- **[[Group Commit]]:** Aggregates multiple transaction log writes into a single disk I/O operation.
- **[[Write Buffer]]:** Holds in-memory updates before flushing them in bulk to persistent storage.
- **Network Packet Coalescing:** Combines small messages into larger frames to reduce per-packet header and interrupt overhead.
- **GPU/Kernel Batch Dispatch:** Groups compute kernels to minimize driver and OS context-switch costs.

## When to Use Batching
| ✅ Ideal Conditions | ❌ Anti-Patterns |
|-------------------|----------------|
| High fixed cost per task invocation | Strict per-request latency SLAs |
| Tasks are idempotent or commutative | Strong ordering or strict dependency requirements |
| Workload exhibits bursty or high-frequency patterns | Memory-constrained environments (batch accumulation increases footprint) |
| System can tolerate deferred execution for individual requests | Real-time or interactive foreground paths |

## Relationship to Other Methodologies
Batching rarely operates in isolation. It is frequently combined with:
- [[Caching]]: To avoid redundant computations within a batch.
- [[Precomputing]]: To prepare batch structures or indices ahead of accumulation windows.
- [[Hardware Optimization]]: To leverage DMA engines or vectorized execution on coalesced data.
- [[Relaxation]] & [[Contextualization]]: To adjust batch thresholds dynamically based on system load or data semantics.

## See Also
- [[Sequential Optimization]]
- [[Deferring]]
- [[Caching]]
- [[Precomputing]]
- [[Relaxation]]
- [[Contextualization]]
- [[Hardware Optimization]]
- [[Layering]]