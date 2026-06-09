>     

# FCFS Gateways

## Definition

**FCFS Gateway** refers to a network router, switch, or any intermediary device that processes incoming packets strictly in the order they arrive — *First Come, First Served*. In this model, all packets are treated equally; no priority, classification, or resource reservation is applied. The gateway maintains a simple FIFO (First-In, First-Out) queue for all traffic passing through it.

FCFS is the simplest possible scheduling discipline for gateway operation. It is often used as a baseline against which more complex algorithms (e.g., weighted fair queuing, priority queuing) are compared.

## Characteristics

- **No prioritization** – Every packet is queued in arrival order regardless of source, destination, protocol, or packet size.
- **Low implementation overhead** – Only a single queue is needed; no per-flow state or sorting is required.
- **Head-of-line (HOL) blocking** – A large or bursty packet at the front of the queue delays all subsequent packets, even if they are small or urgent.
- **Fairness issues** – A single aggressive flow can starve others by filling the queue.
- **No protection against congestion collapse** – Under high load, all flows experience the same delay and packet loss.
- **Simple to model** – Often used as the default behavior when no explicit scheduling policy is configured.

## Examples

| Context | Scenario |
|---------|----------|
| **Home router** | An inexpensive consumer router with no Quality of Service (QoS) settings forwards packets in exact arrival order. A large file download can cause noticeable lag for a real‑time video call. |
| **Ethernet hub** (historical) | An old 10BASE‑T hub repeats frames onto every port in the order they are received – a pure FCFS gateway. |
| **Legacy WAN link** | A serial line without traffic shaping transmits packets in arrival order. VoIP packets get queued behind a large FTP file transfer. |
| **Operating system analogy** | A simple printer spooler that prints jobs in the order they are submitted (FCFS scheduling) shares the same principle. |

## Related Mental Models

- **[[FIFO Queue]]** – The fundamental data structure underlying FCFS gateways; packets enter at the tail and leave from the head.
- **[[Network Congestion]]** – FCFS gateways can exacerbate congestion because they lack mechanisms to differentiate flows.
- **[[Queueing Theory]]** – Mathematical models (e.g., M/M/1 queue) often assume FCFS service discipline for analytical tractability.
- **[[Fair Queuing]]** – A contrast to FCFS; it divides bandwidth among flows to prevent starvation.
- **[[Head‑of‑Line Blocking]]** – The dominant drawback of FCFS gateways, where one large packet delays the entire queue.
- **[[Best‑Effort Delivery]]** – The Internet’s original design principle that treats all packets equally – FCFS is a natural fit for this model.
- **[[Pareto Principle]]** – “80/20 rule” reveals that in a FCFS gateway, a small fraction of flows can consume most of the bandwidth, causing unfairness.

## When to Use (and When Not)

- **Use FCFS** when simplicity outweighs performance, traffic is homogeneous, or no application requires delay differentiation (e.g., isolated local network with only bulk file transfers).
- **Avoid FCFS** when real‑time traffic (VoIP, video conferencing, gaming) shares the link – the HOL blocking caused by one large download will degrade user experience.

## See Also

- [[Packet Scheduling]]
- [[Traffic Shaping]]
- [[Quality of Service (QoS)]]
- [[Bufferbloat]]
- [[Round‑Robin Scheduling]]