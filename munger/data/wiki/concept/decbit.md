# DECbit

**DECbit** (Digital Equipment Corporation's binary congestion notification) is a congestion control algorithm that uses an explicit congestion notification bit in network packet headers. When a router’s queue occupancy exceeds a predefined threshold, it sets the DECbit on the packet. The receiver echoes this bit back to the sender, which then reduces its transmission rate. DECbit was an early precursor to modern [[Explicit Congestion Notification (ECN)]] mechanisms.

## Overview

- **Type:** End-to-end congestion control with router assistance (explicit feedback).
- **Key Idea:** Routers mark packets when congestion is imminent; senders interpret marks and adjust their sending rate.
- **Congestion Signal:** A single bit in the packet header.
- **Router Action:** Monitor queue length. If average queue length exceeds a threshold (e.g., 1 packet), set the DECbit on the packet.
- **Sender Action:** On receiving acknowledgment with the DECbit set, the sender halves its congestion window. Otherwise, it increases the window by roughly one packet per round-trip time (AIMD — Additive Increase Multiplicative Decrease).

## How It Works

1. **Router side:**
   - Maintains a running average of queue occupancy (e.g., using an exponential weighted moving average).
   - Compares the average to a fixed threshold (often 1 packet).
   - If the average exceeds the threshold, the router sets the DECbit on the packet’s header.

2. **Receiver side:**
   - For each packet received, the receiver checks the DECbit.
   - The bit is echoed back in the next acknowledgment (ACK).

3. **Sender side:**
   - On each ACK arrival, the sender counts whether any DECbit was set in the previous window of packets.
   - If at least 50% of the packets in a window had the bit set, the sender reduces its congestion window by half (multiplicative decrease).
   - Otherwise, it increases the window by one packet per window (additive increase).

> DECbit uses a “window-based” detection: the sender tracks the fraction of marked packets over an entire window, not each individual ACK.

## Examples

- **High-speed network:** A router’s queue starts building due to a burst. The average queue length crosses the threshold. DECbits are set on outgoing packets. The sender, upon receiving the feedback, cuts its window in half, alleviating the queue.
- **Comparison to drop-tail:** Instead of waiting for buffer overflow and packet loss, DECbit signals congestion before drops occur, reducing retransmissions and improving goodput.

## Related Mental Models

- [[Explicit Congestion Notification (ECN)]] – Modern successor to DECbit, standardized in IP.
- [[Additive Increase Multiplicative Decrease (AIMD)]] – The core control law used by DECbit and TCP Reno.
- [[TCP Congestion Control]] – Later algorithms that use implicit congestion signals (packet loss) or explicit marks (ECN).
- [[Queue Management]] – DECbit is an early form of active queue management (AQM); see also [[Random Early Detection (RED)]].
- [[End-to-End Argument]] – Debates over where congestion control should be implemented; DECbit uses router hints but leaves final decision at the endpoints.

## Advantages and Limitations

| Pros | Cons |
|------|------|
| Early notification before packet loss | Requires all routers and hosts to support the DECbit field |
| Uses explicit feedback, reducing waste | Threshold-based marking can be slow to react to varying traffic |
| Simple to implement | Only a binary signal; may not capture degree of congestion |
| Basis for modern ECN | Not widely deployed; superseded by ECN in TCP/IP |

## See Also

- [[Random Early Detection (RED)]]
- [[AQM (Active Queue Management)]]
- [[TCP SACK]]
- [[Congestion Collapse]]

---

> *This page was originally created for a wiki on networking concepts and mental models.*