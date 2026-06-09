> -Concepts,         

## Fair Queueing Scheme

A **fair queueing scheme** is a resource allocation and scheduling algorithm designed to distribute a shared resource (e.g., CPU time, network bandwidth, disk I/O) among multiple competing entities (flows, processes, users) in a manner that guarantees each entity a **fair share** of the resource over time. It prevents any single entity from monopolizing the resource, even when others are idle, and ensures that no entity suffers from starvation.

The concept originated in [[Computer Networking]] (as **Fair Queuing**, or **Packet-by-Packet Fair Queuing**) but has broad applications in [[Operating Systems]], [[Economics]], and [[Queueing Theory]].

### Core Idea

Fair queueing treats each entity as a separate **logical queue**. The scheduler services all non-empty queues in a **round-robin** fashion, but with a crucial twist: it allocates resource units (bits, CPU cycles, tokens) in proportion to a weight assigned to each queue. In its simplest form, all queues have equal weight, so each gets an equal share.

The key mechanism is **bit-by-bit round robin** (or the equivalent fluid-flow model), where the scheduler simulates a hypothetical "fluid" system in which bits from all active flows are transmitted interleaved at the same rate. The actual packet scheduler then services packets in the order they would finish in this ideal fluid system. This approximates **max-min fairness**.

Mathematically, each queue \(i\) with weight \(w_i\) receives a service share \(\phi_i = w_i / \sum_j w_j\) of the resource.

### Characteristics

- **Fairness**: Over time, each flow receives exactly its weighted share, regardless of other flows' behavior.
- **Protection**: A misbehaving flow that sends at a high rate can only hurt itself (its own queue backlog grows) but cannot degrade the service of other flows beyond their fair share.
- **Work-conserving**: If one queue is empty, its share is redistributed among active queues (in some implementations).
- **Delay bound**: Fair queueing provides a bounded delay for each packet, which is crucial for [[Quality of Service]] (QoS).

### Examples

**1. Network Router (Fair Queuing)**
- Suppose a router has 1 Gbps link and three traffic flows: A, B, C. All have equal weight (1/3 each). Even if Flow A aggressively sends 800 Mbps, the scheduler will only allocate 333 Mbps to A. Flows B and C each get their guaranteed 333 Mbps. Excess packets from A are dropped or queued, but B and C are unaffected.

**2. CPU Scheduling (CFS – Completely Fair Scheduler)**
- The Linux [[Completely Fair Scheduler]] is a practical implementation of fair queueing for CPU time. It maintains a red-black tree of runnable processes, each with a "virtual runtime". The scheduler always picks the process with the smallest virtual runtime, ensuring that every process gets a proportional share of CPU cycles.

**3. Disk I/O Scheduling**
- In storage systems, a fair queueing scheme can be used to allocate disk bandwidth among virtual machines or containers. Each VM gets a guaranteed IOPS share, preventing a noisy neighbor from starving others.

### Applications

| Domain | Implementation | Purpose |
|--------|----------------|---------|
| [[Network Congestion Control]] | Weighted Fair Queuing (WFQ) | Provide delay guarantees and fairness in routers |
| [[Operating Systems]] | CFS, Fair Share Scheduling | Ensure each process gets CPU time according to priority/weight |
| [[Cloud Computing]] | Virtual CPU allocation (AWS, GCP) | Isolate tenants and enforce Service Level Agreements |
| [[Economics]] | Bankruptcy rules, Aumann-Shapley | Fair division of scarce resources among agents |
| [[Wireless Networks]] | Proportional Fair Scheduling | Balance throughput and fairness among users |

### Related Concepts

- [[Round Robin Scheduling]] – simpler, but not work-conserving in the same way and does not isolate misbehaving flows.
- [[Max-Min Fairness]] – the fairness criterion that fair queueing achieves.
- [[Leaky Bucket]] and [[Token Bucket]] – traffic shaping mechanisms often combined with fair queueing.
- [[Quality of Service]] – broader framework for network performance guarantees.
- [[Stochastic Fairness Queuing]] – a hash-based approximation for high-speed networks.

### Trade-offs

- **Implementation complexity**: Maintaining per-flow state and sorting packet finishing times requires more overhead than FIFO or simple round-robin.
- **Memory requirements**: Each active flow needs a separate buffer.
- **Handling of bursts**: Pure fair queueing may not handle short-term burstiness well without admission control.

### Further Reading

- Demers, A., Keshav, S., & Shenker, S. (1989). "Analysis and simulation of a fair queueing algorithm." *ACM SIGCOMM*.
- [[Pareto Principle]] – sometimes invoked in discussions of fairness vs. efficiency, though fair queueing prioritizes the latter.

---