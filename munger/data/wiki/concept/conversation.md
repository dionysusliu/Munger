# Conversation

A **conversation** refers to a logical communication session identified by a unique **[[Source-Destination Pair]]**. In packet-switched networks, conversations serve as the fundamental unit for bandwidth allocation and fair sharing of link capacity. Each conversation is treated as an independent flow that competes for resources, and scheduling disciplines ensure that active conversations receive their fair share according to a defined policy (e.g., [[Round-Robin Scheduling]]).

## Definition

A conversation is defined by the tuple `(source address, destination address)` and optionally includes protocol/port information for finer granularity. It represents a stream of packets that belong to the same end-to-end communication instance (e.g., a TCP connection or a UDP stream).

### Active Condition

A conversation is considered **active** when it has at least one packet waiting for transmission. In precise scheduling algorithms (such as [[Fair Queuing]] or [[Virtual Clock]]), the active state is expressed using a system-wide virtual time function \( R(t) \) and per-packet tags:

- **Primary condition**: A conversation is active if \( R(t) \ge S_F \) for \( i = \max(j \mid t_j^a \le t) \), where:
  - \( S_F \) is the start tag of the conversation’s current packet.
  - \( t_j^a \) are the arrival times of packets from the conversation.
  - The index \( i \) selects the most recent packet arrival before time \( t \).

- **Alternative condition**: A conversation is active if there exists a packet (identified by index \( a \)) such that \( R(t) \le F_i^a \), where \( F_i^a \) is the finish tag of that packet. This captures the idea that the packet’s virtual finish time has not yet been reached.

These conditions ensure that only conversations with outstanding packets are serviced, and that each receives its fair share of bandwidth according to the scheduling discipline.

## Examples

- **TCP Connection**: A client and server exchanging data over a TCP socket form a single conversation. The scheduler allocates bandwidth to this conversation based on its queue length and the fair share policy.
- **UDP Stream**: A real‑time video stream from a camera to a monitoring station is a conversation. Even though UDP is connectionless, the source‑destination pair defines the flow.
- **VoIP Call**: A bidirectional voice conversation between two endpoints. Each direction may be treated as a separate conversation or combined using symmetric hashing.

## Related Mental Models

- **[[Fair Queuing]]**: Conversations are placed into separate queues; the scheduler visits queues in a round‑robin fashion, ensuring that each active conversation gets an equal share of the link.
- **[[Round-Robin Scheduling]]**: A simple discipline where active conversations are serviced one packet at a time in cyclic order. The condition for activity (having a packet to send) determines participation.
- **[[Virtual Time]]**: A continuous function \( R(t) \) that tracks the progress of the scheduler. Conversations use start and finish tags computed from packet lengths and virtual time to enforce fairness.
- **Flow Isolation**: Conversations are isolated from each other so that a misbehaving or high‑rate flow cannot starve others. This is a core goal of bandwidth allocation based on conversations.
- **[[Packet Scheduling]]**: The broader field that includes algorithms like Weighted Fair Queuing (WFQ), Deficit Round Robin (DRR), and others that use conversation‑level state.

## Internal Links

- [[Source-Destination Pair]]
- [[Bandwidth Allocation]]
- [[Fair Queuing]]
- [[Round-Robin Scheduling]]
- [[Packet Scheduling]]
- [[Virtual Time]]
- [[Flow Isolation]]