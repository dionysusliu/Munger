>      natives”,   

# Congestion Control

Congestion control refers to the set of mechanisms used in computer networks (and other shared‑resource systems) to prevent or mitigate congestion—a state where the demand for network resources exceeds the available capacity. Effective congestion control helps maintain network stability, fairness, and performance by dynamically adjusting the rate at which data is sent.

## Definition

In networking, congestion control is the process of regulating data transmission to avoid overwhelming intermediate nodes (routers, switches) or the receiver. It is typically implemented in transport protocols such as [[TCP]], and involves algorithms that detect incipient congestion (e.g., through packet loss or delay) and throttle back the sending rate. Congestion control differs from [[Flow Control]], which prevents a fast sender from overwhelming a slow receiver.

## Examples

- **TCP Reno / AIMD (Additive Increase Multiplicative Decrease):**  
  The classic TCP congestion control algorithm. The sender increases its window (rate) by one packet per round‑trip time until a loss is detected, then halves the window. This ensures gradual probing and rapid back‑off.

- **TCP CUBIC:**  
  A more modern algorithm optimized for high‑bandwidth, long‑distance networks. It uses a cubic function for growth, allowing aggressive probing after a loss event while maintaining stability.

- **Explicit Congestion Notification (ECN):**  
  A router marks packets to signal impending congestion before actual packet loss occurs, allowing the sender to react proactively.

- **BBR (Bottleneck Bandwidth and Round‑trip propagation time):**  
  A model‑based algorithm that estimates the available bandwidth and round‑trip time to maintain a sending rate near the optimal point without causing queuing.

- **TCP Vegas:**  
  A delay‑based scheme that uses actual RTT measurements relative to a baseline to detect congestion before packet loss occurs.

## Related Mental Models

- **Tragedy of the Commons:**  
  In a shared network, if each sender maximises its own throughput without considering overall capacity, the network becomes congested and all senders suffer. Congestion control algorithms internalise this externality.

- **Feedback Loops (Negative Feedback):**  
  Congestion detection (e.g., packet loss, ECN) triggers a reduction in sending rate, which reduces queue load—a classic negative feedback system that stabilises the network.

- **Control Theory (e.g., PID Controllers):**  
  Modern congestion control algorithms borrow from control theory to balance responsiveness (fast reaction to congestion) and stability (avoiding oscillations).

- **Bucket Analogy (Leaky Bucket / Token Bucket):**  
  Often used to illustrate traffic shaping and rate limiting, which are complementary to congestion control.

- **Law of the Minimum:**  
  A network’s throughput is limited by the most constrained link (bottleneck). Congestion control aims to utilise that bottleneck without overdriving it.

- **Exponential Backoff:**  
  A resilience strategy used in [[Ethernet]] (CSMA/CD) and TCP retransmission timeouts; it mirrors the multiplicative decrease part of congestion control.

- **Bufferbloat:**  
  A mental model of the harm caused by excessive buffering in routers, which masks congestion signals and leads to high latency. Modern congestion control (e.g., BBR) explicitly addresses this.

## Related Pages

- [[TCP]]
- [[Network Congestion]]
- [[AIMD (Additive Increase Multiplicative Decrease)]]
- [[Flow Control]]
- [[Exponential Backoff]]
- [[Bufferbloat]]
- [[Quality of Service]]
- [[End-to-End Principle]]

> *See also:* [The Internet’s Congestion Control Problem](https://example.com) (external reference)