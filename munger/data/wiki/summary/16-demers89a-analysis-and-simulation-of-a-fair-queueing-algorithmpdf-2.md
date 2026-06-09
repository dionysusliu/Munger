# Analysis and Simulation of a Fair Queueing Algorithm

**Source:** Demers, A., Keshav, S., & Shenker, S. (1989). *Analysis and simulation of a fair queueing algorithm*. Proceedings of ACM SIGCOMM '89.

## Overview

This paper presents a seminal analysis of **fair queueing (FQ)** as an alternative to **first-come-first-serve (FCFS)** queueing at network gateways. The authors demonstrate that FCFS is vulnerable to ill-behaved sources that can disproportionately capture bandwidth, and propose FQ as a robust solution for [[Congestion Control]] in datagram networks.

## Key Problems with FCFS

- **No source isolation**: A single aggressive source can consume most of the gateway's buffer and bandwidth
- **Unfair bandwidth allocation**: Well-behaved sources suffer increased delay and packet loss due to misbehaving flows
- **No protection mechanism**: [[Flow Control]] algorithms like TCP's slow-start are ineffective when competing with non-cooperative sources
- **High delay variance**: Bursty sources cause unpredictable queuing delays for all flows

## Fair Queueing Algorithm

Based on Nagle's original concept, the FQ algorithm implements:

### Core Mechanisms
- **Per-source queuing**: Separate FIFO queues maintained for each active source
- **Round-robin service**: Gateway services one packet from each non-empty queue in cyclic order
- **Bit-by-bit fair queuing approximation**: Simulates a fluid-flow model where each source transmits at equal rate

### Key Properties
- **Fair bandwidth allocation**: Each source receives an equal share regardless of behavior
- **Lower delay for low-usage sources**: Lightly-loaded flows experience minimal queuing delay
- **Protection from misbehavior**: Ill-behaved sources cannot starve other flows
- **Reduced delay variance**: More predictable queuing delays across all flows

## Analysis and Simulation Results

The study compares FQ and FCFS under various [[Flow Control]] algorithms:

### Simulation Setup
- Multiple sources with different traffic patterns (bulk transfer, interactive, bursty)
- Both cooperative (TCP-like) and noncooperative (aggressive) sources
- Various network topologies and gateway buffer sizes

### Key Findings
1. **Fairness**: FQ achieves near-perfect fairness, while FCFS allows aggressive sources to capture 3-5x more bandwidth
2. **Delay performance**: FQ reduces mean delay by 40-60% for well-behaved sources in mixed environments
3. **Robustness**: FQ maintains performance even with 50% noncooperative sources
4. **Throughput**: FQ achieves comparable aggregate throughput to FCFS while providing fairness

## Interactions with Network Protocols

The paper discusses important interactions between:

- **[[Queueing Discipline]] and [[Routing]]**: FQ enables better load balancing as flows are isolated
- **Queueing and Flow Control**: FQ provides natural feedback signals for adaptive flow control
- **Queueing and [[Congestion Avoidance]]**: FQ works synergistically with congestion detection mechanisms

## Conclusions

The authors conclude that fair queueing is more effective than FCFS for congestion control in diverse, decentralized networks. FQ provides:

- **Fair resource allocation** without requiring source cooperation
- **Protection** for well-behaved flows
- **Lower and more predictable delays**
- **Robust performance** in heterogeneous environments

## Impact and Legacy

This paper established the foundation for modern [[Active Queue Management]] and [[Quality of Service]] mechanisms. The FQ concept evolved into:

- [[Weighted Fair Queueing (WFQ)]]
- [[Class-Based Queueing (CBQ)]]
- [[Deficit Round Robin (DRR)]]
- Modern [[Traffic Shaping]] and [[Policing]] algorithms

The work remains influential in [[Internet Congestion Control]] research and [[Network Neutrality]] debates.