# Nonpreemptive Version

## Definition

A **nonpreemptive version** refers to a variant of the packet-by-packet (or bit-by-bit) fair queuing algorithm in computer networking where a packet currently being transmitted is **not interrupted** or preempted, even if a higher-priority or more "deserving" packet arrives during its transmission. This is a practical implementation choice made to avoid the complexity and overhead of preempting and resuming packet transmissions.

In the idealized bit-by-bit round-robin model, the scheduler would switch between flows after every bit, achieving perfect fairness. However, real networks transmit whole packets. The nonpreemptive version approximates this ideal by allowing the current packet to finish before applying the next scheduling decision.

## Key Characteristics

- **No mid-packet interruption**: Once a packet starts transmission, it completes regardless of new arrivals.
- **Practical simplicity**: Avoids the need to save/restore packet state mid-transmission.
- **Slight fairness trade-off**: May introduce minor short-term unfairness compared to a preemptive version.
- **Common in real systems**: Most hardware and software network schedulers use nonpreemptive behavior.

## Examples

### Example 1: Fair Queuing in Routers
A router using Weighted Fair Queuing (WFQ) with nonpreemptive behavior:
- Flow A sends a 1500-byte packet, which begins transmission.
- During transmission, Flow B (with higher weight) sends a 100-byte packet.
- The router **does not** stop Flow A's packet. Flow B's packet waits until Flow A finishes.
- This is simpler than preempting, which would require buffering the partial packet.

### Example 2: CPU Scheduling Analogy
In operating systems, a nonpreemptive scheduler (e.g., cooperative multitasking) lets a process run to completion before switching. Similarly, a nonpreemptive packet scheduler lets the current packet finish before selecting the next flow.

## Related Mental Models

- [[Bit-by-Bit Fair Queuing]] – The idealized model that the nonpreemptive version approximates.
- [[Preemptive Version]] – The alternative that interrupts current transmission for fairness.
- [[Packet-by-Packet Fair Queuing]] – The broader algorithm family.
- [[Weighted Fair Queuing (WFQ)]] – A common implementation using nonpreemptive behavior.
- [[Round-Robin Scheduling]] – The underlying fairness mechanism.
- [[Work-Conserving vs. Non-Work-Conserving]] – Related design trade-off in schedulers.

## Practical Implications

- **Pros**: Lower implementation complexity, no need for packet fragmentation/reassembly, compatible with existing hardware.
- **Cons**: Can cause temporary unfairness (e.g., a large packet from a low-weight flow delays a small packet from a high-weight flow).
- **Mitigation**: Use small maximum packet sizes or combine with [[Deficit Round Robin]] to bound unfairness.

## See Also

- [[Max-Min Fairness]]
- [[Quality of Service (QoS)]]
- [[Network Scheduler]]