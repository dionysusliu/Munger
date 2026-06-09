# Lock Contention

## Definition
**Lock contention** is a concurrency performance bottleneck that occurs when multiple threads or processes simultaneously attempt to acquire the same synchronization primitive (e.g., mutex, spinlock, read-write lock) to access a shared resource or enter a [[Critical Section]]. Because mutual exclusion guarantees only one thread can hold the lock at a time, competing threads are forced to wait, spin, or block. This serializes execution, increases latency, inflates context-switching overhead, and caps overall system throughput regardless of available hardware parallelism.

## How It Occurs
1. **Concurrent Execution**: Multiple threads run in parallel across CPU cores.
2. **Critical Section Entry**: Each thread reaches a code region protected by the same lock.
3. **Serialization**: The first thread acquires the lock and executes the sequential critical section.
4. **Queue Formation**: Remaining threads join a wait queue, spin in place, or yield to the scheduler.
5. **Overhead Accumulation**: Waiting threads generate cache coherence traffic, trigger context switches, and stall pipeline utilization, turning a theoretically parallel workload into a sequential bottleneck.

## Examples
- **Database Systems**: High-frequency `UPDATE` or `SELECT ... FOR UPDATE` operations on the same row/table cause transaction locks to serialize query execution.
- **Web/Application Servers**: Thread pools competing for a shared connection pool or global configuration lock under sustained traffic spikes.
- **Kernel Subsystems**: Historically, the Linux [[Big Kernel Lock]] (BKL) forced entire system calls to serialize, severely limiting multi-core scalability.
- **Research Implementations** (from sequential performance optimization frameworks):
  - `[[ShflLock]]` (SOSP'19): Reorders the waiting queue to prioritize threads closer to lock release, reducing wake-up latency.
  - `[[CNA]]` (EuroSys'19): Batches waiting threads to improve cache locality and amortize context-switch costs.
  - `[[SynCord]]` (OSDI'22): Applies dynamic, workload-aware scheduling policies to the lock wait queue for adaptive serialization.

## Optimization Methodologies
Modern systems research systematizes lock contention mitigation through targeted [[Serial Performance Optimization]] techniques:
- **Wait Queue Reordering**: Prioritize threads based on NUMA proximity, remaining critical section length, or historical fairness metrics.
- **Thread Batching**: Group contending threads to execute critical sections back-to-back, maximizing cache reuse and minimizing coherence invalidations.
- **Dynamic Policy Switching**: Adapt lock behavior at runtime (e.g., switching between spinning, yielding, or queue-based blocking) based on contention intensity.
- **Lock-Free/Wait-Free Alternatives**: Replace coarse-grained locks with atomic operations, RCU, or fine-grained partitioning where algorithmic correctness allows.
- **Critical Section Minimization**: Refactor code to shrink the sequential portion, directly addressing the root cause of serialization.

## Related Mental Models
- `[[Amdahl's Law]]`: Illustrates why optimizing the sequential (locked) portion yields diminishing but critical returns as parallelism increases.
- `[[Critical Section]]`: The fundamental code region protected by synchronization; its length directly dictates contention severity.
- `[[Queueing Theory]]`: Models lock wait times as a service queue; arrival rate vs. service rate determines saturation and tail latency.
- `[[Cache Locality]]`: Batching and reordering techniques exploit spatial/temporal locality to reduce memory subsystem bottlenecks during contention.
- `[[False Sharing]]`: A related concurrency pitfall where unrelated variables on the same cache line cause unnecessary coherence traffic, often mistaken for pure lock contention.
- `[[Serial Performance Optimization]]`: A broader framework emphasizing that sequential bottlenecks (including locks) must be systematically profiled and resolved before scaling parallelism.

## See Also
- `[[Mutex]]`
- `[[Spinlock]]`
- `[[Context Switching]]`
- `[[Cache Coherence]]`
- `[[Concurrency Control]]`
- `[[Performance Profiling]]`