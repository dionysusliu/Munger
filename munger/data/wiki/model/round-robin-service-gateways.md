>                           Th

# Round Robin Service Gateways

## Overview

A **round robin service gateway** is a mental model for distributing requests or tasks across multiple resources in a sequential, cyclic manner. It draws inspiration from the computer networking and load‑balancing concept of round‑robin scheduling, where each server or worker takes a turn handling incoming work. The model embodies **fairness**, **simplicity**, and **predictability** — at the cost of not adapting to varying loads or resource capacities.

## Explanation

The core idea is straightforward:

1. A list of available resources (servers, workers, queues, etc.) is maintained.
2. Incoming requests are assigned to resources one after another in a fixed order.
3. When the last resource is reached, the assignment loops back to the first.
4. No resource is skipped or given priority unless explicitly configured (e.g., weighting).

This model is often implemented as a **stateless** algorithm, meaning it does not track the current load of each resource. It assumes all resources are equally capable and available. If one resource fails or becomes slow, a round‑robin gateway may continue sending traffic to it unless health checks are added (a common extension called *weighted* or *adaptive* round‑robin).

### Key Characteristics

| Property | Description |
|----------|-------------|
| **Fairness** | Each resource receives an equal share of requests over the long run. |
| **Simplicity** | Easy to understand, implement, and debug. |
| **Low overhead** | No need to query resource state for every decision. |
| **No starvation** | Every resource is guaranteed to be used. |
| **Ignores capacity** | Does not react to current load or processing speed. |

## Examples

### 1. Web Server Load Balancing
A common use – a set of three web servers behind a load balancer:

```
Request 1 → Server A
Request 2 → Server B
Request 3 → Server C
Request 4 → Server A
Request 5 → Server B
...
```
If Server B becomes overloaded, requests are still sent to it until it fails or an external health check removes it.

### 2. DNS Round‑Robin
Domain Name Systems often use round‑robin to distribute queries among multiple IP addresses for the same hostname. Each DNS lookup returns the next IP in the list, spreading client connections across servers.

### 3. Task Queue Workers
Imagine a queue of jobs and three worker processes. A round‑robin dispatcher assigns jobs in order: worker 1, worker 2, worker 3, then back to worker 1. This prevents any one worker from being idle for long.

### 4. Physical Retail Checkouts
A less technical analogy: a supermarket with three checkout counters. New customers are directed to counter #1, then #2, then #3, then repeat. This ensures all cashiers serve an equal number of customers, regardless of queue length (ignoring that customers with full carts take longer – a limitation).

## Applications

Round‑robin service gateways are appropriate when:

- **Resources are roughly homogeneous** in capacity and speed.
- **Short‑lived tasks** predominate, making load variations average out.
- **Simplicity** is more important than optimal performance.
- **Session affinity** is not required (e.g., stateless APIs).
- **Fault tolerance** is handled externally (e.g., automatic server removal).

They are less suitable for:

- Tasks with highly variable processing times (e.g., video encoding with different file sizes).
- Situations where some resources are significantly faster or more powerful.
- Applications requiring real‑time load awareness (use [[Weighted Round Robin]] or [[Least Connections]] instead).

## Limitations & Counter‑Considerations

| Limitation | Mitigation |
|------------|------------|
| Does not adapt to resource load | Combine with health checks or dynamic weighting ([[Adaptive Load Balancing]]). |
| Cannot handle heterogeneous resources | Use **weighted round‑robin** – assign different shares (e.g., 3:2:1). |
| Non‑linear effects (e.g., slow request blocks) | Add timeouts or circuit breakers ([[Circuit Breaker Pattern]]). |
| Requires careful handling of failures | Use a [[Service Registry]] to remove dead nodes. |

## Related Mental Models

- [[Load Balancing]] – the broader family of distribution strategies.
- [[Scheduling Algorithms]] – including FIFO, priority queues, and shortest job first.
- [[Token Bucket]] – a rate‑limiting pattern that can complement round‑robin.
- [[Random Distribution]] – an alternative “fair‑by‑chance” approach.
- [[Polling vs. Event‑Driven]] – paradigms for deciding when to assign work.

## References

- “Round‑Robin Scheduling” – Operating Systems concepts.
- “DNS Round‑Robin” – IETF RFC 1794.
- “Load Balancing 101” – Nginx / HAProxy documentation.
- T. H. Cormen et al., *Introduction to Algorithms* (Chapter on Scheduling).

---

*Round‑robin service gateways are a proven, simple way to achieve basic fairness. Use them as a starting point, and evolve toward more adaptive models when monitoring reveals imbalances.*