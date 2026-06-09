# Linux kernel

## Definition
The **Linux kernel** is the foundational, reactive core of the Linux operating system that arbitrates access to hardware, manages system resources, and enforces execution boundaries between user-space applications and privileged system operations. Rather than a static collection of functions, it operates as a **context-aware, event-driven orchestrator** designed to respond to interrupts, system calls, and hardware signals with precise intent. Its architecture emphasizes separation of privilege, deterministic state transitions, and isolation of failure domains. Understanding the kernel requires shifting focus from implementation syntax to behavioral architecture: how it *responds*, *enforces*, *isolates*, and *serves* across competing workloads.

## Conceptual Examples
The following examples illustrate kernel behavior through operational patterns rather than code structures:

- **[[Virtual Memory Translation]]**: Maps contiguous user-space memory requests to fragmented physical RAM using page tables. The kernel doesn't allocate memory upfront; it reacts to page faults on-demand, swapping, caching, and reclaiming pages based on access patterns and pressure signals.
- **[[Process Scheduling & Time Slicing]]**: Treats CPU time as a shared, finite resource. The kernel continuously evaluates task priority, historical runtime, and I/O wait states to dynamically assign execution windows, ensuring fairness without guaranteeing real-time determinism.
- **[[Namespace Isolation & Cgroup Enforcement]]**: Partitions a single kernel instance into logically independent environments. The kernel intercepts resource requests, applies quotas, and masks system views, enabling containerization without duplicating core infrastructure.
- **[[Interrupt Splitting & Deferred Work]]**: Reacts immediately to hardware signals with minimal top-half handlers, then defers complex processing to bottom halves (`[[SoftIRQ]]`, `[[Tasklet]]`, `[[Workqueue]]`). This asymmetry preserves low-latency responsiveness while preventing CPU starvation.
- **[[System Call Gateway]]**: Acts as a controlled privilege boundary. Every user request is validated, sanitized, and executed in kernel context before returning results. The kernel never trusts user-space pointers, sizes, or state assumptions.

## Related Mental Models
To reason about the Linux kernel effectively, the following conceptual frameworks capture its underlying operational philosophy:

- **[[Context-Driven Execution]]**: Kernel behavior is strictly gated by execution context. In `[[Process Context]]`, blocking, sleeping, and dynamic allocation are permitted. In `[[Interrupt Context]]` or atomic sections, operations must be non-blocking and time-bounded. The kernel constantly evaluates *where* it runs before deciding *what* it can do.
- **[[Privilege & Space Separation]]**: The kernel enforces a hard boundary between untrusted user-space and trusted kernel-space. This isn't merely architectural; it's operational. Every cross-boundary transition involves mode switching, pointer validation, and capability checking to prevent privilege escalation.
- **[[Arbitration Over Participation]]**: The kernel functions as a referee, not a worker. It tracks, allocates, and reclaims resources (CPU, memory, I/O, network) according to policy and fairness rules, but never executes application logic. Applications request; the kernel grants, denies, or queues.
- **[[Deferred Asymmetry]]**: Immediate hardware events are handled minimally; heavier processing is pushed outward or downward. This split optimizes for two competing goals: preserving interrupt latency while maintaining system throughput through asynchronous work queues and user-space daemons.
- **[[State Machine Coordination]]**: Processes, memory regions, and devices are modeled as finite state machines. Transitions (`RUNNING` → `SLEEPING` → `ZOMBIE`, `ALLOCATED` → `EVICTED`, `IDLE` → `ACTIVE`) are event-driven. The kernel enforces invariant rules across all state changes, ensuring consistency even under concurrent pressure.

> *Note: This page reflects a behavioral and architectural lens. For implementation details, refer to [[Kernel Source Navigation]], [[Subsystem Architecture]], or [[Driver Development Model]].*