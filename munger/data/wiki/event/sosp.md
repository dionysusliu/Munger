# SOSP

**Principles and Methodologies for Serial Performance Optimization** is a research paper and methodological guide presented to the [[Symposium on Operating Systems Principles|SOSP]] and [[Symposium on Operating Systems Design and Implementation|OSDI]] communities. The work addresses a foundational challenge in [[Systems Research]]: how to systematically identify, analyze, and resolve sequential performance bottlenecks in modern software systems.

## Authors & Affiliation
* **Authors:** Sujin Park, Mingyu Guan, Xiang Cheng, Taesoo Kim
* **Affiliation:** [[Georgia Institute of Technology]]

## Overview
Performance optimization remains a long-standing and central goal within the systems community. An analysis of publication trends shows that approximately **43%** of papers accepted to [[OSDI]] and [[SOSP]] over the past decade focus primarily on performance improvements. 

Rather than introducing a novel system architecture or benchmark tool, this paper asks a meta-question:
> *"Can we systematize how sequential performance is optimized in practice?"*

The authors position the work not as a one-off solution, but as a reusable guide for researchers and engineers to tackle performance challenges across diverse domains.

## Methodology
To construct a unified optimization framework, the authors employed a large-scale empirical approach:
* Reviewed **477** papers published in [[OSDI]] and [[SOSP]] over a ten-year period.
* Extracted recurring patterns, techniques, and debugging workflows used to improve sequential execution paths.
* Synthesized these practices into a structured, domain-agnostic framework.
* Emphasized practical applicability, aiming to provide actionable guidance rather than theoretical abstractions.

## Key Insights

### 1. Profiling Identifies the Bottleneck
Effective optimization begins with rigorous [[Performance Profiling]]. A common real-world scenario reveals that degraded throughput often stems from synchronization overhead, particularly [[Lock Contention]]. The paper stresses that identifying the bottleneck is only the first step, posing the critical follow-up: *"You found a bottleneck. Now what?"*

### 2. The Hard Limits of Parallelism
While scaling across multiple threads or cores can improve throughput, not all workloads can be effectively parallelized. The maximum achievable speedup is fundamentally constrained by the sequential portion of the program, as formalized in [[Amdahl's Law]].

### 3. Sequential Optimization Remains Crucial
Despite industry trends heavily favoring [[Concurrency]] and [[Parallel Computing]], optimizing sequential execution paths continues to deliver substantial performance gains. The authors argue that sequential tuning is complementary to parallelization, not obsolete, and must remain a core competency in systems engineering.

## Optimization Framework
The paper distills its findings into a repeatable methodology for sequential performance tuning:
1. **Isolation:** Use profiling and tracing tools to pinpoint exact sequential bottlenecks (e.g., lock contention, serialized I/O, algorithmic complexity).
2. **Constraint Analysis:** Evaluate the theoretical parallelization limits of the identified component using models like [[Amdahl's Law]].
3. **Sequential Transformation:** Apply proven techniques such as data structure redesign, algorithmic refinement, cache-aware memory access, and lock-free/lock-reduction patterns.
4. **Validation & Iteration:** Measure throughput and latency improvements, ensuring that sequential optimizations do not inadvertently introduce new scalability ceilings or concurrency hazards.

## See Also
* [[Amdahl's Law]]
* [[Lock Contention]]
* [[Performance Profiling]]
* [[Concurrency]]
* [[Parallel Computing]]
* [[OSDI]]
* [[SOSP]]
* [[Systems Research]]

## References
* Park, S., Guan, M., Cheng, X., & Kim, T. *Principles and Methodologies for Serial Performance Optimization*. [[Georgia Institute of Technology]].
* Amdahl, G. M. (1967). "Validity of the Single Processor Approach to Achieving Large Scale Computing Capabilities". *AFIPS Conference Proceedings*.
* [[OSDI]] & [[SOSP]] Proceedings Archive (Past Decade).