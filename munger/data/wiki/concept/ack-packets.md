# ACK packets

**ACK packets** (acknowledgment packets) are control packets used in reliable transport protocols (e.g., TCP) to confirm the successful receipt of data segments. They play a critical role in flow control, congestion avoidance, and maintaining throughput. The scheduling treatment of ACK packets can significantly impact network performance, especially when competing with data packets like those from FTP transfers.

## Definition

An ACK packet is a small (typically header-only) message sent by the receiver back to the sender to indicate that a specific sequence of data has been received without error. In TCP, ACKs are cumulative—they acknowledge all bytes up to a given sequence number. The sender uses ACKs to:
- Advance the sliding window
- Trigger the transmission of new data
- Detect packet loss (via duplicate ACKs or timeouts)

Because ACKs carry no payload, they are lightweight but essential for protocol correctness.

## The Problem: ACK Delay Under FCFS Scheduling

Under **First-Come-First-Served (FCFS)** scheduling (also known as FIFO queuing), packets are processed in the order they arrive. When an FTP data stream and its corresponding ACK stream share a bottleneck link, the following occurs:

- Large FTP data packets (often 1460 bytes or more) fill the queue.
- Small ACK packets (typically 40–60 bytes) arriving later must wait behind the large data packets.
- This **ACK compression** or **ACK delay** reduces the rate at which the sender receives feedback, slowing down the TCP congestion window increase and degrading throughput.

In FCFS queues, ACK packets have no priority, so they experience the same queuing delay as data packets—despite being much smaller and more time-sensitive for flow control.

## Fair Queuing (FQ) to the Rescue

**Fair Queuing (FQ)** gateways (and its variants like Weighted Fair Queuing, WFQ) maintain separate per-flow queues and schedule packets in a round‑robin fashion. This ensures that each flow gets a fair share of the link bandwidth. For ACK packets:

- FQ can isolate ACK flows from data flows, preventing ACKs from being queued behind large FTP packets.
- Many FQ implementations **give priority to ACK packets** (or small packets) by serving them first within each round, or by using a separate high‑priority queue for control packets.
- This reduces ACK delay, allowing TCP senders to receive timely feedback, increase their congestion window faster, and achieve higher throughput.

The result is improved flow control and better utilization of the network path.

## Related Mental Models

- **[[Flow Control]]** – ACKs directly implement flow control by telling the sender how much buffer space is available.
- **[[Congestion Control]]** – ACK arrival rate influences TCP’s congestion window (e.g., in AIMD).
- **[[Fairness]]** – FQ ensures that ACK flows are not starved by bulk data flows.
- **[[Self-Clocking]]** – TCP is said to be “self‑clocking” because ACKs pace the transmission of new data; delayed ACKs break this clock.
- **[[Bufferbloat]]** – Large buffers in FCFS queues exacerbate ACK delay, while FQ mitigates it.

## Examples

### Example 1: FTP over FCFS
- A 10 Mbps link with a FIFO queue.
- An FTP sender transmits 1500‑byte data packets at line rate.
- ACK packets arrive at the queue but must wait for 10–20 data packets ahead.
- The sender sees ACKs arriving in bursts (ACK compression), causing the congestion window to open slowly and then overshoot.

### Example 2: FTP over Fair Queuing
- Same link, but with an FQ gateway that maintains separate queues.
- The FTP data flow and its ACK flow each get their own queue.
- The scheduler serves one packet from each queue per round, or prioritizes the ACK queue.
- ACK packets are dequeued quickly, maintaining a steady ACK stream and stable throughput.

## Internal Wiki Links

- [[TCP Congestion Control]]
- [[FIFO vs Fair Queuing]]
- [[Bufferbloat]]
- [[Weighted Fair Queuing (WFQ)]]
- [[Self-Clocking in TCP]]

## Further Reading

- *“Acknowledgment Packets and Fair Queuing”* – Sally Floyd & Van Jacobson (1995)
- *“The Effect of Router Scheduling on TCP Performance”* – Keshav, S. (1993)
- IETF RFC 970 – *“On Packet Switches with Infinite Storage”* (early work on queueing disciplines)