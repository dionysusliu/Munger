> tion,         April
source

# Sliding Window Flow Control

## Definition

**Sliding Window Flow Control** is a protocol mechanism used in data communications and networking to manage the rate of data transmission between two entities, ensuring that a sender does not overwhelm a receiver with more data than the receiver can process. The concept derives its name from the "window"—a contiguous range of sequence numbers that represents the frames or packets the sender is allowed to transmit before waiting for an acknowledgment.

The window "slides" forward as acknowledgments are received, allowing new data to be sent. This technique balances throughput and reliability, preventing congestion while maximizing bandwidth utilization.

## Key Principles

- **Windowing**: The sender maintains a window of outstanding, unacknowledged packets.
- **Acknowledgments (ACKs)**: The receiver sends ACKs for successfully received packets, which advance the window.
- **Flow Control**: The receiver can advertise a window size (often via the TCP header’s "Window Size" field) to limit how much data the sender can have in flight.
- **Sequencing**: Each packet is assigned a sequence number to enable ordering, retransmission, and duplicate detection.

## Examples

### 1. TCP (Transmission Control Protocol)
TCP uses a sliding window mechanism for both flow control and congestion control. The receiver specifies a *receive window* (`rwnd`), and the sender tracks a *congestion window* (`cwnd`). The effective window is the minimum of these two.

**Example Flow:**
- Sender is allowed to send up to 4 packets (window = 4).
- Sender sends packets 1, 2, 3, 4.
- Receiver ACKs packet 1 and 2, advertising `rwnd = 4` again.
- The window slides: sender can now send packets 5, 6, and optionally fill the slot where packet 1 and 2 were.

### 2. Go-Back-N ARQ
In this automatic repeat request protocol, the sender can transmit up to `N` packets without acknowledgment. If a packet is lost, the sender retransmits all packets starting from the lost one (the window "rolls back").

### 3. Selective Repeat
A more efficient variant where only the missing or erroneous packets are retransmitted, while correctly received out-of-order packets are buffered. The window here advances individually per packet, not as a block.

## Related Mental Models

- [[Leaky Bucket Algorithm]] — A traffic shaping model that smooths bursty traffic; complementary to sliding window for rate control but less adaptive.
- [[Token Bucket]] — Allows bursts up to a certain size, akin to a window that accumulates "tokens" over time; used in conjunction with sliding window in modern congestion control (e.g., TCP BBR).
- [[Congestion Control]] — Sliding window is the core mechanism; models like [[AIMD (Additive Increase Multiplicative Decrease)]] govern how the window size changes.
- [[Bufferbloat]] — A problem where excessively large buffers defeat sliding window flow control, leading to high latency.
- [[Stop-and-Wait Protocol]] — The simplest flow control model (window size = 1); sliding window generalizes this to allow pipelining.

## Use Cases

- All modern internet communication (TCP, SCTP, QUIC)
- Data link layer protocols (HDLC, PPP)
- Reliable streaming and file transfer protocols
- Network simulation and performance analysis

## Advantages vs. Disadvantages

| Advantages | Disadvantages |
|-----------|---------------|
| High throughput through pipelining | Complexity in implementation |
| Adaptive to network conditions | Overhead from sequence numbers and ACKs |
| Prevents receiver overload | Not ideal for highly lossy links without adaptation |
| Supports out-of-order delivery (Selective Repeat) | Can lead to head-of-line blocking |

## See Also

- [[Flow Control (General Model)]]
- [[Acknowledgments (ACK/NACK)]]
- [[TCP Reno vs. TCP Cubic]]
- [[Round-Trip Time (RTT)]]
- [[Self-Clocking (ACK-clocking)]]