>    limit      well-beh

# Flow Control Algorithms

**Flow control algorithms** are a set of techniques used in computer networks, operating systems, and distributed systems to manage the rate of data transmission between a sender and a receiver. Their primary goal is to prevent a fast sender from overwhelming a slower receiver or congesting a shared network, thereby ensuring reliable and efficient communication. These algorithms operate at various layers of the protocol stack (e.g., transport layer in TCP) and often involve feedback mechanisms where the receiver signals its capacity or congestion state to the sender.

## Definition

A flow control algorithm dictates **how much data** a sender can transmit before receiving an acknowledgment or permission from the receiver (or the network). The algorithm continuously adapts the transmission rate based on:

- **Receiver's buffer capacity** (available memory)
- **Network congestion** (packet loss, delays)
- **Processing speed** of the receiver

The core challenge is balancing **throughput** (maximising data delivery) with **fairness** (avoiding starvation of other flows) and **avoidance of buffer overflow**.

## Examples

### 1. Stop-and-Wait
- **How it works**: The sender transmits one packet and waits for an acknowledgment (ACK) before sending the next.
- **Pros**: Simple, minimal buffer requirements.
- **Cons**: Poor performance on high-latency links (low utilization).
- **Used in**: Simple protocols, serial lines.

### 2. Sliding Window
- **How it works**: The sender maintains a window of outstanding packets (up to a fixed size). It can send all packets in the window without waiting for individual ACKs. The window "slides" forward as ACKs arrive.
- **Variants**:
  - **Go-Back-N**: On packet loss, all subsequent packets are retransmitted.
  - **Selective Repeat**: Only lost packets are retransmitted.
- **Used in**: TCP (with congestion window as an extension).

### 3. TCP Flow Control (Advertising Window)
- The receiver advertises its available receive buffer size (rwnd). The sender limits its unacknowledged data to ≤ rwnd. Combined with congestion control (cwnd), the effective window is `min(cwnd, rwnd)`.
- **Self-clocking property**: Packets are released at the rate of returning ACKs.

### 4. Congestion Control Algorithms (Hybrid)
- **TCP Reno, Cubic, BBR**: These algorithms adjust the sending rate based on observed packet loss or delay. Although primarily for congestion control, they integrate with flow control to prevent receiver overload.

## Related Mental Models

| Mental Model | Description | Link |
|--------------|-------------|------|
| **Leaky Bucket** | Traffic shaping algorithm where packets are poured into a bucket and drained at a constant rate. Used to smooth bursts. | [[Leaky Bucket]] |
| **Token Bucket** | Allows bursts by accumulating tokens up to a limit. Each packet consumes tokens. Provides average rate limiting with burst allowance. | [[Token Bucket]] |
| **Sliding Window** | A general pattern for tracking the latest N events or time intervals. Applied in flow control as the sliding window protocol. | [[Sliding Window (General)]] |
| **PID Controller** | A control loop feedback mechanism that uses proportional, integral, derivative terms to maintain a setpoint. Some advanced congestion control (e.g., delay-based) mimics PID. | [[PID Controller]] |
| **Queueing Theory** | Mathematical study of waiting lines (queues). Flow control prevents buffer queues from overflowing or growing excessively. | [[Queueing Theory]] |
| **Network Congestion** | The condition when offered load exceeds available capacity. Flow control interacts with congestion avoidance. | [[Network Congestion]] |
| **Backpressure** | A signal sent from a congested node to upstream nodes to reduce flow, commonly used in data buses and network-on-chip. | [[Backpressure]] |

## Key Concepts

- **Flow control vs Congestion control**: Flow control prevents sender outrunning **receiver**; congestion control prevents sender outrunning **network**.
- **Window-based vs rate-based**: Window-based algorithms limit the amount of in-flight data; rate-based algorithms limit the bits per second (e.g., token bucket).
- **Feedback loop**: Most flow control algorithms are closed-loop – they use ACKs, timeouts, or explicit congestion notification (ECN) to adjust.
- **Fairness**: Algorithms like TCP ensure multiple flows share capacity fairly (see [[TCP Fairness]]).

## References

- Tanenbaum, A. S., & Wetherall, D. J. (2011). *Computer Networks*.
- Forouzan, B. A. (2007). *Data Communications and Networking*.
- Jacobson, V. (1988). *Congestion avoidance and control*.

---

*See also: [[ACK Clocking]], [[RTT Fairness]], [[Dynamic Window Adjustment]], [[Bufferbloat]].*