# First-Come, First-Served (FCFS) Gateway

## Overview

The **First-Come, First-Served (FCFS) Gateway** is a fundamental queueing discipline used in network routers and switches, where packets are processed strictly in the order they arrive. Also known as FIFO (First-In, First-Out), this is the simplest and most intuitive scheduling algorithm. However, its lack of flow differentiation can lead to significant fairness issues in congested networks.

## Core Concept

In an FCFS gateway:
- All incoming packets are placed into a single queue
- The router processes packets from the head of the queue in arrival order
- No distinction is made between different traffic flows, applications, or users
- A single packet's delay affects all subsequent packets regardless of their source

## Mathematical Model

The FCFS gateway behavior can be modeled as an **M/M/1 queue** in simple cases:
- **Arrival rate**: λ (packets per second)
- **Service rate**: μ (packets per second)
- **Average queue length**: L = λ / (μ - λ)
- **Average waiting time**: W = 1 / (μ - λ)

## Advantages

1. **Simplicity**: Easy to implement in hardware with minimal overhead
2. **Deterministic**: Packet order is preserved (important for TCP)
3. **Low computational cost**: O(1) enqueue/dequeue operations
4. **Fair in short term**: First to arrive gets served first

## Disadvantages

1. **Unfair bandwidth allocation**: A single aggressive flow can consume most of the bandwidth
2. **No QoS support**: Cannot prioritize critical traffic (e.g., VoIP over file downloads)
3. **Global synchronization**: Can cause TCP global synchronization in congestion avoidance
4. **Vulnerability to malicious flows**: Easy target for [[Denial of Service (DoS) Attacks]]

## Examples

### Example 1: Web Server Under Load
```
Traffic mix:
- Flow A: 10 large file downloads (1 MB each)
- Flow B: 100 small web page requests (10 KB each)

Under FCFS: Flow A's first packet arrives first → all large packets served first
→ Flow B users experience high latency despite small requests
→ Flow B's throughput is severely degraded
```

### Example 2: Video Conferencing vs. File Transfer
```
- Flow C: Real-time video call (requires low latency, <150ms)
- Flow D: Background file download

FCFS behavior:
- If Flow D packets arrive first, they fill the queue
- Flow C packets must wait behind all Flow D packets
- Video call experiences jitter and packet loss
- Application: [[Real-Time Communication]] quality degrades
```

## Comparison with Fair Queuing

| Feature | FCFS Gateway | [[Fair Queuing (FQ) Gateway]] |
|---------|--------------|-------------------------------|
| Queue structure | Single global queue | Per-flow queues |
| Bandwidth allocation | First-come, first-served | Equal sharing among active flows |
| Implementation complexity | Low | Moderate to high |
| Protection from aggressive flows | None | Strong |
| QoS support | None | Yes (via weighted variants) |

## Applications Where FCFS is Acceptable

1. **Low-traffic networks** where congestion is rare
2. **Legacy systems** with simple hardware constraints
3. **Single-flow environments** (e.g., dedicated point-to-point links)
4. **Non-critical traffic** where latency doesn't matter

## Common Mitigation Strategies

When FCFS is used but fairness is needed, consider:

1. **Traffic shaping** at the ingress to limit aggressive flows
2. **[[Random Early Detection (RED)]]** to prevent global synchronization
3. **Priority queues** as a hybrid approach (e.g., strict priority + FCFS per class)
4. **Rate limiting** per source IP or application

## Related Concepts

- [[Packet Scheduling]] - Overview of scheduling disciplines
- [[Queueing Theory]] - Mathematical foundations
- [[Quality of Service (QoS)]] - Service differentiation mechanisms
- [[Head-of-Line Blocking]] - A key problem in FCFS systems
- [[Weighted Fair Queuing (WFQ)]] - Advanced scheduling for QoS

## See Also

- [[Network Congestion]]
- [[TCP Global Synchronization]]
- [[Bufferbloat]]
- [[Active Queue Management (AQM)]]