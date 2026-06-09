# 16 [Demers89a] Analysis and simulation of a fair queueing algorithm.pdf

## Abstract

This paper by Demers, Keshav, and Shenker (1989) presents a detailed analysis and simulation of **[[Fair Queueing]] (FQ)** algorithms at network gateways. Fair Queueing is proposed as a fundamental mechanism for **[[Congestion Control]]** in datagram networks, complementing source-based flow control and routing. The work builds on Nagle’s original proposal and demonstrates that FQ provides significant advantages over traditional **[[First-Come-First-Serve]] (FCFS)** queueing, especially in noncooperative network environments.

## Key Concepts

- **Fair Queueing (FQ):** Maintains separate queues per source and services them in a round‑robin fashion. This ensures fair allocation of **bandwidth**, **promptness** (low delay), and **buffer space** among competing flows.
- **Nagle’s Proposal:** Inspired by Nagle’s early work on fair queueing at gateways to prevent ill‑behaved sources from monopolizing network resources.
- **Comparison with FCFS:** FCFS allows a single aggressive source to capture arbitrary bandwidth, increasing delays and drop rates for other sources. FQ prevents this through per‑source isolation.

## Advantages of Fair Queueing Over FCFS

The paper identifies three core benefits of FQ:

1. **Fair bandwidth allocation** – each active source receives an equal share of gateway capacity.
2. **Lower delay for well‑behaved sources** – sources using less than their fair share experience reduced queueing delays, as excess capacity is promptly reassigned.
3. **Protection from misbehaving sources** – a source that sends excessive traffic cannot degrade the performance of other flows; its own queue builds up and is dropped independently.

## Analysis and Simulation

- The paper presents a rigorous **analytic model** of FQ, calculating expected queue lengths, delays, and throughput under various traffic patterns.
- **Simulations** compare FQ with other congestion control mechanisms (e.g., drop‑tail FCFS, random early detection) in both cooperative and **noncooperative** environments.
- Results demonstrate that FQ remains effective even when sources do not follow any end‑to‑end congestion avoidance protocol (e.g., **TCP**). The gateway can isolate and penalize aggressive sources, maintaining fairness across the network.

## Impact and Legacy

Fair Queueing, as analyzed in this paper, became a foundational concept in modern networking. It directly influenced:

- **[[Weighted Fair Queueing]] (WFQ)** – a generalized version that supports traffic classes with different priorities.
- **[[Class‑Based Queueing]] (CBQ)** and **[[Hierarchical Fair Service Curve]] (HFSC)**.
- The design of **Active Queue Management (AQM)** algorithms such as **[[Random Early Detection]] (RED)**.

## External Links

- [Original paper citation and PDF](https://www.eecs.berkeley.edu/Pubs/TechRpts/1989/CSD-89-544.html) (UC Berkeley technical report, 1989)

---

*See also: [[Nagle’s Algorithm]], [[Congestion Avoidance]], [[Flow Control]]*