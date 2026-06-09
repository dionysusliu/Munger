# Scenario 2: Overloaded Gateway with Mixed FTP and Telnet Sources

**Scenario 2** is a classic networking example used to illustrate the effects of buffer saturation and queue management under mixed traffic conditions. The scenario involves a gateway with a fixed buffer size of **15 packets** receiving traffic from **6 FTP sources** (bulk, large transfers) and **2 Telnet sources** (interactive, small packets). The gateway is **overloaded**, meaning the total incoming rate exceeds the outgoing link capacity, causing packets to queue and eventually drop.

## Definition

In a network gateway where multiple sources compete for a limited buffer and link bandwidth, Scenario 2 models a situation with:

- **6 FTP flows**: Each sending large, continuous data streams (e.g., file transfers). These flows are greedy and fill the buffer aggressively.
- **2 Telnet flows**: Generating small, interactive packets (e.g., remote shell keystrokes). These flows are delay-sensitive but low-bandwidth.
- **Buffer size**: 15 packets (not bytes) – a very small queue relative to the number of sources.
- **Overload condition**: The aggregate input rate exceeds the output rate, causing sustained queuing and eventual packet drops.

The core problem is that the FTP flows, being large and persistent, can easily overwhelm the buffer, causing Telnet packets to be dropped or delayed unacceptably, degrading the interactive user experience.

## Example

Assume all sources send packets of equal size for simplicity, and the gateway uses a simple **FIFO (first-in-first-out)** queue with **tail drop** (dropping new packets when buffer is full). The buffer holds at most 15 packets.

- The 6 FTP sources each transmit at high rate, filling the queue rapidly.
- The 2 Telnet sources send occasional small packets (e.g., 1 packet every few seconds).
- Once the buffer is full, any arriving packet is dropped – but because FTP packets arrive much more frequently, Telnet packets are disproportionately dropped.
- Even when a Telnet packet is accepted, it may sit behind many FTP packets in the queue, causing high latency (bufferbloat). A typical Telnet round-trip time might increase from milliseconds to seconds.

**Outcome**: The gateway becomes virtually unusable for interactive traffic, while FTP flows continue to transmit (though with reduced throughput due to drops). This illustrates the **fairness problem** of tail-drop queues.

## Related Mental Models

### 1. [[Bufferbloat]]
The large standing queue (even if small in absolute terms, relative to interactive traffic) causes excessive latency. Scenario 2 is a textbook example of bufferbloat in miniature.

### 2. [[Drop-Tail vs Active Queue Management]]
The tail-drop behaviour in Scenario 2 leads to **lockout** and **full-queue syndrome**. Contrast with [[Random Early Detection (RED)]] or [[Fair Queuing (FQ)]] which would drop FTP packets earlier to give Telnet a chance.

### 3. [[TCP Global Synchronization]]
If FTP sources use TCP, the drops cause all TCP flows to reduce window simultaneously, leading to sawtooth throughput. This synchronization can be avoided with RED.

### 4. [[Fairness vs Efficiency]]
The scenario demonstrates a trade-off: FTP flows achieve high throughput (efficiency) but starve Telnet (unfairness). A fair queueing discipline would allocate buffer and link bandwidth equally per flow (or per protocol class).

### 5. [[Priority Queuing]]
One solution is to give Telnet packets higher priority (e.g., using a separate queue with lower drop probability). However, this can cause starvation of FTP if not policed.

## Practical Relevance

- **Network configuration**: Administrators must choose queue disciplines (e.g., WFQ, CBQ, fq_codel) to protect interactive traffic.
- **Buffer sizing**: The small buffer (15 packets) amplifies the problem. In legacy routers, large buffers (e.g., 1000 packets) would hide this effect but introduce bufferbloat. The optimal buffer size is a design trade-off.
- **Protocol dynamics**: Telnet over TCP is especially sensitive to delay and drops, while FTP (or HTTP bulk transfers) can tolerate them.

## See Also

- [[Overloaded Gateway Scenario 1]]
- [[Buffer Management in Routers]]
- [[Quality of Service (QoS)]]
- [[Flow Isolation]]

---

*This page is part of a wiki on networking scenarios and mental models. Interpret the buffer size "15" as a didactic simplification; real buffers are measured in kilobytes or packets but the lesson scales.*