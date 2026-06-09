# Fairness

**Fairness** is a core requirement for any adequate queueing algorithm, ensuring that resources are allocated to [[User]]s and [[Conversation]]s in a manner that prevents starvation, excessive delay, or systematic bias. In queueing theory and system design, fairness balances efficiency with equity, often trading off against throughput or latency.

## Definition

In the context of queueing algorithms, fairness means that all **users** and **conversations** receive a “fair share” of processing time or bandwidth according to a predetermined policy. A queue is fair if:

- No user or conversation is indefinitely postponed (freedom from [[Starvation]]).
- The service order approximates some ideal distribution (e.g., first-come-first-served, proportional to weight, or round-robin).
- The algorithm provides **bounded waiting** – each entity is served within a finite time.

### Definitions of Key Terms

- **[[User]]** – An entity (human, process, or agent) that generates requests or interactions. In a chat system, a user is a participant; in an operating system, a user is a process or thread. Fairness across users ensures that no single user monopolizes the queue.

- **[[Conversation]]** – A sequence of related interactions between users or between a user and a system. For example, a multi‑turn dialogue, a transaction, or a session. Fairness across conversations means that longer or more active conversations do not starve shorter ones, and that each conversation makes progress.

## Examples

### 1. Round‑Robin Queueing
Each user or conversation receives a fixed time slice in cyclic order. This guarantees that no entity waits longer than `(n-1) × time_slice` before being served.

### 2. Weighted Fair Queueing (WFQ)
Each conversation is assigned a weight (e.g., based on priority or resource entitlement). The algorithm serves packets in order of their finish time in a virtual clock system, approximating a bit‑by‑bit round‑robin. WFQ is widely used in network routers to ensure fairness among flows.

### 3. First‑Come, First‑Served (FCFS)
The simplest fairness policy: requests are processed in arrival order. While intuitively fair, FCFS can lead to the **convoy effect** where a long request blocks many short ones, reducing overall fairness for later arrivals.

### 4. Priority Queue with Aging
To prevent starvation, low‑priority conversations have their priority increased over time (aging). This ensures that even low‑priority users eventually receive service.

## Related Mental Models

- [[Starvation]] – A situation where a user or conversation never gets service due to higher‑priority entities always being chosen. Fairness algorithms must explicitly avoid starvation.

- [[Bounded Waiting]] – A guarantee that a request will be served after a finite number of other requests. This is a formal property of fair queues.

- [[Throughput vs. Fairness Trade‑off]] – Maximizing total throughput often hurts fairness (e.g., serving only the fastest users). Many queueing algorithms (e.g., max‑min fairness) balance these goals.

- [[Priority Inversion]] – When a high‑priority conversation is blocked by a lower‑priority one holding a shared resource, violating fairness. Solutions like priority inheritance restore fairness.

- [[Latency]] – Fairness can increase average latency for some users (e.g., by forcing a long job to wait for short ones). Understanding this trade‑off is critical for system design.

## Implications for System Design

An adequate queueing algorithm must define what “fair” means for its specific domain. For instance:

- In a **chat system**, fairness might require that each user’s messages are interleaved, and that a single verbose conversation does not dominate the server’s response time.
- In a **task scheduler**, fairness often means that each process gets a proportional share of CPU time over a window.
- In a **load balancer**, fairness ensures that no backend server is overloaded while others idle.

Fairness is not absolute; it is always relative to a chosen policy and the definitions of [[User]] and [[Conversation]]. A system that is fair for users may be unfair for conversations if, for example, a single user starts many conversations that each receive equal weight. Therefore, the queueing algorithm must explicitly state its fairness criterion and the entities it treats as peers.

---

*For further reading, see [[Queueing Theory]], [[Resource Allocation]], and [[Scheduling Algorithms]].*