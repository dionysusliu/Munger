# Taesoo Kim

**Taesoo Kim** is a computer scientist and faculty member at the [[Georgia Institute of Technology]]. His research spans [[operating systems]], [[systems security]], and [[performance engineering]]. He is particularly known for his work on systematizing software performance analysis and developing reusable methodologies for optimizing sequential execution bottlenecks in modern systems.

## Research Interests
* [[Operating Systems]]
* [[Systems Security]]
* [[Performance Optimization]]
* [[Serial Performance]]
* [[Parallel Computing]]
* [[Software Profiling & Diagnostics]]

## Key Publication: Principles and Methodologies for Serial Performance Optimization
Co-authored with Sujin Park, Mingyu Guan, and Xiang Cheng, this work addresses a foundational challenge in systems research: how to systematically identify, analyze, and optimize sequential performance bottlenecks.

### Motivation & Scope
Performance optimization has long been a central goal in the [[systems community]]. An analysis of the past decade of premier systems conferences revealed that **43% of papers** published at [[OSDI]] and [[SOSP]] address performance-related topics. Rather than proposing a one-off solution to a specific bottleneck, the authors pose a meta-question:
> *“Can we systematize how sequential performance is optimized in practice?”*

To answer this, the team conducted a comprehensive literature review, analyzing **477 OSDI/SOSP papers** published over a 10-year period. The goal was to distill recurring optimization patterns into a unified, actionable framework.

### Core Methodology & Framework
The research positions performance optimization not as a system-building exercise, but as a diagnostic and methodological discipline. The proposed framework follows a structured workflow:
1. **Profile & Diagnose:** Use instrumentation and profiling tools to isolate the exact cause of performance degradation (e.g., [[lock contention]], cache thrashing, or I/O serialization).
2. **Classify the Bottleneck:** Determine whether the bottleneck is inherently sequential or can be mitigated through parallelization.
3. **Apply Targeted Optimizations:** Utilize distilled, repeatable methodologies tailored to the bottleneck type.
4. **Iterate & Validate:** Measure throughput improvements and reassess, recognizing that optimization is often an iterative process.

### Key Insights
* **Parallelism Has Hard Limits:** While multithreading and concurrency improve throughput, they cannot overcome sequential bottlenecks. The framework explicitly references [[Amdahl's Law]], demonstrating that speedup is fundamentally capped by the sequential portion of a program.
* **From Ad-Hoc Fixes to Systematic Practice:** By cataloging optimization strategies across hundreds of papers, the work transforms isolated case studies into a generalized guide applicable to diverse systems problems.
* **Practical Guidance Over Novel Systems:** The paper emphasizes that practitioners do not always need to build new systems; instead, they can leverage proven sequential optimization methodologies to extract maximum performance from existing architectures.

## Academic Affiliation & Community Impact
* **Institution:** [[Georgia Institute of Technology]], College of Computing
* **Venues:** Regular contributor and reviewer for top-tier systems conferences including [[OSDI]], [[SOSP]], [[EuroSys]], and [[USENIX ATC]].
* **Impact:** Bridges theoretical performance modeling with practical systems engineering, providing developers and researchers with a structured playbook for tackling serial bottlenecks in production workloads.

## See Also
* [[Georgia Institute of Technology]]
* [[Operating Systems Research]]
* [[Performance Engineering]]
* [[Amdahl's Law]]
* [[OSDI]]
* [[SOSP]]
* [[Software Profiling]]

## References
* Park, S., Guan, M., Cheng, X., & Kim, T. *Principles and Methodologies for Serial Performance Optimization*. Georgia Institute of Technology.
* OSDI/SOSP 10-Year Performance Paper Analysis (477 papers reviewed).
* [Georgia Tech Systems Group](https://systems.gatech.edu)