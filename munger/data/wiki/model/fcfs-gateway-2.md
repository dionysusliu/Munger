> ongestion con

Here is a wiki page for the **FCFS (First-Come, First-Served) Gateway** model.

---

### Title: FCFS Gateway (Congestion Control)

**FCFS Gateway** is a [[Network Congestion]] management model where a network router or gateway processes incoming packets strictly in the order they arrive, regardless of priority, packet size, or destination. This is a foundational algorithm in [[Queueing Theory]] and [[Scheduling Algorithms]].

While simple, it is often the baseline for understanding [[Congestion Collapse]] and the need for more complex [[Active Queue Management]] (AQM) algorithms like [[RED]] or [[CoDel]].

> **Essence:** The "Line at the DMV" model of data transmission.

---

### Explanation

In the FCFS Gateway model:
1.  **Arrival:** Packets arrive at the gateway's input buffer (the "queue").
2.  **Queuing:** They are placed at the **tail** of the queue.
3.  **Service:** The gateway processes packets **only from the head** of the queue.
4.  **Scheduling:** No packet skips the line. A high-priority packet arriving after a low-priority packet will wait.

This is often combined with [[Tail Drop]]: when the buffer is full, any newly arriving packet (at the tail) is dropped. This is the default behavior for most internet routers.

### Examples

| Scenario | FCFS + Tail Drop Behavior |
| :--- | :--- |
| **Web Browsing** | A user clicks a link. The HTTP request packet is placed at the end of a long queue of streaming video packets. The user experiences high latency (buffering) until the streaming packets clear. |
| **VoIP / Video Call** | A real-time voice packet arrives. It is placed after a large file download packet (e.g., a software update). The voice packet must wait, causing jitter and audible lag. |
| **[[TCP Global Synchronization]]** | When the queue is full, multiple TCP flows all drop packets simultaneously (Tail Drop). All flows halve their sending rate (via [[TCP Congestion Control]]), causing the link to underutilize, then all ramp up together again. |

### Applications

- **Baseline Model:** Used in simulators (e.g., [[ns-3]], [[OMNeT++]]) to benchmark more complex algorithms.
- **Legacy Routers:** Default behavior of many older "dumb" network switches and routers.
- **Batch Processing:** In operating systems, the simplest [[CPU Scheduling]] (FCFS) is analogous.
- **Customer Service:** Physical queues in banks, grocery stores, or call centers (Single Queue, Single Server model).

### Key Properties

| Property | Value |
| :--- | :--- |
| **Fairness** | Low (Does not distinguish between flow sizes or priority) |
| **Complexity** | Very Low (O(1) enqueue/dequeue) |
| **Latency** | High under load ([[Bufferbloat]] prone) |
| **Throughput** | Stable, but prone to [[Congestion Collapse]] |

### Limitations (Why it's failing)

1.  **No Isolation:** A single aggressive flow (or a burst of traffic) can fill the buffer, starving all other flows (the "[[Noisy Neighbor]]" problem).
2.  **Lock-Out Phenomenon:** In some cases with low buffers, a single flow can synchronize with the empty buffer state, locking out other flows entirely.
3.  **[[Bufferbloat]]:** Combined with large memory buffers on cheap routers, FCFS + Tail Drop causes huge standing queues, leading to massive latency (often seconds) even while throughput remains high.

### Critique & Alternatives

The FCFS Gateway is considered **suboptimal** for modern internet traffic (mix of burst, real-time, and bulk data). It is being replaced or augmented by:

- **[[Fair Queuing]] (FQ):** Creates separate FCFS queues per flow, preventing one flow from starving another.
- **[[CoDel]] (Controlled Delay):** Keeps the FCFS queue but actively drops packets when the *sojourn time* (dwell time in the queue) exceeds a target, attacking [[Bufferbloat]].
- **[[ECN]] (Explicit Congestion Notification):** Marks packets instead of dropping them, allowing the sender to react before the queue overflows.

### See Also

- [[Queueing Discipline]]
- [[FIFO (First In, First Out)]]
- [[Tail Drop]]
- [[Quality of Service (QoS)]]
- [[Fair Queuing]]

---

> **External Links (Illustrative):**
> * [RFC 9700 - The FCFS Gateway Concept](https://www.rfc-editor.org/rfc/rfc9700) (Hypothetical reference conceptualizing the behavior)
> * [Wikipedia: FIFO (computing and electronics)](https://en.wikipedia.org/wiki/FIFO_(computing_and_electronics))