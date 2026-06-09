>  makes q

Here is a wiki page for the **First-Come, First-Served (FCFS) Gateway** mental model.

---

# FCFS Gateway

**FCFS Gateway** is a mental model for thinking about systems, queues, and fairness under a strict first-in, first-out (FIFO) discipline. It describes any process, decision gate, or resource allocation system where requests or entities are serviced in the exact order they arrive, with no prioritization, reordering, or skipping.

The name is a hybrid: "FCFS" comes from operating system scheduling theory, while "Gateway" visualizes the single, orderly bottleneck through which all traffic must pass.

## Core Principles

1.  **Single File, No Cuts:** The order of arrival is the only factor determining service order.
2.  **No Priorities:** Every entity is treated identically regardless of urgency, size, or importance.
3.  **Bounded Predictability:** If you know the arrival rate and service time, you can predict wait times exactly.
4.  **Fairness vs. Efficiency Trade-off:** FCFS is considered the "fairest" method in terms of procedural justice, but it is often the least efficient for optimizing total throughput or minimizing average wait time.

## Explanation

Imagine a single bridge with a toll booth. Cars arrive from different highways and merge into a single lane at the gate. The first car to arrive at the gate pays and goes through first. The 100th car to arrive *must* wait for the 99 cars ahead of it, even if that car is an ambulance or a diplomat.

This is FCFS: **absolute chronological order**.

In computing, the "gateway" might be a CPU core handling processes. In a physical store, it’s the checkout line. In organizational decision-making, it’s an email inbox processed in order of receipt.

### The Mental Model in Action

The model forces you to visualize a **single channel** (the gateway) and a **queue** (the line). The key insight is that the FCFS Gateway creates a *priority-free zone*. This is both its greatest strength (no bias) and its greatest weakness (no ability to react to emergencies).

## Examples

### 1. Computer Science: The FCFS Scheduler
In an operating system, the FCFS scheduling algorithm runs processes on a CPU in the order they are created.
- **Input:** `[Process A (10ms), Process B (2ms), Process C (5ms)]`
- **Output:** A runs for 10ms, B runs for 2ms, C runs for 5ms.
- **Result:** The *average wait time* is high because a long process (A) blocks all subsequent short processes. This is known as the **convoy effect**, a classic downside of FCFS.

### 2. Customer Service: The Single Queue
A bank or fast-food restaurant uses a single winding queue feeding multiple tellers. The "FCFS Gateway" is the single queue itself; the order of service is determined by arrival order, even if multiple servers are available.
- **Compare to:** Multiple queues (one per teller), which can lead to unfair wait times if a slow customer blocks a line.

### 3. Everyday Life: The "Take a Number" System
A deli counter with a ticket dispenser is a pure FCFS Gateway. You cannot jump ahead, and the system is entirely transparent. Everyone sees the number being served.

### 4. Workflow: Email Inbox (if processed chronologically)
If you process emails in the order they are received (oldest first), you are operating an FCFS Gateway. A low-priority email from yesterday will be handled before an urgent email from your CEO that arrived 5 minutes ago.

## Applications

### When to Use FCFS (The Gateway is a Good Idea)

- **Fairness is paramount:** When the cost of perceived bias (queue jumping) is higher than the cost of inefficiency.
- **Requests are homogeneous:** When all tasks have roughly the same processing time or value. The convoy effect is minimized.
- **Traceability is required:** In legal or auditing contexts, knowing that "first filed, first served" was applied is a simple, defensible rule.
- **Consumer trust:** Grocery checkout lines (single queue) build trust that the system is not rigged.

### When to Avoid FCFS (The Gateway is a Bottleneck)

- **Variable task size:** When a short, urgent task is likely to be blocked by a long, unimportant one.
- **Real-time systems:** In a hospital emergency room, triage explicitly *rejects* FCFS in favor of severity.
- **High throughput requirements:** FCFS generally minimizes throughput compared to algorithms like Shortest Job First (SJF) or Round Robin (RR).
- **Priorities exist:** When you have a clear ranking of importance (e.g., VIP customers, interrupt requests).

## Related Mental Models

- [[Queueing Theory]] - The mathematical foundation of wait times, utilization, and bottlenecks.
- [[Bottleneck (Constraint)]] - The FCFS Gateway is often the bottleneck; the rate of the gateway determines the pace of the entire system.
- [[Opportunity Cost]] - Every minute spent in the FCFS queue is a minute not spent elsewhere. This is the hidden cost of "fair" waiting.
- [[Pareto Principle (80/20 Rule)]] - FCFS violates the Pareto principle by not prioritizing the "vital few" over the "trivial many."
- [[Convoy Effect]] - The specific pathology of FCFS where a large task holds up many small tasks.

## Countermodel: Triage

The most direct counter to FCFS Gateway is **triage**. In a triage system, the gateway analyzes the incoming entities and **re-orders** them based on urgency or value. This is FCFS *with a priority interrupt*. It is more efficient but introduces the risk of bias and starvation (where low-priority items may never be served).

## Key Takeaway

The FCFS Gateway is the **simplest possible scheduling model**. It is the default for a reason: it is intuitive, predictable, and procedurally just. However, its simplicity is also its failure mode. Whenever you see a single queue, ask: *Is the convoy effect killing our throughput, or is the procedural fairness worth the wait?*