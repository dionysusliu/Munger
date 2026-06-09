>     

# FCFS Gateways

## Definition

**FCFS gateways** represent a specific application of the **First-Come, First-Served (FCFS)** scheduling principle (also known as **FIFO – First In, First Out**) to network gateways. In this context, a gateway processes incoming packets, requests, or connections strictly in the order they arrive, without prioritization, preemption, or reordering. The queue maintained by the gateway operates as a simple linear buffer: the first packet to enter the queue is the first to be forwarded or processed.

This behavior is pervasive in simple network devices, router interfaces, and API gateways where fairness of order is desired over performance optimization. While easy to implement, FCFS gateways suffer from the **convoy effect**, where a single large or slow packet delays all subsequent packets, and from **head-of-line blocking**, where a blocked first packet stalls the entire queue.

FCFS gateways are often contrasted with priority‑based or fair‑queuing gateways, which aim to reduce latency for time‑sensitive traffic.

## Examples

### 1. Simple Router Interface Queue
- A low‑cost home router uses a single FIFO buffer for outbound traffic on a DSL link.
- All packets (web browsing, VoIP, video streaming) are enqueued in arrival order.
- **Effect**: If a large file download arrives first, a subsequent VoIP packet must wait until the file’s packets are transmitted, causing audible jitter.

### 2. API Gateway with FCFS Limiting
- A cloud API gateway throttles requests by queuing them in arrival order.
- Every request is processed in the exact sequence it was received.
- **Effect**: A compute‑intensive request can block hundreds of lightweight health‑check requests behind it, increasing tail latency.

### 3. Legacy Terminal Gateway (Serial Line)
- In older terminal servers (e.g., connecting serial terminals to a host), characters were buffered and forwarded in FCFS order.
- No flow control or priority was applied, leading to “line noise” affecting all subsequent characters.

## Related Mental Models

- **[[FCFS Scheduling]]** – The foundational scheduling algorithm in operating systems. FCFS gateways are a direct networking analog.
- **[[FIFO Queue]]** – The data structure underlying FCFS gateways. Understanding queue behavior is essential.
- **[[Head‑of‑Line (HoL) Blocking]]** – The main downside of FCFS gateways, where the first packet blocks later packets even if those later packets could be processed faster.
- **[[Convoy Effect]]** – A phenomenon where a single slow or large task forces all subsequent tasks to wait, reducing throughput.
- **[[Queuing Theory]]** – The mathematical study of waiting lines (queues). FCFS is the simplest discipline (FIFO) and is described by M/M/1 and other basic models.
- **[[Fair Queuing]]** – A contrasting mental model where gateways attempt to allocate bandwidth or processing fairly among flows, avoiding the bias of FCFS toward bursty or large flows.
- **[[Network Bufferbloat]]** – Excessive buffering in FCFS gateways can lead to high latency, mitigated by active queue management (AQM) like CoDel or RED.

For further reading, see [[First-Come, First-Served]], [[Queueing Disciplines]], and [[Network Gateway Architectures]].