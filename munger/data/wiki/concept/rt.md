# R(t) - The Round Number Function

## Definition

**R(t)** is a continuous, monotonically increasing function that represents the number of rounds completed in a **round-robin service discipline** up to time \( t \). The integer part of \( R(t) \) indicates the number of fully completed rounds, while the fractional part represents a partially completed round. The function increases only when there are bits present at the gateway, making it a **work-conserving** time measure.

### Formal Properties

- **Domain**: \( t \in [0, \infty) \)
- **Range**: \( R(t) \in [0, \infty) \), real-valued
- **Monotonicity**: \( t_1 < t_2 \implies R(t_1) \leq R(t_2) \)
- **Continuity**: \( R(t) \) is continuous in \( t \)
- **Increment condition**: \( \frac{dR}{dt} > 0 \) only when the gateway queue is non-empty

## Usage in Virtual Time Algorithms

R(t) serves as a **virtual time reference** in packet scheduling algorithms, most notably in **Fair Queuing** and **Weighted Fair Queuing (WFQ)** systems. It allows the scheduler to compare the progress of different conversations (flows) on a normalized timescale.

### Active/Inactive Conversation Determination

A conversation \( i \) is determined to be **active** or **inactive** based on the condition:

\[
R(t_{L_a}) > F_{i,a}
\]

Where:
- \( t_{L_a} \) is the arrival time of packet \( a \)
- \( F_{i,a} \) is the **finish number** (virtual finish time) of packet \( a \) in conversation \( i \)

If \( R(t_{L_a}) > F_{i,a} \), the conversation is considered **inactive** (i.e., it has no backlogged packets). Otherwise, it is **active**.

## Bid Calculation Context

In auction or resource allocation systems using virtual time, R(t) is used in **bid calculation**, where it may represent:

- A computed **round-trip time** (RTT) value
- A function of elapsed real time, scaled or transformed
- The current virtual time stamp for comparing competing requests

The bid value \( B_i(t) \) for a participant \( i \) is often expressed as:

\[
B_i(t) = f(R(t), \text{parameters}_i)
\]

## Examples

### Example 1: Simple Round-Robin

Consider a gateway serving three flows (A, B, C) in round-robin. Each round serves one packet from each active flow:

- At \( t=0 \): All flows have packets → R(t) begins increasing
- At \( t=5 \): 2 full rounds completed, 3rd round 40% done → \( R(5) = 2.4 \)
- At \( t=10 \): 4 full rounds completed → \( R(10) = 4.0 \)

### Example 2: Inactive Flow Detection

Suppose flow X has a packet with finish number \( F = 5.2 \). At the next packet arrival time \( t_{arrival} \), if \( R(t_{arrival}) = 6.0 \), then \( 6.0 > 5.2 \), so flow X is declared **inactive** — meaning it has no outstanding packets and its previous packet has been fully served.

## Related Mental Models

- [[Virtual Time]] — The broader concept of using a normalized time reference in distributed systems
- [[Fair Queuing]] — The scheduling discipline that uses R(t) to achieve max-min fairness
- [[Leaky Bucket]] — A traffic shaping model often paired with virtual time scheduling
- [[Work-Conserving System]] — A property that R(t) exhibits by increasing only when work is present
- [[Finish Number (F)]] — The virtual completion time assigned to a packet, compared against R(t)
- [[Round-Robin Service]] — The base scheduling discipline that R(t) measures progress of

## See Also

- [[Weighted Fair Queuing (WFQ)]]
- [[Generalized Processor Sharing (GPS)]]
- [[Packet-by-Packet Fair Queuing (PGPS)]]
- [[Earliest Deadline First (EDF)]]