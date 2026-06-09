# OSDI

**OSDI** (Operating Systems Design and Implementation) is a top-tier academic symposium in the field of [[Systems Research]] and [[Operating Systems]]. Co-sponsored by [[USENIX]] and [[ACM SIGOPS]], OSDI serves as a premier venue for publishing foundational and applied research on system design, implementation, evaluation, and management. It is widely recognized alongside [[SOSP]] as one of the two most influential conferences in the operating systems community.

## Research Landscape & Performance Focus

Performance optimization has remained a long-standing and central goal within the systems community. Over the past decade, approximately **43% of all OSDI and SOSP papers** have addressed performance-related challenges, reflecting the continuous demand for efficient, scalable, and responsive systems.

### Featured Study: [[Principles and Methodologies for Serial Performance Optimization]]

| **Authors** | Sujin Park, Mingyu Guan, Xiang Cheng, Taesoo Kim |
|-------------|--------------------------------------------------|
| **Affiliation** | [[Georgia Institute of Technology]] |
| **Publication Venue** | [[OSDI]] / [[SOSP]] |
| **Research Type** | Meta-analysis & Systematization |

#### Motivation & Scope
Rather than introducing a novel system or patching a single bottleneck, this work addresses a foundational meta-question:  
> *"Can we systematize how sequential performance is optimized in practice?"*

The authors conducted a comprehensive review of **477 OSDI/SOSP papers** published over a ten-year period. By analyzing recurring patterns, they distilled a **unified framework of serial optimization methodologies**. The paper positions itself not as a point solution, but as a practical guide applicable to a wide range of performance engineering scenarios.

#### Core Methodologies & Insights

* **Profiling-Driven Bottleneck Identification**  
  Optimization workflows typically begin with [[Profiling]] to isolate the root cause of latency or throughput degradation. In practice, bottlenecks frequently manifest as [[Lock Contention]], cache coherence overhead, or memory access serialization rather than raw CPU limitations.

* **The Fundamental Limit of [[Parallel Computing]]**  
  While increasing thread counts or leveraging multi-core architectures can improve throughput, gains are inherently constrained by the sequential portions of a workload. This relationship is formally captured by **[[Amdahl's Law]]**:
  * The theoretical speedup is capped by the fraction of execution that must remain sequential.
  * Beyond a certain concurrency threshold, adding parallelism yields diminishing returns, making serial optimization increasingly critical.

* **Sequential Optimization Framework**  
  The paper proposes a structured, repeatable methodology for tackling serial bottlenecks:
  1. **Profile & Isolate** the critical path using deterministic measurement tools.
  2. **Classify** the bottleneck (e.g., synchronization, memory latency, algorithmic inefficiency).
  3. **Apply Targeted Optimizations** such as lock-free data structures, critical section reduction, batching, or algorithmic redesign.
  4. **Validate & Iterate** to ensure improvements do not introduce regression or correctness issues.

* **Practical Application Example**  
  When profiling reveals that [[Lock Contention]] is the primary performance limiter, developers can leverage the distilled framework to restructure critical sections, adopt fine-grained locking, or transition to wait-free synchronization primitives. This approach improves throughput without relying solely on hardware scaling or parallel decomposition.

## Conclusion

The systematization of serial performance optimization highlights a crucial reality in systems engineering: **parallelism alone cannot solve all performance challenges**. By distilling a decade of community knowledge into a unified methodology, this work provides practitioners with a repeatable, evidence-based guide for diagnosing and resolving sequential bottlenecks. As hardware scaling slows and workloads grow increasingly complex, rigorous serial optimization remains a cornerstone of high-performance system design.

## See Also
* [[Performance Optimization]]
* [[Amdahl's Law]]
* [[Lock Contention]]
* [[Profiling]]
* [[Parallel Computing]]
* [[SOSP]]
* [[USENIX]]
* [[ACM SIGOPS]]

## External Resources
* [Official OSDI Conference Page](https://www.usenix.org/conference/osdi)
* [USENIX Conference Archive](https://www.usenix.org/conferences)
* [ACM SIGOPS Hall of Fame & Proceedings](https://www.sigops.org/)