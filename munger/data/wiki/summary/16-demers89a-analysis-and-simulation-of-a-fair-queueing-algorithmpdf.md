# 16 [Demers89a] Analysis and Simulation of a Fair Queueing Algorithm

## Overview

This paper, by Alan Demers, Srinivasan Keshav, and Scott Shenker, addresses congestion control in datagram networks through gateway queueing algorithms. It proposes and evaluates a **Fair Queueing (FQ) algorithm**, originally suggested by Nagle, as an alternative to traditional First-Come-First-Served (FCFS) queueing.

## Problem with FCFS Queueing

- **Intertwined resources**: FCFS queueing conflates bandwidth allocation, promptness (delay), and buffer space.
- **Reliance on sources**: Congestion control is left entirely to end-systems (sources).
- **Vulnerability to misbehavior**: A single ill-behaved or greedy source can capture a disproportionate share of bandwidth and buffer space, causing unfairness and increased delay for well-behaved flows.

## Fair Queueing (FQ) Algorithm

Based on Nagle's original idea, the FQ algorithm operates as follows:

- **Per-source queues**: The gateway maintains a separate queue for each active source (or flow).
- **Round-robin service**: Queues are serviced in a round-robin fashion, with each queue receiving service in turn.
- **Key advantages**:
  - **Fair bandwidth allocation**: Each source gets an equal share of the link capacity.
  - **Lower delay for low-bandwidth sources**: Sources using less than their fair share experience lower queueing delay.
  - **Protection from misbehavior**: A misbehaving source cannot degrade the performance of other sources; its impact is limited to its own queue.

## Analysis and Simulation

The paper provides both **analytical modeling** and **simulation results** comparing FQ gateways with FCFS gateways.

- **Performance metrics**: Throughput, delay, and fairness under various traffic conditions.
- **Flow control algorithms tested**: The evaluation includes different end-system flow control schemes (e.g., TCP-like behavior).
- **Key findings**:
  - FQ gateways provide significantly better fairness than FCFS gateways.
  - FQ gateways offer lower delay for well-behaved sources, even in the presence of greedy sources.
  - FQ gateways improve overall network stability and robustness against congestion.

## Significance and Legacy

This paper is foundational in the development of fair queueing and active queue management (AQM) techniques. The FQ algorithm directly influenced later work on:

- **Weighted Fair Queueing (WFQ)** for differentiated services.
- **[[Active Queue Management]]** (AQM) mechanisms like RED (Random Early Detection).
- Modern router and switch scheduling disciplines.

The paper demonstrates that intelligent gateway scheduling can effectively complement end-to-end congestion control, leading to more robust and fair networks.

## See Also

- [[Congestion Control]]
- [[Active Queue Management]]
- [[Weighted Fair Queueing]]
- [[Nagle's Algorithm]]