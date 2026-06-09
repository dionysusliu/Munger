# FQ Gateways (Fair Queueing Gateways)

## Overview

FQ Gateways (Fair Queueing gateways) are network traffic management systems that use fair queueing algorithms to allocate bandwidth equitably across active network flows. Unlike traditional FIFO (First-In-First-Out) gateways, FQ gateways actively prevent any single flow from monopolizing network resources, effectively acting as **firewalls against ill-behaved traffic sources**.

This concept was notably explored in [[Network Fairness]] research and extended by [[Stochastic Fair Queueing]] (SFQ) implementations.

## Core Mechanism

FQ gateways operate by:

1. **Per-flow buffering** – Maintaining separate queues for each active traffic flow
2. **Round-robin scheduling** – Cycling through queues to give each flow equal transmission opportunities
3. **Drop policy enforcement** – Applying packet drops to flows that exceed fair share thresholds

## Key Benefits

### 1. Protection Against Ill-Behaved Sources
- Prevents aggressive flows (e.g., UDP floods, greedy TCP streams) from starving well-behaved flows
- Acts as a distributed [[Active Queue Management]] system

### 2. FTP Performance Improvement
- Reduces TCP global synchronization effects
- Allows multiple FTP connections to share bandwidth more predictably
- Minimizes bufferbloat for bulk data transfers

### 3. Telnet Performance Enhancement  
- Dramatically reduces latency variance for interactive sessions
- Prevents bulk transfers from overwhelming interactive keystroke echo traffic
- Maintains responsive [[Interactive Traffic]] even under heavy network load

## How It Works (Simplified)

```
Incoming packets ─→ Flow Classifier ─→ Queue 1 ─→ Scheduler ─→ Output
                                       Queue 2 ─→ (Round-robin)
                                       Queue 3 ─→
                                       Queue N ─→
```

## Comparison with FIFO Gateways

| Aspect | FIFO Gateway | FQ Gateway |
|--------|-------------|------------|
| Bandwidth allocation | Best-effort, first-come-first-served | Fair share per flow |
| Protection from aggressive flows | Minimal | Strong |
| Latency for interactive traffic | Degraded under load | Maintained |
| Implementation complexity | Low | Moderate |

## Examples

### Example 1: Telnet During FTP Download
- **Without FQ**: Telnet key echoes suffer seconds of delay while FTP buffers dominate the link
- **With FQ**: Telnet flow gets its fair share → sub-100ms keystroke echo latency maintained

### Example 2: Multiple FTP Sessions
- **Without FQ**: One aggressive TCP flow captures 80% of bandwidth
- **With FQ**: Each of 5 FTP flows gets ~20% bandwidth with bounded jitter

## Practical Applications

1. **[[Edge Router]] deployment** – Protecting customer traffic at ISP borders
2. **Cloud infrastructure** – Isolating noisy tenant VMs from well-behaved ones
3. **Real-time communications** – Ensuring VoIP/video conferencing quality alongside data transfers
4. **IoT gateways** – Preventing one sensor flood from blocking other devices

## Limitations

- **Scalability**: Per-flow state becomes expensive at high link speeds
- **Computational overhead**: Classification and queue management consume CPU cycles
- **Flow identification**: Deep packet inspection needed for encrypted VPN traffic
- **Fairness definition**: What constitutes a "flow" can be ambiguous (source-destination pair? application? user?)

## Related Concepts

- [[Stochastic Fair Queueing]] (SFQ) – Reduces state by hashing flows into buckets
- [[Deficit Round Robin]] – Handles variable-length packets fairly
- [[Class-Based Queueing]] – Extends fairness to traffic classes
- [[Bufferbloat]] – Problem that FQ helps mitigate
- [[CoDel AQM]] – Often paired with FQ for drop decisions

## Implementation Tools

- Linux `tc` (traffic control) with `sfq` or `fq_codel` qdiscs
- Cisco `fair-queue` feature on serial interfaces
- Juniper per-flow queueing with firewall filters
- OpenWrt SQM (Smart Queue Management) for [[Home Router Fairness]]

## Further Reading

- "A Fair Queueing Gateway for Internet Services" (original research)
- "Bufferbloat: Dark Buffers in the Internet" by Gettys & Nichols
- [[DiffServ Architecture]] as an alternative QoS approach

---

> **Key Insight**: An FQ gateway doesn't just increase throughput—it reshapes the quality of experience for all users by ensuring that no single misbehaving flow can degrade interactive applications.