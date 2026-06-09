# CNA

**CNA** is a lock contention optimization technique introduced at [[EuroSys]] 2019. It addresses performance bottlenecks in concurrent systems by batching threads within lock waiting queues to improve [[Cache Locality]] and optimize sequential execution within [[Critical Section]]s.

## Overview
In highly concurrent applications, profiling frequently reveals that [[Lock Contention]] is a primary performance bottleneck. While increasing parallelism generally improves system throughput, the achievable speedup is fundamentally constrained by the sequential portions of the program, as formalized by [[Amdahl's Law]]. CNA specifically targets the sequential execution phase that occurs when threads serialize at a shared lock.

## Background & Motivation

### The Parallelism Limit
- Parallelism increases overall throughput, but not all workloads can be fully parallelized.
- As thread counts scale, the sequential portion of the program becomes the dominant bottleneck.
- Optimizing sequential execution remains crucial for maximizing performance in concurrent environments.

### Sequential Execution in Critical Sections
When multiple threads contend for a shared lock, execution follows a predictable serialization pattern:
1. Concurrent threads execute until they reach a critical section.
2. Only one thread may enter the critical section at a time.
3. Remaining threads join a lock waiting queue.

This serialization forces threads to execute sequentially, making the scheduling and grouping of waiting threads a primary target for performance optimization.

## Core Principles of Sequential Optimization
Research into sequential execution optimization identifies three foundational principles for improving performance within serialized code paths:
1. **Remove**: Eliminate unnecessary or redundant tasks from the execution sequence.
2. **Replace**: Substitute existing tasks with faster or more computationally efficient alternatives.
3. **Reorder**: Rearrange tasks to improve data locality, reduce pipeline stalls, and minimize cache misses.

## CNA Approach & Mechanism
CNA primarily leverages the **Reorder** principle to optimize lock waiting queues:
- **Thread Batching**: Instead of waking and processing waiting threads individually, CNA groups them into logical batches based on execution patterns.
- **Cache Utilization**: By batching threads that will execute similar or adjacent memory accesses, CNA significantly improves CPU cache locality during sequential critical section execution.
- **Throughput Improvement**: This reduces cache thrashing and memory latency, leading to higher overall system throughput under high contention scenarios.

## Broader Optimization Framework
The research surrounding CNA aims to systematize sequential optimization techniques, providing a unified methodology for understanding, categorizing, and applying performance improvements.

### Research Questions
The framework addresses three core investigative questions:
1. Can we systematically categorize sequential optimization techniques?
2. How many distinct optimization approaches exist?
3. Under what conditions should each approach be applied?

### The Eight Methodologies
Building upon the three core principles, the research identifies eight distinct optimization methodologies for sequential performance. Each methodology is derived from strategic combinations of removing, replacing, or reordering tasks within a critical section. For detailed definitions, visualizations, and implementation guidelines, refer to the original publication.

## Related Work
CNA exists within a broader research ecosystem focused on lock queue optimization and sequential execution tuning:
- **[[ShflLock]]** ([[SOSP]] 2019): Optimizes performance by reordering the lock waiting queue to accelerate progress and reduce thread starvation.
- **[[SynCord]]** ([[OSDI]] 2022): Introduces dynamic, custom scheduling policies for thread reordering within lock queues, adapting to runtime workload characteristics.

## See Also
- [[Lock Contention]]
- [[Amdahl's Law]]
- [[Critical Section]]
- [[Thread Batching]]
- [[Cache Locality]]
- [[Thread Synchronization]]

## References
- *CNA: Batching Threads for Better Cache Utilization in Lock Contention*. [[EuroSys]] 2019.
- *ShflLock: Reordering Lock Waiting Queues for Faster Progress*. [[SOSP]] 2019.
- *SynCord: Dynamic Custom Policies for Lock Queue Reordering*. [[OSDI]] 2022.