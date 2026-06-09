# Bit-by-Bit Round-Robin Algorithm

## Overview

The **Bit-by-Bit Round-Robin (BR)** algorithm is a theoretical ideal for fair bandwidth allocation among multiple data flows. It defines a perfect fairness model where the server processes exactly **one bit from each active flow in a round-robin fashion**, cycling through all flows repetitively. This idealized model serves as the benchmark that practical algorithms like [[Packet-by-Packet Fair Queuing]] (PGPS) aim to emulate.

## Key Characteristics

- **Work-conserving**: The server never idles if there is any backlogged flow.
- **Perfect fairness**: Each flow receives service proportional to its reserved rate (if weights are equal, each gets identical service).
- **Fluid-flow model**: Operates at the **bit level**, ignoring packet boundaries.
- **Theoretical ideal**: Cannot be implemented in practice due to the packet granularity of real networks.

## How It Works

1. **Round structure**: The server maintains a virtual "round" counter. One round = transmission of **one bit** from every currently backlogged flow.
2. **Service order**: Within a round, flows are served sequentially in a fixed order (e.g., Flow 1, Flow 2, ..., Flow N).
3. **Completion**: A flow finishes transmitting when its final bit is served.

### Example

Consider three flows (A, B, C) with packets of sizes:
- Flow A: 3 bits
- Flow B: 2 bits  
- Flow C: 4 bits

**Ideal BR service sequence** (bits served per round):
```
Round 1: A₁ B₁ C₁
Round 2: A₂ B₂ C₂
Round 3: A₃    C₃
Round 4:       C₄
```

- Round 1: One bit from each flow → A has 2 bits left, B has 1, C has 3.
- Round 2: One bit from each → A has 1 bit left, B finishes, C has 2.
- Round 3: Only A and C are active → A finishes, C has 1 bit left.
- Round 4: C finishes.

## Practical Emulation: Packet-by-Packet Algorithm

The **[[Packet-by-Packet Fair Queuing (PGPS)]]** algorithm emulates BR by:

1. Computing a **virtual finish time** for each packet as if it were served bit-by-bit.
2. Scheduling packets in order of these virtual finish times.

### Why Emulation Is Needed

- Real networks transmit **whole packets**, not individual bits.
- The BR ideal provides a **reference model** to compute fairness guarantees.
- PGPS achieves a fairness bound: No flow receives more than **one maximum-size packet** worth of extra service compared to BR.

## Applications

| Domain | Use Case |
|--------|----------|
| **Router QoS** | Fair queuing for per-flow bandwidth allocation |
| **ATM Networks** | Cell-level scheduling with guaranteed rates |
| **Wireless Scheduling** | Channel-aware fair allocation |
| **Cloud Networking** | Virtual machine bandwidth guarantees |

## Relationship to Other Algorithms

- **[[Weighted Fair Queuing (WFQ)]]** – Generalized version supporting unequal weights
- **[[Deficit Round Robin (DRR)]]** – Practical implementation with lower complexity
- **[[Earliest Deadline First (EDF)]]** – Different scheduling discipline based on deadlines

## Limitations

- **Not realizable** due to bit-level granularity
- **Computationally expensive** to emulate in hardware
- **Assumes fixed order** of flows; real implementations may use [[Virtual Time]] for efficiency

## Learn More

- [[Packet-by-Packet Fair Queuing]]
- [[Weighted Fair Queuing]]
- [[Fair Queuing Theory]]
- [[Quality of Service (QoS)]]