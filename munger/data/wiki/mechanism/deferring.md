# Deferring

## Overview
**Deferring** is a sequential execution optimization methodology that improves system performance by identifying non-critical tasks within a processing sequence and moving them to execute later. By decoupling low-priority or independently resolvable operations from the immediate critical path, deferring reduces latency, alleviates thread blocking, and improves overall resource utilization.

It is one of eight core methodologies systematized for [[Sequential Execution Optimization]], alongside [[Batching]], [[Caching]], [[Precomputing]], [[Relaxation]], [[Contextualization]], [[Hardware]], and [[Layering]].

## Mechanism: Working with Causal Chains
At its core, deferring operates by analyzing and restructuring **causal chains**—dependency-ordered sequences where each operation relies on the completion or state produced by its predecessor. When causal chains are strictly linear, threads frequently stall in lock waiting queues or synchronization barriers. Deferring breaks non-essential links to shorten the critical path.

### 1. Baseline Causal Chain
In a typical sequential execution, tasks form a rigid dependency chain:
```
Before:  a → b → c → d → e → f
```
Each task blocks the next until completion. If `c` or `e` involves heavy I/O, lock acquisition, or complex computation, downstream tasks (`d`, `f`) and waiting threads are forced to idle.

### 2. Causal Dependency Analysis
Deferring evaluates the causal chain to identify tasks that:
- Do **not** immediately unblock critical downstream operations
- Have **relaxed consistency** or eventual-execution semantics
- Can be safely scheduled when system resources (CPU, cache, I/O bandwidth) are optimal

### 3. Chain Restructuring via Deferral
Non-essential tasks are extracted from the immediate causal chain and scheduled asynchronously or at a batch boundary:
```
After:   a → b → d → f        (Critical Path)
         ↓
         c, e                  (Deferred to background/later epoch)
```
**How it works:**
- **Shortens the critical causal path:** By removing `c` and `e` from the immediate sequence, `d` and `f` execute sooner, reducing end-to-end latency.
- **Reduces synchronization overhead:** Threads no longer join lock waiting queues for deferred operations, decreasing context-switching and contention.
- **Enables better resource alignment:** Deferred tasks can be grouped or rescheduled to maximize spatial/temporal locality, often overlapping with idle cycles or dedicated background workers.

## Relationship to Optimization Principles
Deferring is systematically derived from the three foundational principles of sequential execution optimization:
- **[[Reorder]]:** Primary mechanism. Tasks are moved out of their original sequence to execute at a more optimal time or epoch.
- **[[Remove]]:** Tasks are temporarily removed from the immediate critical path (not deleted, just relocated in time).
- **[[Replace]]:** A lightweight placeholder, acknowledgment, or fast-path operation often replaces the deferred task in the critical chain to maintain responsiveness.

## When to Apply Deferring
Based on systematized analysis of optimization patterns, deferring is most effective when:
- ✅ **Dependencies are loose or eventually consistent:** Correctness does not require immediate execution (e.g., logging, metrics, background cleanup).
- ✅ **Lock contention is high:** Threads frequently stall in lock waiting queues; deferring lock-heavy or serializing operations reduces blocking.
- ✅ **I/O or compute can be decoupled:** Network flushes, disk writes, or heavy transformations can be scheduled asynchronously.
- ✅ **Batching opportunities exist:** Deferring is inherently used in [[Batching]] to accumulate tasks before execution, improving spatial/temporal locality and enabling stale-task discarding.

## Real-World Patterns & Examples
Deferring was identified in **62** performance optimization papers across 10 years of OSDI & SOSP proceedings. Common implementations include:
- **Lazy Evaluation & Write-Back Caching:** Deferring disk writes until cache eviction or explicit sync commands.
- **Asynchronous Lock Acquisition:** Replacing blocking lock calls with deferred retries, ticket locks, or RCU-style deferments.
- **Background Garbage Collection:** Moving memory reclamation out of the allocation fast-path to avoid pausing causal chains.
- **Deferred Acknowledgments:** Networking stacks delaying ACKs to coalesce responses and reduce interrupt overhead.

## Related Methodologies
- [[Batching]]: Groups deferred tasks to amortize overhead, discard stale work, and maximize locality.
- [[Relaxation]]: Weakens strict causal dependencies to make deferring semantically safe.
- [[Precomputing]]: Opposite approach; executes tasks earlier in the causal chain to avoid waiting later.
- [[Caching]]: Often stores results of deferred computations for faster future access.
- [[Layering]]: Separates fast-path and slow-path execution, enabling clean deferral boundaries.

## References & Research Context
- Systematization of [[Sequential Execution Optimization]] principles: Remove, Replace, Reorder
- Analysis of 206 performance optimization papers from OSDI & SOSP (2013–2023)
- Formal definitions, visualizations, and causal chain diagrams available in our associated research paper.