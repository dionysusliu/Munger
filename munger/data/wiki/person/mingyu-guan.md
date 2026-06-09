# Mingyu Guan

**Mingyu Guan** is a systems researcher affiliated with the [[Georgia Institute of Technology]], focusing on operating systems, performance analysis, and the systematization of optimization methodologies.

## Research Focus
* [[Serial Performance Optimization]]
* Systems performance profiling and bottleneck analysis
* Concurrency, [[Lock Contention]], and [[Parallelism]] limitations
* Operating systems research and [[Systematization of Knowledge]]

## Notable Work
### Principles and Methodologies for Serial Performance Optimization
**Authors:** Sujin Park, Mingyu Guan, Xiang Cheng, Taesoo Kim  
**Institution:** [[Georgia Institute of Technology]]  
**Conference Context:** Analyzed publication trends across [[OSDI]] and [[SOSP]] over a 10-year period.

This work addresses a foundational meta-question in the systems community: *"Can we systematize how sequential performance is optimized in practice?"* Rather than proposing a new system or solving a single problem, the research distills recurring optimization patterns into a unified, actionable framework that serves as a guide for solving multiple performance challenges.

#### Methodology & Scope
* Reviewed **477 papers** from top-tier systems conferences over the past decade.
* Identified that performance optimization remains a long-standing priority, featuring in **~43%** of published papers.
* Distilled a unified framework of recurring optimization methodologies.
* Positioned as a practical, repeatable guide rather than a single-domain solution.

#### Key Insights
* **Bottleneck Identification:** Profiling frequently reveals sequential bottlenecks such as [[Lock Contention]].
* **Optimization Pathways:** Provides structured methodologies for transitioning from bottleneck discovery to targeted resolution.
* **Limits of Parallelism:** While [[Parallelism]] can improve throughput, it cannot eliminate sequential execution paths. The framework explicitly addresses how system speedup is fundamentally limited by the sequential portion of execution.

## Collaborators & Affiliations
* **Primary Institution:** [[Georgia Institute of Technology]]
* **Key Collaborators:** 
  * [[Sujin Park]]
  * [[Xiang Cheng]]
  * [[Taesoo Kim]]

## See Also
* [[Serial Performance Optimization]]
* [[Operating Systems Design and Implementation]]
* [[Symposium on Operating Systems Principles]]
* [[Systems Research]]

---
[[Category:Researchers]] | [[Category:Georgia Institute of Technology]] | [[Category:Systems Research]] | [[Category:Performance Optimization]]