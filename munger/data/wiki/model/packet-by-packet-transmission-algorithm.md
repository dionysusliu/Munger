# Packet-by-Packet Transmission Algorithm (PGPS / Weighted Fair Queuing)

## Overview

The **packet-by-packet transmission algorithm** is a scheduling discipline for network routers and switches that emulates the behavior of an idealized **bit-by-bit round-robin** (also known as **Generalized Processor Sharing** or GPS) system. It operates by selecting the next packet to transmit based on the smallest value of a computed quantity \( F_i^a \), the **finish number** or **virtual finish time** of packet \( a \) in flow \( i \).

This algorithm is the foundation of **Weighted Fair Queuing (WFQ)** and **Packet-by-Packet Generalized Processor Sharing (PGPS)**.

## Core Concept

In an ideal **bit-by-bit round-robin** system, the server services all active flows simultaneously, transmitting one bit from each flow in a round. This provides perfect fairness and isolation between flows. However, networks transmit discrete **packets**, not bits. The packet-by-packet algorithm approximates the GPS ideal by:

1. Assigning each arriving packet a **virtual finish time** \( F_i^a \), which is the time at which the packet would complete service in the ideal GPS system.
2. When the server becomes free, selecting the packet with the **smallest** \( F_i^a \) for transmission.

## Mathematical Definition

For a packet \( a \) belonging to flow \( i \):

\[
F_i^a = \max(R(t), F_i^{a-1}) + \frac{L_i^a}{r_i}
\]

Where:
- \( R(t) \) = **virtual time** at arrival time \( t \) (the current round number in the GPS system)
- \( F_i^{a-1} \) = finish number of the previous packet from flow \( i \)
- \( L_i^a \) = length (in bits) of the current packet
- \( r_i \) = service rate allocated to flow \( i \) (proportional to its weight)

The packet with the **minimum** \( F_i^a \) among all pending packets is transmitted next.

## Key Properties

- **Fairness**: Emulates GPS closely, providing weighted fair allocation of bandwidth.
- **Bounded delay**: Provides delay guarantees for leaky-bucket constrained flows.
- **Work-conserving**: Never idles when packets are queued.
- **Complexity**: Requires \( O(\log N) \) operations per packet (using a priority queue), where \( N \) is the number of active flows.

## Example

Consider two flows, Flow A (weight 1) and Flow B (weight 2), with link speed 1 Mbps.

**Packet arrivals:**
- Flow A: Packet A1 (500 bits) at t=0
- Flow B: Packet B1 (1000 bits) at t=0, Packet B2 (500 bits) at t=0.5ms

**Virtual time computation** (simplified):
- At t=0: Both flows active. Virtual time \( R(t) = 0 \).
  - A1: \( F = \max(0,0) + 500/1 = 500 \)
  - B1: \( F = \max(0,0) + 1000/2 = 500 \)
- Tie broken arbitrarily (e.g., by flow ID). Suppose A1 sent first.

**Transmission order:**
1. A1 (500 bits) → completes at t=0.5ms
2. B1 (1000 bits) → completes at t=1.5ms
3. B2 (500 bits) → arrives during B1's transmission; \( F = \max(R(0.5), 500) + 500/2 = 500 + 250 = 750 \) → sent after B1

This approximates the GPS ideal where B would receive twice the service of A over time.

## Applications

- **[[Weighted Fair Queuing (WFQ)]]** – The most common implementation in routers (e.g., Cisco, Juniper).
- **[[Class-Based Weighted Fair Queuing (CBWFQ)]]** – Groups traffic into classes.
- **[[Guaranteed Service]]** in [[Integrated Services (IntServ)]] architecture.
- **[[DiffServ]]** with assured forwarding PHB.
- **Packet scheduling** in [[ATM Networks]] (per-VC queuing).
- **Wireless scheduling** (e.g., Channel-Aware WFQ).

## Related Concepts

- [[Generalized Processor Sharing (GPS)]]
- [[Virtual Clock Scheduling]]
- [[Deficit Round Robin (DRR)]]
- [[Leaky Bucket Traffic Shaper]]
- [[Quality of Service (QoS)]]

## Limitations

- **Computational overhead**: Maintaining virtual time and sorting packets can be expensive at high speeds.
- **Timestamp wrap-around**: Large finish numbers can overflow in hardware implementations.
- **Not perfectly fair with variable packet sizes**: The approximation of GPS is exact only in the limit of infinitesimally small packets.

## Further Reading

- Parekh & Gallager, "A generalized processor sharing approach to flow control in integrated services networks" (1993)
- Demers, Keshav, & Shenker, "Analysis and simulation of a fair queueing algorithm" (1989)