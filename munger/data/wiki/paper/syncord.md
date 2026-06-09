# SynCord

**SynCord** is a research system and optimization framework introduced at [[OSDI]] 2022 that addresses [[Lock Contention]] bottlenecks in concurrent applications. By enabling dynamic, customizable policies for reordering threads within lock waiting queues, SynCord improves the efficiency of sequential execution within [[Critical Section]]s, ultimately increasing overall system throughput.

## Background: Lock Contention and Parallelism Limits

### Amdahl's Law and Sequential Bottlenecks
Identifying a bottleneck is only the first step in system optimization. While [[Parallel Computing]] and multithreading can significantly improve throughput, performance scaling is fundamentally constrained by the sequential portions of a program. This limitation is formalized by [[Amdahl's Law]], which states that the maximum speedup is bounded by the fraction of code that must execute sequentially. Consequently, optimizing sequential execution remains a critical component of high-performance system design.

### Critical Sections and Lock Waiting Queues
In concurrent systems, multiple threads execute in parallel until they reach a [[Critical Section]]. At this point:
1. Only one thread is permitted to enter and execute the critical section sequentially.
2. All other contending threads are placed into a lock waiting queue.
3. The sequential execution of the queued threads becomes the primary performance bottleneck.

Optimizing how threads are managed within this waiting queue is essential for reducing idle time and improving cache utilization.

## Sequential Optimization Framework

To systematically address sequential bottlenecks, the SynCord research team posed three foundational questions:
1. Can we systematize sequential optimization?
2. How many distinct optimization approaches exist?
3. When should each approach be applied?

### Three Principles of Sequential Execution
Through analysis, the authors distilled sequential optimization into three core principles:
1. **Remove**: Eliminate unnecessary tasks from the execution sequence.
2. **Replace**: Substitute an existing task with a faster or more efficient alternative.
3. **Reorder**: Rearrange tasks to improve data locality, cache utilization, or execution flow.

### Eight Optimization Methodologies
Building upon these three principles, the framework identifies eight common optimization patterns for sequential performance. Each methodology is derived from one or more of the core principles, providing a unified taxonomy for understanding and exploring sequential optimization techniques. Key methodologies include:
* **Batching**: Grouping threads to maximize cache reuse and reduce context-switch overhead.
* **Caching**: Pre-fetching or retaining frequently accessed data to minimize memory latency.
* **Precomputation**: Calculating results ahead of time to reduce critical section workload.
*(Note: The full set of eight methodologies, including visualizations and real-world examples from systems literature, is detailed in the original publication.)*

## Contributions

SynCord introduces a flexible, runtime-adaptive mechanism for sequential optimization. Rather than relying on static scheduling policies, SynCord allows systems to:
* Dynamically select and apply custom reordering policies for lock waiting queues.
* Adapt queue management strategies based on real-time workload characteristics and hardware topology.
* Seamlessly integrate with existing synchronization primitives to minimize overhead.

By shifting from fixed scheduling to policy-driven thread reordering, SynCord achieves higher throughput and better hardware utilization in highly contended environments.

## Related Systems

Several prior works have explored sequential optimization within lock contention:
* **[[ShflLock]]** ([[SOSP]] 2019): Focuses on reordering the lock waiting queue to accelerate progress and reduce tail latency.
* **[[CNA]]** ([[EuroSys]] 2019): Implements thread batching strategies to improve underlying cache utilization during critical section execution.
* SynCord extends these approaches by providing a generalized, dynamic policy framework rather than a single fixed optimization technique.

## References

1. *SynCord: Dynamic Custom Policies for Lock Waiting Queues*. [[OSDI]] 2022.
2. *ShflLock: Optimizing Lock Contention via Queue Reordering*. [[SOSP]] 2019.
3. *CNA: Cache-Aware Thread Batching for Synchronization*. [[EuroSys]] 2019.
4. Amdahl, G. M. (1967). "Validity of the Single Processor Approach to Achieving Large Scale Computing Capabilities".

## See Also
* [[Lock Contention]]
* [[Amdahl's Law]]
* [[Critical Section]]
* [[Thread Scheduling]]
* [[Sequential Optimization]]
* [[OSDI]] Proceedings