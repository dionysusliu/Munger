# FTP (File Transfer Protocol)

## Definition

**File Transfer Protocol (FTP)** is a standard network protocol used for transferring files between a client and a server over a TCP/IP network. It typically operates on port 21 for control commands and port 20 for data transfer.

In network modeling and simulation (e.g., ns-2, ns-3), FTP is often abstracted as a **greedy traffic source** that continuously generates data as fast as the underlying transport protocol (usually TCP) allows. Key characteristics of this model include:

- **Infinite supply of 1000‑byte packets** – the source always has data to send, packetized into fixed‑size segments (often 1000 bytes, including headers).
- **Window‑based control** – the source uses a congestion window `W` to regulate packet generation. `W` evolves according to the congestion control algorithm (e.g., TCP Reno, CUBIC).
- **Bandwidth competition** – when multiple FTP sources share a bottleneck link, they compete for bandwidth, leading to queue buildup, packet drops, and throughput oscillations.
- **Synchronization effects** – under certain conditions (e.g., tail‑drop queues), FTP sources may synchronize their window reductions, causing periodic underutilization. More complex behaviors (e.g., phase effects, desynchronization) emerge with different queue management schemes (RED, CoDel) or heterogeneous round‑trip times.

Thus, in the context of performance analysis, “FTP” often refers to a **long‑lived, bulk‑data transfer source** that exhibits the dynamics of TCP congestion control.

## Examples

- **Real‑world FTP client** – downloading a large ISO file from a public FTP server. The client uses TCP, and the server sends data as fast as the window allows.
- **Simulation scenario** – a dumbbell topology with two FTP sources sharing a 10 Mbps bottleneck link. Each source sends 1000‑byte packets with an infinite backlog. The simulation tracks queue length, throughput, and window evolution over time.
- **Hybrid traffic** – combining an FTP source (bulk transfer) with a [[Web Browsing]] or [[VoIP]] source to study how interactive traffic is affected by background large flows.

## Related Mental Models

- [[TCP Congestion Control]] – the core mechanism that governs window evolution (`W`), using additive increase / multiplicative decrease (AIMD).
- [[Additive Increase Multiplicative Decrease (AIMD)]] – the mathematical model behind TCP Reno, directly shaping FTP source behavior.
- [[Queueing Theory]] – used to analyze buffer occupancy, packet loss, and delay when multiple FTP sources compete.
- [[Bandwidth-Delay Product]] – defines the optimal window size for a single FTP flow; exceeding it leads to queue buildup.
- [[Synchronization and Phase Effects]] – explains how multiple FTP sources can lock into synchronous window oscillations, and how active queue management (AQM) can break this synchronization.
- [[Active Queue Management (AQM)]] – techniques like RED or CoDel that prevent synchronization and improve fairness among FTP flows.
- [[Traffic Modeling]] – broader framework for representing network sources, including FTP, Pareto, and Markovian models.

## See Also

- [[FTP vs HTTP for File Transfer]]
- [[TCP Throughput Formula]]
- [[ns-2 FTP Application]]