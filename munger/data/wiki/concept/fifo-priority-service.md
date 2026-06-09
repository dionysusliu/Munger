# FIFO Priority Service (Combined Round Robin & FIFO)

## Definition

**FIFO Priority Service** is a hybrid queueing discipline that integrates elements of **Round Robin** scheduling with **FIFO (First-In-First-Out)** priority. In this model, multiple priority levels exist, and within each priority level, jobs are served in FIFO order. However, the server cycles through priority levels in a round-robin fashion, ensuring that lower-priority jobs are not starved indefinitely while still giving preference to higher-priority jobs.

This approach is often used in **operating systems**, **network packet scheduling**, and **customer service systems** where a balance between fairness and priority is required.

## Key Characteristics

- **Multiple Priority Queues**: Jobs are classified into discrete priority levels (e.g., high, medium, low).
- **FIFO within each priority**: At each level, jobs are served in the order they arrive.
- **Round Robin across priorities**: The server cyclically visits each priority queue, serving a limited number of jobs (or a time slice) before moving to the next.
- **No starvation**: Lower-priority jobs eventually get service because the server cycles back to them.
- **Analyzable performance**: The model is tractable for queueing theory analysis, especially under Markovian assumptions.

## Examples

### 1. Operating System Process Scheduling
- A CPU scheduler uses multiple priority queues (e.g., real-time, interactive, batch).
- Within each queue, processes are scheduled FIFO.
- The scheduler cyclically checks each queue, giving a time quantum to the next process in the highest non-empty queue, but also occasionally serving lower queues to prevent starvation.

### 2. Network Packet Scheduling (e.g., DiffServ)
- Routers classify packets into priority classes (e.g., voice, video, best-effort).
- Each class has a FIFO queue.
- The router serves packets in a round-robin fashion across classes, but with weighted or priority-based service rates.

### 3. Customer Service Call Centers
- Callers are categorized (e.g., VIP, standard, low-priority).
- Agents serve callers in FIFO order within each category.
- Agents rotate through categories to ensure all callers eventually get served.

## Mathematical Analysis

The FIFO Priority Service model is often analyzed using **queueing theory**, particularly **Markov chains** and **M/G/1 queues with priority scheduling**.

- **State space**: Number of jobs in each priority queue.
- **Service discipline**: Cyclic server with FIFO within each queue.
- **Performance metrics**:
  - Mean waiting time per priority class
  - System throughput
  - Probability of starvation for low-priority jobs
- **Key results**:
  - The system is stable if the total arrival rate is less than the service rate.
  - Higher-priority classes experience lower mean waiting times.
  - The round-robin component ensures that the variance of waiting times is bounded for all classes.

## Related Mental Models

- [[Queueing Theory]] – Foundational framework for analyzing waiting lines and service disciplines.
- [[Priority Queue]] – A data structure where elements are served based on priority, often implemented as a heap.
- [[Round Robin Scheduling]] – A time-sharing discipline where each process gets a fixed time slice in cyclic order.
- [[Starvation]] – A situation where a low-priority job is indefinitely postponed due to continuous arrival of higher-priority jobs.
- [[Work-Conserving Queue]] – A queue discipline that never idles the server when there is work available.
- [[M/G/1 Queue]] – A standard queueing model with Poisson arrivals, general service times, and a single server.
- [[DiffServ (Differentiated Services)]] – A network architecture for traffic prioritization using similar principles.

## Practical Considerations

- **Choosing the number of priority levels**: Too many levels increase overhead; too few may not provide adequate differentiation.
- **Time slice length**: Smaller slices improve fairness but increase context-switching overhead.
- **Weighted variations**: Some implementations assign different service rates to each priority level (e.g., weighted round robin).
- **Real-time constraints**: Hard real-time systems may require strict priority preemption rather than round-robin cycling.

## See Also

- [[FIFO (First-In-First-Out)]]
- [[Priority Inversion]]
- [[Scheduling Algorithms]]
- [[Queueing Delay Analysis]]

---

*This page is part of the [[Systems Design]] and [[Queueing Theory]] knowledge base.*