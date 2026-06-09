## Scenario 5

**Scenario 5** is a standard simulation testbed for evaluating **flow control** and **queueing algorithms** in a multihop path network. It typically comprises four FTP (File Transfer Protocol) sources transmitting data through multiple intermediate nodes over distinct routes, enabling systematic analysis of traffic management and congestion control mechanisms under controlled, reproducible conditions.

### Definition

Scenario 5 is a network topology and traffic pattern used in discrete‑event simulators (e.g., ns‑2, ns‑3, OMNeT++) to benchmark the performance of:

- **Flow control algorithms** (e.g., TCP variants such as Reno, NewReno, Vegas, CUBIC)
- **Queueing disciplines** (e.g., DropTail, RED, CoDel, FQ_CoDel)
- **Active queue management (AQM)** and **explicit congestion notification (ECN)** schemes
- **Router buffer sizing** and **bottleneck link behavior**

The scenario isolates the effects of multihop forwarding, route diversity, and competing long‑lived flows on end‑to‑end throughput, latency, and fairness.

### Characteristics

- **Topology**: A multihop network with four distinct source‑to‑destination paths. Each path shares a common bottleneck link (or a set of shared links) to create contention.
- **Traffic**: Four FTP sources generating bulk data transfer (typically TCP Reno or a configurable variant). Each source sends to a unique sink along its own route.
- **Simulation parameters**: Common settings include link bandwidths (e.g., 1–10 Mbps), propagation delays (e.g., 10–50 ms), queue sizes (e.g., 20–100 packets), and simulation duration (e.g., 100–500 seconds).
- **Metrics measured**: Throughput per flow, packet loss rate, queue occupancy, round‑trip time (RTT) variation, fairness index (Jain’s), and utilization of the bottleneck link.

### Example

A concrete instance of Scenario 5 in ns‑3 might be:

```
Node topology:
  S1 ── R1 ── R2 ── D1
  S2 ── R1 ── R2 ── D2
  S3 ── R1 ── R2 ── D3
  S4 ── R1 ── R2 ── D4

  Links: Sx→R1 = 10 Mbps, 5 ms
         R1→R2 = 5 Mbps, 10 ms (bottleneck)
         R2→Dx = 10 Mbps, 5 ms

  Queue at R1 (outgoing to R2): DropTail, 50 packets
  Transport: TCP Reno (sink acknowledges every segment)
  Application: FTP, continuous send from t=0 to t=100 s
```

In this setup, all four flows converge at the bottleneck link between R1 and R2. The simulation tests how different queueing disciplines (e.g., RED vs. DropTail) affect TCP’s congestion window evolution, packet marking/dropping, and overall fairness.

### Related Mental Models

- [[TCP Congestion Control]] – The end‑to‑end mechanism that reacts to packet loss or ECN marks triggered by queueing algorithms.
- [[Queueing Discipline]] – The active buffer management policy at routers (DropTail, RED, CoDel, etc.) that determines how packets are enqueued and dropped.
- [[Bottleneck Link]] – The constrained link (e.g., R1→R2 in the example) that limits aggregate throughput and induces queue buildup.
- [[Flow Control]] – The per‑connection regulation of sender rate based on receiver feedback (e.g., TCP’s window‑based flow control).
- [[Multihop Network]] – A network where data traverses multiple intermediate nodes, introducing cumulative delay and potential for interference.
- [[Fairness Index]] – A metric (e.g., Jain’s index) used to quantify how equally bandwidth is shared among competing flows.
- [[Simulation Methodology]] – Best practices for designing and interpreting network simulations, including Scenario 5 as a canonical test case.

### Usage Notes

Scenario 5 is often paired with other standard topologies (e.g., the “dumbbell” or “parking lot”) to create a suite of benchmarks. It is particularly useful for:

- Comparing TCP variants under identical queueing conditions.
- Evaluating AQM algorithms in a multihop context.
- Studying the interaction between flow control and buffer sizing at intermediate routers.

When reporting results, it is essential to specify all simulation parameters (e.g., buffer size, RTT, bottleneck bandwidth) to ensure reproducibility.