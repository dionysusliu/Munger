>        

# FQ gateways

**FQ gateways** (Fair Queuing gateways) is a mental model for managing competing demands on a shared resource by ensuring that no single flow can starve others. Derived from network traffic scheduling, the model emphasizes **fairness** over raw throughput, preventing “noisy neighbors” from degrading the experience of others.

## Explanation

At its core, an FQ gateway treats each incoming stream (or “flow”) as a separate queue. Rather than processing packets in a simple first‑in‑first‑out (FIFO) order, the gateway interleaves service among all active queues in a round‑robin or weighted fashion. This prevents a bursty or large flow from monopolizing the resource.

The mental model can be applied beyond networking to any system where multiple agents compete for a limited resource (CPU time, memory, budget, attention, etc.). The key insight is that **fairness emerges from explicit queue management**, not from hoping everyone will behave nicely.

### Core principles

- **Separation of concerns** – Isolate each flow so that its behavior doesn’t directly affect others.
- **Proportional service** – Give each flow a roughly equal share of the resource over time.
- **Protection against misbehavior** – A greedy or malfunctioning agent cannot starve others.

## Examples

### 1. Network router (classic use)
A home router with several devices streaming video, browsing, and gaming. Without FQ, a single device running a large download can fill the router’s buffer, causing latency spikes for all others ([[Bufferbloat]]). With FQ, each device gets its own queue, so the gamer’s small packets are interleaved quickly even while the downloader’s queue is full.

### 2. Team workload management
A software team has a shared code review queue. If one developer submits many large pull requests, they could block everyone else’s smaller fixes. An FQ approach would give each developer a separate queue and process reviews round‑robin, ensuring that no single developer dominates the reviewers’ time.

### 3. Cloud resource allocation
In a multi‑tenant database, one tenant’s heavy query might hog CPU and I/O. By implementing fair queuing at the query scheduler, each tenant gets a guaranteed slice, preventing a “noisy neighbor” from degrading service for others.

## Applications

| Domain                | How FQ gateways apply                                                                 |
|-----------------------|---------------------------------------------------------------------------------------|
| **Computer networks** | QoS algorithms (FQ, WFQ, FQ‑CoDel) reduce latency and jitter. See [[Quality of Service]]. |
| **Operating systems** | CPU scheduling (fair share schedulers, e.g., CFS in Linux) allocate time slices fairly. |
| **Business processes**| Load‑balancing across departments or customers ensures no single client consumes all support resources. |
| **Personal productivity** | Time‑boxing tasks (e.g., Pomodoro) can be seen as a simple FQ gateway for your attention. |

## Related mental models

- [[Bufferbloat]] – The problem FQ gateways solve in networks.
- [[Tragedy of the Commons]] – Without FQ, shared resources can be overused.
- [[Round‑Robin Scheduling]] – A specific implementation of fair queuing.
- [[Queueing Theory]] – The mathematical foundation behind these models.

---

*FQ gateways remind us that fairness is not accidental—it must be designed into the system.* By explicitly carving out separate queues and servicing them equitably, we can prevent a few aggressive flows from ruining the experience for everyone.