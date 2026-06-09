# DECbit Algorithm

The **DECbit (DE congestion notification bit) algorithm** is a selective congestion notification mechanism for TCP/IP networks that achieves fair bandwidth allocation while maintaining small average queue sizes. It functions as an [[Active Queue Management]] scheme and [[Flow Control]] mechanism.

## Overview

DECbit uses a single binary feedback bit in packet headers to signal congestion to senders. Routers monitor their queue occupancy and set the bit when congestion is detected, enabling end hosts to adjust their transmission rates accordingly.

## Key Components

### Router-Side Logic

1. **Queue Monitoring**: Each router maintains a running average of queue occupancy using:
   ```
   avg_queue = (1 - α) × avg_queue + α × current_queue
   ```
   where α is typically 0.5

2. **Bit Setting Condition**: Set the DECbit in packet headers when `avg_queue > min_threshold`

3. **Threshold Configuration**: Typically uses a single threshold rather than dual thresholds like [[Random Early Detection]]

### Sender-Side Logic

1. **Window-based Adaptation**: Maintains a congestion window (`cwnd`)

2. **Window Update Rules**:
   ```
   if DECbit is set in more than 50% of packets:
       cwnd = cwnd × (1 - β)  # Multiplicative decrease
   else:
       cwnd = cwnd + 1/cwnd    # Additive increase
   ```
   where β is typically 0.5

3. **Measurement Window**: Tracks DECbit over a period of packet arrivals (usually one round-trip time)

## How It Works

1. **Normal Operation**: When queue is below threshold, senders additively increase their window
2. **Congestion Detection**: When average queue exceeds threshold, routers mark packets with DECbit
3. **Fairness Enforcement**: All flows sharing the link receive feedback proportional to their rates
4. **Response**: Senders observing >50% marked packets reduce their window multiplicatively

## Mathematical Properties

### Fairness

DECbit achieves weighted max-min fairness:
- Each flow i gets bandwidth proportional to its weight w_i
- The algorithm converges to equal window sizes for flows with identical RTTs

### Queue Dynamics

- Average queue size bounded by threshold
- Queue oscillations dampened through exponential averaging
- Small queue sizes maintained through early signaling

## Advantages

1. **Fair Allocation**: Perfect max-min fairness among competing flows
2. **Low Latency**: Small average queue sizes (typically < 20% of buffer)
3. **Efficient Link Utilization**: Prevents bufferbloat while maintaining throughput
4. **Simple Implementation**: Single bit feedback, minimal router state
5. **Stability**: Proven convergence properties under ideal conditions

## Limitations

1. **Bit Overhead**: Requires one reserved bit in packet header (not always available)
2. **Delay Sensitivity**: Performance degrades with heterogeneous RTTs
3. **Burst Sensitivity**: Sudden traffic bursts can cause false congestion signals
4. **Threshold Tuning**: Optimal threshold depends on number of flows and RTTs

## Applications

- [[Data Center Networks]]: Low-latency fair sharing
- [[Cellular Networks]]: Bandwidth allocation among users
- [[Satellite Links]]: Early congestion indication for long-delay paths
- [[Cloud Computing]]: Fair resource sharing in virtualized environments

## Example Scenario

Consider two flows sharing a 10 Mbps link with 100ms RTT:

1. **Initial State**: Both flows send at 5 Mbps, queue empty
2. **Flow 3 joins**: Attempts to send at 5 Mbps, queue grows
3. **Queue exceeds threshold (e.g., 20 packets)**: DECbit marked in packets
4. **Both original flows see >50% marked**: Reduce windows by 50%
5. **New flow also reduces**: All flows converge to ~3.3 Mbps
6. **Result**: Fair 1/3 bandwidth allocation with low queue latency

## Relationship to Other Algorithms

- [[TCP Reno]]: DECbit provides explicit congestion notification vs implicit packet loss
- [[Explicit Congestion Notification (ECN)]]: DECbit is a precursor to modern ECN implementations
- [[Random Early Detection (RED)]]: Both are AQM algorithms but DECbit uses binary feedback

## Code Example (Simplified Router Implementation)

```python
class DECbitRouter:
    def __init__(self, threshold, alpha=0.5):
        self.threshold = threshold
        self.alpha = alpha
        self.avg_queue = 0.0
        
    def enqueue(self, packet):
        self.avg_queue = (1 - self.alpha) * self.avg_queue + \
                         self.alpha * len(self.queue)
        
        if self.avg_queue > self.threshold:
            packet.set_decbit()
        
        self.queue.append(packet)
```

## Research Extensions

- [[XCP (eXplicit Control Protocol)]]: Uses multi-bit feedback for better precision
- [[VCP (Variable-structure Congestion Control)]]: Extends DECbit with multi-level feedback
- [[DCTCP]]: Data Center TCP uses ECN with DECbit-style marking

## See Also

- [[Congestion Control]] overview
- [[Active Queue Management]] techniques
- [[TCP Congestion Avoidance]]
- [[Network Bufferbloat]]