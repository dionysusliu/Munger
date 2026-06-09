# F_i^a

**F_i^a** (also known as the *virtual finish time* or *finishing number*) is a key scheduling parameter used in packet-by-packet transmission algorithms, particularly in [[Fair Queuing]] and [[Packet-by-Packet GPS]] (PGPS). It determines the order in which packets from different conversations (flows) are transmitted from a network node.

## Definition

For packet \(i\) of conversation (or flow) \(a\), the finishing number \(F_i^a\) is defined as the sum of its virtual start time and the packet size:

\[
F_i^a = S_i^a + P_i^a
\]

where:
- \(S_i^a\) is the **virtual start time**: the time at which the packet would begin transmission in an idealised fluid-flow (Generalised Processor Sharing, [[GPS]]) system.
- \(P_i^a\) is the **packet size** (expressed in bits, bytes, or in the same unit as the virtual time).

Packets are transmitted in **increasing order** of \(F_i^a\). A smaller finishing number indicates higher priority.

## Example

Consider two conversations, A and B, with the following backlog:

| Conversation | Packet | Size (bytes) | Virtual Start Time \(S\) | Finishing Number \(F = S + P\) |
|--------------|--------|--------------|--------------------------|--------------------------------|
| A            | p1     | 100          | 100                      | 200                            |
| A            | p2     | 200          | 200                      | 400                            |
| B            | q1     | 150          | 50                       | 200                            |

In this example:
- Both p1 and q1 have \(F = 200\). Tie-breaking rules (e.g., conversation index or round-robin) apply.
- p2 has \(F = 400\) and will be transmitted after both p1 and q1.

## Usage in Scheduling Algorithms

- In [[Weighted Fair Queuing]] (WFQ), each backlogged flow has a virtual clock; the finishing number corresponds to the timestamp on the packet.
- In [[Virtual Clock]] scheduling, each packet is assigned a *virtual finishing time* computed similarly, and the node transmits the packet with the smallest timestamp.
- The concept is derived from [[Generalised Processor Sharing]] (GPS) and its packetised approximation, PGPS.

## Related Mental Models

- [[Fair Queuing]] – Aligns the finishing-number order with GPS fluid-flow fairness.
- [[Leaky Bucket]] – Used to enforce traffic shaping; finishing numbers often incorporate arrival times shaped by leaky bucket constraints.
- [[Token Bucket]] – The relationship between packet arrival, token count, and virtual time can influence \(S_i^a\).
- [[Earliest Deadline First]] (EDF) – A different scheduling model using real time deadlines; conceptually similar to ordering by finish time.

## See Also

- [[S_i^a]]
- [[Virtual Time]]
- [[Packet-by-Packet GPS]]

> **Note:** Finishing numbers are usually computed incrementally as packets arrive and depart; the exact implementation depends on the specific scheduling discipline and the definition of virtual time (e.g., system virtual time vs. flow-specific virtual time).