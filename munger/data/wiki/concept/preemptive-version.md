# Preemptive Version

A **preemptive version** of a packet-by-packet algorithm is a scheduling mechanism in which a newly arriving packet with a smaller *F<sub>i</sub><sup>a</sup>* (finish number, or a similar virtual-time stamp) immediately interrupts the transmission of the currently transmitting packet, allowing the higher-priority (earlier-finish) packet to be served first.

This contrasts with a **[[Non-Preemptive Version]]**, where a packet once started is transmitted to completion, even if a higher-priority packet arrives.

## Definition

In the context of packet scheduling (e.g., **[[Packet-by-Packet Generalized Processor Sharing (PGPS)]]** or **[[Weighted Fair Queueing (WFQ)]]**), each packet is assigned a finish number *F<sub>i</sub><sup>a</sup>* that represents the virtual time at which the packet would complete service under an ideal fluid-flow system. A preemptive scheduler checks this value upon every arrival. If the incoming packet’s finish number is smaller than that of the packet currently being transmitted, the current packet is preempted (its transmission is suspended) and the new packet begins transmission immediately. The preempted packet is requeued and will resume later based on its original finish number.

Key properties:
- **Interrupts ongoing transmission** – requires the network interface to support preemption (e.g., packet segmentation or abort capability).
- **Sensitive to arrival order** – the decision is made packet-by-packet, not flow-by-flow.
- **Provides tighter delay bounds** for high-priority traffic, but can increase overhead from preemptions.

## Example

Consider a single link with two flows:
- **Flow A**: Packet arrives at time 0, size 1500 bytes, finish number *F<sub>A</sub>* = 10.
- **Flow B**: Packet arrives at time 2, size 500 bytes, finish number *F<sub>B</sub>* = 5.

Under a preemptive version (preemptive WFQ):
1. At t=0, Packet A starts transmission (since it’s the only packet).
2. At t=2, Packet B arrives with *F<sub>B</sub>* = 5 < *F<sub>A</sub>* = 10. The scheduler preempts Packet A.
3. Packet B is transmitted to completion (takes 500 bytes / link speed).
4. After Packet B finishes, Packet A resumes from where it was interrupted.

Without preemption, Packet A would complete first, delaying Packet B.

## Related Mental Models

- **[[Non-Preemptive Version]]** – The default mode of most packet schedulers (e.g., FIFO, non-preemptive WFQ). Simpler to implement but can cause priority inversion.
- **[[Priority Queueing]]** – A stricter form of preemptive scheduling based on fixed priority classes rather than dynamic virtual finish numbers.
- **[[Earliest Deadline First (EDF)]]** – A preemptive scheduling policy using absolute deadlines instead of virtual finish numbers.
- **[[Round-Robin Scheduling]]** – Typically non-preemptive; preemptive variants exist for time-sharing systems.
- **[[Packet Segmentation]]** – A hardware mechanism often required to support preemption (e.g., Ethernet jumbo frames may need to be fragmented).

## Trade‑offs

| Advantage | Disadvantage |
|-----------|--------------|
| Better delay bounds for time‑sensitive flows | Higher implementation complexity and CPU overhead |
| Closer emulation of ideal fluid GPS | Packet fragmentation and reassembly overhead |
| Natural fit for real‑time traffic | Possible starvation of lower‑priority flows |

## See Also

- [[Finish Number (Fⁱᵃ)]]
- [[Virtual Time Scheduling]]
- [[Generalized Processor Sharing (GPS)]]
- [[Packet-by-Packet Algorithm]]