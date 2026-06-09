# Xiang Cheng

**Xiang Cheng** is a computer systems researcher affiliated with the [[Georgia Institute of Technology]]. Their work focuses on performance optimization, methodology systematization, and empirical analysis of systems research trends.

## Overview
Cheng's research addresses foundational challenges in the [[Computer Systems]] community, particularly the optimization of serial execution paths in increasingly parallelized software stacks. By conducting large-scale literature analyses and distilling practical optimization frameworks, Cheng contributes to bridging the gap between theoretical performance models and real-world systems engineering.

## Research Interests
* [[Performance Optimization]] in operating systems and distributed systems
* Systematization of software engineering methodologies
* Sequential vs. parallel execution analysis
* Bottleneck identification and resolution (e.g., [[Lock Contention]], synchronization overhead)
* Meta-analysis of systems research literature

## Notable Work
### Principles and Methodologies for Serial Performance Optimization
Co-authored with Sujin Park, Mingyu Guan, and [[Taesoo Kim]], this research presents a comprehensive meta-analysis of how sequential performance bottlenecks are identified and resolved in practice. Key contributions and findings include:

* **Scope & Methodology:** Systematically reviewed 477 papers from premier systems conferences ([[OSDI]] and [[SOSP]]) published over a ten-year period.
* **Core Objective:** Addressed the meta-question: *"Can we systematize how sequential performance is optimized in practice?"*
* **Key Insights:**
  * Performance optimization remains a dominant research theme, representing approximately 43% of OSDI/SOSP publications over the past decade.
  * Distilled a unified, recurring framework of optimization methodologies, positioning the work as a practical guide for solving diverse performance problems rather than a single-system solution.
  * Demonstrated that while parallelism improves throughput, overall speedup is fundamentally constrained by sequential code segments, reinforcing principles aligned with [[Amdahl's Law]].
  * Provided actionable diagnostic and resolution strategies for common serial bottlenecks, using [[Lock Contention]] as a primary case study for profiling-driven optimization.

## Academic Affiliation & Collaborators
* **Institution:** [[Georgia Institute of Technology]]
* **Department:** School of Computer Science
* **Primary Collaborators:** 
  * Sujin Park
  * Mingyu Guan
  * [[Taesoo Kim]]

## References & Further Reading
* Park, S., Guan, M., Cheng, X., & Kim, T. *Principles and Methodologies for Serial Performance Optimization*. [[Georgia Institute of Technology]].
* Related Venues: [[OSDI]], [[SOSP]]
* External Resources: [Georgia Tech College of Computing](https://www.cc.gatech.edu/)

---
*{{stub}}*