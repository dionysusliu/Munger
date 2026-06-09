# JK Flow Control

**JK flow control** is a congestion avoidance and rate control algorithm designed for packet-switched networks, particularly when combined with [[Fair Queuing (FQ)]] gateways. It originated from the *Jain–Kurose* collaboration and is often used in network simulations to dynamically adjust transmission rates based on real-time network feedback. As a mental model, JK flow control helps us think about **adaptive regulation** where a system continuously recalibrates its output in response to variable constraints and distributed feedback.

## Explanation

JK flow control operates by having each sender maintain a window size (the number of packets it can transmit without waiting for an acknowledgment). Unlike classic TCP Reno, which uses additive increase/multiplicative decrease (AIMD), JK flow control is designed to be **smoother and faster-reacting** when deployed with FQ gateways. The key idea is that the algorithm leverages the per-flow queuing isolation provided by FQ to avoid unnecessary backoffs and to converge more quickly to a fair and efficient rate.

### Core Mechanics

1. **Window-based control** – The sender adjusts a congestion window (cwnd) based on acknowledgment timing and loss signals.
2. **Gradient estimation** – JK uses a form of **delta-based** adjustment: it measures the change in round-trip time (RTT) or queue delay between successive packets.
3. **Binary feedback** – The algorithm interprets a single bit of congestion information (e.g., an ECN mark or a dropped packet) but does so in a way that accounts for the flow’s “weight” in a FQ scheduler.
4. **Fairness with FQ** – Because FQ gateways interleave packets from multiple flows fairly, JK can safely increase its window more aggressively when capacity is underutilized and decrease only minimally when the gateway signals mild congestion.

In essence, JK flow control models a **cooperative-adaptive system** where each agent (flow) trusts the network infrastructure (FQ) to provide clean, per-flow queue dynamics, and in return the agent adjusts its sending rate with a simple, linear rule.

## Examples

### Example 1: Simulating a congested link
In a network simulator (e.g., ns-3), two TCP flows share a 10 Mbps link with a Fair Queuing router. Using JK flow control, each flow’s window evolves as:

- When no packets are lost and RTT is stable: window increases by 1 per RTT (like TCP Reno).
- When a single packet is dropped (or ECN is set): window decreases by a small fraction (e.g., 0.125 * cwnd), much gentler than TCP Reno’s halving.
- Because FQ prevents one flow from starving the other, both flows converge to equal shares within a few round trips.

### Example 2: Web server rate limiter
A mental model application: an API rate limiter that uses “JK-like” logic – it measures average response time, and if latency rises above a threshold, it reduces the allowed requests per second by a small factor; if latency drops, it increases linearly. This mimics the smooth adaptation seen in JK flow control without hard cutoffs.

## Applications

- **Network simulation research** – JK is a benchmark for studying the interplay between end-to-end congestion control and router-based fair queuing.
- **Design of low-latency protocols** – The principles of JK (gentle decrease, confidence in FQ) inspired parts of DCTCP and other data-center TCP variants.
- **Traffic management in real-time systems** – Any system where multiple senders compete for a shared resource and receive per-flow isolation can benefit from a JK-like control loop (e.g., cloud storage QoS, video streaming adaptation).

## Related Mental Models

- [[AIMD (Additive Increase Multiplicative Decrease)]] – The classic counterpart; JK uses a *multiplicative decrease* but with a smaller factor.
- [[Echo Cancellation in feedback loops]] – How a sender can interpret delayed signals to avoid oscillation.
- [[Coordination in distributed systems]] – JK’s success depends on both sender and gateway cooperating, mirroring the broader need for aligned incentives.

## Limitations

- JK’s performance degrades significantly without Fair Queuing; on a drop-tail FIFO queue it behaves similarly to or worse than AIMD.
- The algorithm assumes reliable congestion signaling (e.g., ECN, or negligible non-congestion losses). In wireless networks with random loss, JK may misinterpret corruption as congestion.
- It is not designed for highly dynamic bandwidth scenarios (e.g., cellular handovers) where the reaction time may be too slow.

## Further Reading

- *Analysis of the Increase and Decrease Algorithms for Congestion Avoidance in Computer Networks* (Jain & Ramakrishnan, 1988) – Foundation for JK-inspired work.
- [[Flow Control (OSI layer 4)]] – Broader context of data rate management.
- [[Fair Queuing]] – Necessary companion for JK’s ideal behavior.

---

*This page is part of the wiki’s [[Mental Models]] collection.*