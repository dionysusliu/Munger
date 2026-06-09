# Fair Queueing

**Fair Queueing** is a network scheduling algorithm designed to allocate bandwidth and buffer space equitably among multiple data flows, preventing any single flow from monopolizing network resources. By isolating traffic into separate queues and servicing them in a round-robin fashion, it ensures that well-behaved flows are protected from aggressive or ill-behaved sources. The concept was originally introduced by H. Murray and later refined by researchers such as John Nagle, Sally Floyd, and Van Jacobson.

## Definition

Fair Queueing (FQ) operates at network routers or gateways to manage packet transmission order. Unlike traditional FIFO (First-In, First-Out) queuing, which can allow a single high-throughput flow to starve others, FQ maintains a separate queue for each active flow (defined by source-destination IP pair, port numbers, or other criteria). The scheduler then services these queues in a weighted round-robin or bit-by-bit fashion, approximating an ideal "fluid flow" model where each flow receives a fair share of the link capacity.

### Key Principles

- **Per-flow isolation**: Each flow has its own buffer, preventing one flow's burstiness from causing packet loss in others.
- **Fairness**: Bandwidth is distributed equally (or proportionally to weights) among active flows.
- **Low latency for low-throughput flows**: Interactive traffic (e.g., SSH, VoIP) experiences minimal delay even when bulk transfers (e.g., FTP) are active.
- **Protection against misbehavior**: Ill-behaved sources that send at excessive rates cannot degrade service for compliant flows.

## Examples

### Example 1: FTP vs. Interactive Traffic
Consider a 10 Mbps link shared by:
- **Flow A**: An FTP download with large TCP window size, sending at maximum rate.
- **Flow B**: An SSH session with small packets (e.g., 100 bytes) sent intermittently.

With FIFO queuing, Flow A’s packets fill the buffer, causing Flow B’s packets to wait behind large FTP packets, resulting in high latency for SSH. With Fair Queueing, Flow B’s queue is serviced frequently (e.g., round-robin), so its small packets are transmitted within milliseconds, while Flow A still gets its fair share of bandwidth.

### Example 2: Multiple Web Browsers
Ten users open web pages simultaneously. Each user’s HTTP requests generate short bursts of packets. In a FIFO queue, one user’s burst might delay others. Fair Queueing assigns each user a separate queue, ensuring that no single user’s burst causes packet loss or delay for the rest.

### Example 3: Weighted Fair Queueing (WFQ)
A video conferencing app (Flow X) and a file download (Flow Y) share a 1 Gbps link. WFQ assigns a weight of 3 to Flow X and 1 to Flow Y, guaranteeing Flow X receives 750 Mbps (75%) and Flow Y gets 250 Mbps (25%), even if Flow Y tries to send faster.

## Related Mental Models

- [[Network Congestion Control]] – Fair Queueing complements congestion control algorithms (e.g., TCP Reno) by preventing bufferbloat and ensuring fair bandwidth distribution.
- [[Leaky Bucket Algorithm]] – Similar to Fair Queueing in traffic shaping, but focuses on smoothing bursts rather than per-flow fairness.
- [[Round-Robin Scheduling]] – The core mechanism behind Fair Queueing; also used in operating systems for CPU scheduling.
- [[Bufferbloat]] – A problem Fair Queueing helps mitigate by limiting buffer occupancy per flow, reducing excessive latency.
- [[Quality of Service (QoS)]] – Fair Queueing is a fundamental QoS technique for guaranteeing service levels in packet-switched networks.
- [[Pareto Efficiency]] – Fair Queueing aims for a Pareto-optimal allocation where no flow can improve without harming another.
- [[Token Bucket Algorithm]] – Often used alongside Fair Queueing for traffic policing and shaping.

## Implementation Considerations

- **State overhead**: Per-flow queuing requires memory and processing to maintain queues and track active flows. Modern routers use hash tables or flow caches to manage this efficiently.
- **Flow classification**: Flows are typically identified by 5-tuple (source/destination IP, ports, protocol). In encrypted traffic, deep packet inspection may be needed.
- **Weighted variants**: [[Weighted Fair Queueing (WFQ)]] and [[Class-Based Weighted Fair Queueing (CBWFQ)]] allow administrators to assign different weights to flows or traffic classes.
- **Hardware acceleration**: High-speed routers implement Fair Queueing in ASICs or FPGAs to keep up with line rates.

## Limitations

- **Scalability**: Maintaining per-flow state becomes challenging with millions of concurrent flows (e.g., in core internet routers).
- **Computational cost**: Bit-by-bit approximation algorithms (e.g., [[Deficit Round Robin]]) are used to reduce overhead.
- **Fairness definition**: "Fair" may mean equal bandwidth, equal delay, or proportional allocation depending on context—leading to different implementations like [[Proportional Fair Scheduling]].

## See Also

- [[Active Queue Management]] (AQM) – Often combined with Fair Queueing to drop packets proactively (e.g., [[CoDel]], [[RED]]).
- [[Stochastic Fairness Queueing]] (SFQ) – A hash-based variant that reduces state requirements.
- [[Flow Queuing vs. Class Queuing]] – Trade-offs between per-flow granularity and aggregated traffic classes.