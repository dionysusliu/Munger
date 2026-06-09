# Round-Robin Service

## Overview

**Round-Robin Service** is a scheduling algorithm that distributes resources (e.g., bandwidth, CPU time, or network capacity) equally among multiple consumers in a cyclic order. Each consumer receives a fixed quantum (time slice or packet) in turn, ensuring **fairness** over time. While conceptually simple, pure round-robin (RR) does not always deliver the same instantaneous allocation as its more refined variants, such as **Bit-by-bit Round Robin (BR)** or **Weighted Fair Queuing (WFQ)**.

## Core Concepts

### Quantum-Based Allocation
- Each flow or connection is assigned a **service quantum** (e.g., number of bytes or time slots).
- The scheduler cycles through all active flows in order, granting each one its quantum before moving to the next.
- Over a complete cycle, every active flow receives equal service opportunity.

### Fairness
- **Long-term fairness**: Over many cycles, each flow gets an equal share of the resource.
- **Instantaneous fairness**: The allocation at any given moment may differ significantly from the long-term average—this is where pure RR diverges from BR variants.

## Pure Round-Robin vs. Bit-by-Bit Round Robin

| Feature | Pure Round-Robin (RR) | Bit-by-Bit Round Robin (BR) |
|---|---|---|
| **Allocation unit** | Fixed-size packet/quantum (e.g., 1500 bytes) | Single bit (or very small unit) |
| **Instantaneous fairness** | Poor: Large packets dominate bandwidth temporarily | Near-perfect: All flows progress equally at all times |
| **Complexity** | Low | Higher (requires virtual time tracking) |
| **Use case** | Simple environments, no need for tight latency bounds | QoS, real-time traffic, strict fairness |

### Why Pure RR Lacks Instantaneous Fairness
- When flows send variable-size packets, a flow with a large packet will consume more time than one with small packets during its turn.
- This creates a **temporary imbalance**—the large-packet flow gets more bandwidth in that moment, even though averages out over cycles.

### Example: Pure RR vs. BR
- **Scenario**: Two flows:
  - Flow A: 1500-byte packets
  - Flow B: 500-byte packets
  - Bandwidth: 1 Mbps, quantum = 500 bytes

- **Pure RR**:
  - Cycle 1: A sends 1500 bytes → B waits until A finishes → B sends 500 bytes.
  - Instantaneously: A gets 3x more bandwidth than B during that cycle.

- **Bit-by-bit RR**:
  - Both flows send 1 bit each in strict alternation.
  - No flow ever gets ahead: instantaneous allocation = 50/50 at all times.

## Applications

### Network Scheduling
- **Pure Round-Robin**: Used in simple routers where fairness over long periods is sufficient and implementation cost must be low.
- **BR/WFQ**: Used in corporate routers, data centers, and real-time systems needing low jitter and tight bandwidth guarantees (e.g., VoIP, video streaming).

### Operating Systems
- **CPU Scheduling**: Round-robin scheduler (e.g., in early Unix) cycles through processes with a fixed time quantum.
- **Fair Share Scheduler**: Modern kernels use weighted variants for interactive vs. batch processes.

### Disk I/O
- **I/O Scheduling**: Round-robin can balance requests across multiple disk queues, but variant like **Deadline Scheduler** adds priority to avoid starvation.

## Advantages & Disadvantages

### Advantages of Pure RR
- Simple to implement
- No starvation (every flow gets a turn)
- Low overhead (no virtual time calculations)

### Disadvantages
- Poor instantaneous fairness with variable-size packets
- Higher jitter and latency variance
- Cannot provide differentiated service weights (no quality of service guarantees)

### Improvements
- [[Weighted Fair Queuing (WFQ)]]: Assigns weights to flows, approximating BR with virtual finishing times.
- [[Deficit Round Robin (DRR)]]: Uses a deficit counter to handle variable packet sizes more fairly while keeping O(1) complexity.
- [[Hierarchical Round Robin]]: Nested round-robin structures for multi-level scheduling.

## Related Pages

- [[Weighted Fair Queuing (WFQ)]]
- [[Deficit Round Robin (DRR)]]
- [[Quality of Service (QoS)]]
- [[Network Scheduler]]
- [[Fair Queueing Algorithms]]
- [[CPU Scheduling]]

## Summary

Round-Robin Service is a foundational fair scheduling algorithm, but its simplicity comes at the cost of **instantaneous fairness** when packet sizes vary. Variants like **Bit-by-bit Round Robin**, [[Deficit Round Robin]], and **Weighted Fair Queuing** address this by emulating finer-grained or weighted allocation. Choose pure RR for environments where long-term fairness suffices, and move to BR-based algorithms where low jitter and real-time guarantees are critical.