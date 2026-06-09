# Precomputing

## Overview
**Precomputing** is a performance optimization methodology that shifts computational work from the critical execution path to idle or low-contention periods. By calculating results, building data structures, or resolving dependencies ahead of time, systems can dramatically reduce latency when actual requests arrive. Precomputing is one of the eight core sequential optimization methodologies identified in systems research (e.g., [[OSDI]]/[[SOSP]] literature), alongside [[Caching]], [[Batching]], [[Deferring]], and [[Relaxation]].

## Core Optimization Principles
Precomputing directly applies the [[Three Principles of Sequential Execution]]:
* **Replace with a faster one**: Substitutes runtime computation with a pre-resolved result (e.g., lookup tables, materialized views).
* **Remove a task**: Eliminates intermediate steps in an execution sequence when the downstream outcome is already known.
* **Reorder tasks**: Shifts heavy or predictable computations to background threads, improving [[Locality]] and freeing the critical path for latency-sensitive operations.

## Mechanism: Working with Causal Chains

### Causal Chain Fundamentals
In sequential and concurrent systems, a **causal chain** represents a sequence of dependent operations where each step requires the output of the previous step to proceed:
```
Task A → Task B → Task C → Final Result
```
Causal chains inherently enforce sequential execution, creating bottlenecks when:
* Individual tasks have high computational or I/O overhead.
* Dependencies force strict ordering, preventing parallelism.
* Runtime conditions repeatedly traverse the same chain paths.

### How Precomputing Intervenes
Precomputing breaks or shortens causal chains by anticipating future dependencies and resolving them proactively:

1. **Chain Analysis & Prediction**
   * Identifies frequently traversed or predictable dependency paths.
   * Monitors system state to trigger precomputation during low-load windows.
   * Maps deterministic inputs to their eventual downstream outputs.

2. **Proactive Resolution**
   * Executes downstream tasks (`B` and `C`) before `A` is requested.
   * Stores resolved states in memory, persistent storage, or hardware registers.
   * Maintains versioning or epoch tracking to handle state changes.

3. **Runtime Short-Circuiting**
   * When a request enters the chain, the system checks for precomputed results.
   * If available, it bypasses intermediate causal dependencies.
   * Execution jumps directly to the precomputed state or applies a lightweight delta update.

### Causal Chain Transformation
| Phase | Standard Execution | Precomputed Execution |
|-------|-------------------|------------------------|
| **Structure** | `A → B → C → Result` (strictly sequential) | `Request → [Lookup/Validate] → Result` |
| **Latency** | Sum of all task latencies | Near constant-time lookup + validation overhead |
| **Dependency Handling** | Blocking, synchronous resolution | Asynchronous background resolution + synchronous consumption |
| **Resource Profile** | CPU/I/O bound during request | Background-bound during idle, memory-bound during request |

## Implementation Patterns
* **Materialized Views & Lookup Tables**: Precompute joins, aggregations, or hash mappings for frequent queries.
* **Speculative Execution**: Predict likely execution branches in [[nCord]] or lock-free structures and prepare results ahead of contention.
* **Index & State Pre-building**: Construct B-trees, bloom filters, or state machines during deployment or maintenance windows.
* **JIT/AOT Compilation**: Resolve type dependencies, inline functions, or optimize hot paths before runtime invocation.
* **Epoch-Based Precomputation**: Group updates into epochs, compute next-state transitions in the background, and swap atomically.

## Trade-offs & Considerations
* **Memory vs. CPU**: Precomputing trades compute cycles for memory footprint. Over-precomputing can cause cache pollution.
* **Staleness & Consistency**: Precomputed results must be invalidated or updated when causal chain inputs change. [[Caching]] coherence protocols often apply.
* **Prediction Accuracy**: Works best for deterministic or highly predictable workloads. Low hit rates waste background resources.
* **Initialization Overhead**: Cold-start latency may increase if precomputation is deferred until first use.
* **Concurrency Control**: Background precomputation must synchronize with live updates to avoid race conditions or torn states.

## Related Methodologies
* [[Caching]]: Stores past results; precomputing anticipates future results.
* [[Batching]]: Groups multiple requests; precomputing prepares for individual or batched requests.
* [[Deferring]]: Delays work to reduce contention; precomputing advances work to avoid critical-path delays.
* [[Contextualization]]: Adapts behavior based on runtime context; often paired with precomputed context-specific states.
* [[Layering]]: Separates abstraction levels; precomputing often occurs at lower layers to accelerate upper-layer causal chains.

## References
* Sequential Execution Optimization Taxonomy (OSDI '22)
* Analysis of 477 OSDI/SOSP papers: Precomputing appears in 35 performance-focused studies
* [[nCord]] synchronization patterns and speculative precomputation techniques
* Systems locality and background scheduling literature