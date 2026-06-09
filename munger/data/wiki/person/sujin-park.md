# Sujin Park

**Sujin Park** is a computer systems researcher affiliated with the [[Georgia Institute of Technology]]. Their work focuses on performance optimization, with a particular emphasis on systematizing methodologies for sequential (serial) performance bottlenecks in systems software.

## Academic Affiliation & Collaborators
* **Institution:** [[Georgia Institute of Technology]]
* **Key Collaborators:** [[Mingyu Guan]], [[Xiang Cheng]], [[Taesoo Kim]]
* **Research Domain:** [[Operating Systems]], [[Performance Optimization]], [[Systems Research]]

## Research Focus: Serial Performance Optimization
Performance optimization has long been a central goal in the systems community, representing approximately **43%** of publications at top-tier systems conferences over the past decade. Park's research takes a meta-analytical approach to this domain, moving beyond single-system solutions to develop generalized optimization frameworks.

### Key Publication
* **Title:** *Principles and Methodologies for Serial Performance Optimization*
* **Methodology:** Comprehensive literature review of **477 papers** published at [[OSDI]] and [[SOSP]] over a ten-year span.
* **Core Objective:** Systematize how sequential performance is optimized in practice by distilling recurring methodologies into a unified, actionable framework.

## Core Principles & Framework
The research framework is designed as a practical guide for systems engineers and researchers facing sequential bottlenecks that cannot be resolved through parallelization alone. Key principles include:

* **Meta-Optimization Approach:** Rather than proposing a novel system, the work provides a structured methodology applicable across diverse systems problems.
* **Profiling-Driven Discovery:** Emphasizes systematic profiling to identify root causes of performance degradation (e.g., discovering [[Lock Contention]] as a hidden bottleneck).
* **Limits of Parallelism:** Acknowledges that not all workloads can be parallelized. The framework addresses the theoretical and practical constraints where [[Amdahl's Law]] limits speedup, making serial optimization critical.
* **Recurring Optimization Patterns:** Identifies and categorizes common techniques used in practice to improve sequential execution paths, thread scaling, and resource utilization.

## Practical Application Workflow
Based on the distilled framework, the recommended optimization workflow typically follows:
1. **Profile & Identify:** Use system profiling tools to locate the exact bottleneck.
2. **Classify Bottleneck Type:** Determine if the issue stems from contention, serialization, I/O blocking, or algorithmic inefficiency.
3. **Apply Methodology:** Select from the unified framework of proven optimization patterns.
4. **Validate & Iterate:** Measure throughput/scalability improvements across varying thread counts and workloads.

## See Also
* [[Georgia Institute of Technology]]
* [[OSDI]] (Operating Systems Design and Implementation)
* [[SOSP]] (Symposium on Operating Systems Principles)
* [[Performance Optimization]]
* [[Lock Contention]]
* [[Profiling (Computer Systems)]]
* [[Amdahl's Law]]

## Notes
* The research highlights that performance optimization remains a dominant and recurring theme in systems research.
* The framework is intentionally designed to be problem-agnostic, serving as a methodological guide rather than a point solution.
* Findings underscore the continued relevance of serial performance tuning even in highly concurrent, multi-core architectures.

[[Category:Researchers]] [[Category:Computer Systems]] [[Category:Georgia Institute of Technology]] [[Category:Performance Optimization]]