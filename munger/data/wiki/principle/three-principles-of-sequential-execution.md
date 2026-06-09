# Three Principles of Sequential Execution

## Overview
The **Three Principles of Sequential Execution** is a systematic framework for understanding and optimizing sequential bottlenecks in concurrent systems. Despite the widespread focus on parallelism, sequential execution segments remain critical performance constraints. This framework categorizes optimization strategies into three foundational principles, which map to eight practical methodologies commonly observed in systems research.

## Background: The Sequential Bottleneck
In concurrent systems, performance is heavily governed by [[Amdahl's Law]], which dictates that the speedup of a program using multiple processors is limited by the time needed for the sequential fraction of the program. 

Key characteristics of sequential bottlenecks include:
* **Critical Sections**: Code regions where only one thread can execute at a time to maintain data consistency.
* **Lock Waiting Queues**: When a [[Critical Section]] is occupied, contending threads are serialized by joining a queue.
* **Throughput Impact**: Even with many concurrent threads running, the sequential portion dictates overall system throughput. Optimizing this segment is therefore crucial for achieving higher performance.

## The Three Core Principles
To optimize an existing sequence of tasks, all sequential optimizations can be reduced to three fundamental operations:

1. **Remove** a task  
   Eliminate unnecessary operations, redundant checks, or superfluous synchronization.
2. **Replace** with a faster one  
   Substitute a slow operation with a more efficient alternative (e.g., atomic instructions instead of heavy mutexes, or optimized data structures).
3. **Reorder** tasks for better locality  
   Change the execution order to improve cache utilization, reduce contention, or align with hardware pipeline characteristics.

These principles provide a unified mental model for analyzing and designing sequential optimizations.

## Practical Methodologies
Derived from the three core principles, researchers have identified a set of common optimization patterns. Together, they form a unified taxonomy for sequential performance engineering:

| Methodology | Description | Linked Principle |
|-------------|-------------|------------------|
| [[Batching]] | Group multiple operations or threads to reduce per-unit overhead and improve cache utilization. | Reorder / Replace |
| [[Caching]] | Store frequently accessed or computed results to avoid repeated sequential work. | Remove / Replace |
| [[Precomputing]] | Perform calculations ahead of time to eliminate sequential delays during critical paths. | Remove |
| [[Relaxation]] | Weaken strict ordering or consistency guarantees where safe, allowing more parallel progress. | Reorder / Remove |
| [[Contextualization]] | Adapt execution strategies based on runtime state, workload characteristics, or hardware topology. | Replace / Reorder |
| [[Hardware Layering]] | Leverage hardware-specific features (e.g., NUMA awareness, cache hierarchy, prefetching) to accelerate sequential steps. | Replace |
| [[Deferring]] | Delay non-critical sequential work to later stages, overlapping it with concurrent execution. | Remove / Reorder |
| *(Framework Total)* | **Eight methodologies** systematically cover common sequential optimization patterns. | All three |

*Note: Definitions, visualizations, and real-world implementations of each methodology are detailed in the foundational paper.*

## Literature Review & Validation
The framework was validated through a comprehensive manual review of top-tier systems conferences over a 10-year span:

* **Total Papers Reviewed**: 477 papers from [[OSDI]] and [[SOSP]]
* **Non-Performance Papers**: 271
* **Performance Optimization Papers**: 206
* **Distribution of Methodologies** (sampled from performance papers):
  * [[Batching]]: 52 papers
  * [[Caching]] & [[Relaxation]]: Frequently co-occurring with batching and deferring
  * Remaining methodologies distributed across synchronization, storage, and networking subsystems

This empirical analysis confirms that the eight methodologies effectively cover the vast majority of sequential optimization techniques published in modern systems literature.

## Key Research Questions
The framework was developed to address three foundational questions in systems performance engineering:
1. Can we systematize sequential optimization?
2. How many distinct approaches exist?
3. When should each approach be applied in practice?

## Notable Examples & Implementations
Recent systems research demonstrates the practical application of these principles:
* **Queue Reordering**: [[ShflLock]] (SOSP'19) reorders the lock waiting queue to accelerate progress under high contention.
* **Thread Batching**: [[CNA]] (EuroSys'19) batches threads to better utilize underlying cache hierarchies and reduce synchronization overhead.
* **Dynamic Policies**: [[SynCord]] (OSDI'22) allows dynamic, custom reordering policies tailored to workload characteristics at runtime.

## See Also
* [[Amdahl's Law]]
* [[Critical Section]]
* [[Lock Contention]]
* [[Throughput Optimization]]
* [[Concurrent Programming]]
* [[OSDI]]
* [[SOSP]]
* [[Performance Optimization]]