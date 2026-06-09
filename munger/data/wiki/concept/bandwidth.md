# Bandwidth

**Definition:** Bandwidth refers to the maximum rate of data transfer across a given path or network connection, typically measured in bits per second (bps). In computing and networking, bandwidth represents the capacity of a communication channel—the amount of data that can be transmitted in a fixed amount of time. Beyond its technical meaning, "bandwidth" is also used metaphorically in cognitive science and productivity contexts to describe a person's mental capacity to process information or handle tasks.

---

## Examples

### Technical Examples
- **Internet Connection:** A fiber optic connection with 1 Gbps bandwidth can download a 1 GB file in approximately 8 seconds, while a 10 Mbps DSL connection would take over 13 minutes.
- **Network Queue Management:** Using [[Round-Robin Scheduling]], a router allocates bandwidth fairly among competing data flows. Each flow gets an equal turn to transmit packets, preventing any single flow from monopolizing the channel.
- **Wi-Fi Channels:** A 20 MHz Wi-Fi channel offers roughly 433 Mbps bandwidth (802.11ac), while a 160 MHz bonded channel can provide up to 3.5 Gbps.

### Metaphorical Examples
- **Cognitive Bandwidth:** A manager overwhelmed with 15 simultaneous Slack conversations has reduced cognitive bandwidth for strategic thinking.
- **Team Capacity:** A software team working on three critical projects simultaneously may lack bandwidth to handle urgent bug fixes.

---

## Related Mental Models

### [[Round-Robin Scheduling]]
A queueing algorithm where each competing flow receives an equal, sequential allocation of transmission opportunities. This ensures fair bandwidth distribution among multiple users or processes. For example, in a router handling 10 active connections, each connection gets a turn to send one packet before returning to the start of the queue.

### [[The Queueing Theory]]
Mathematical study of waiting lines. Bandwidth allocation directly influences queue depth and latency. Higher bandwidth reduces queue buildup, while insufficient bandwidth causes congestion and packet drops.

### [[Parkinson's Law]]
Work expands to fill available time. Similarly, data transmission often expands to fill available bandwidth—a phenomenon known as "bandwidth elasticity." Adding bandwidth may not always improve performance if the bottleneck lies elsewhere (e.g., server processing power).

### [[The Bottleneck]]
The slowest component in a system determines overall throughput. Bandwidth is often a bottleneck in network performance, but other factors like latency, packet loss, and processing speed can become limiting even with ample bandwidth.

### [[Cognitive Load Theory]]
Related to mental bandwidth: the amount of working memory resources available for processing information. When cognitive bandwidth is exceeded, learning and decision-making degrade.

### [[The Tragedy of the Commons]]
Without fair allocation mechanisms like [[Round-Robin Scheduling]], shared bandwidth can be overconsumed by aggressive users, degrading experience for everyone.

---

## Key Takeaways
- Bandwidth is a measure of capacity, not speed—it determines how much data can flow, not how fast each packet travels.
- Fair allocation methods like round-robin prevent starvation and ensure equitable resource distribution.
- "Bandwidth" applies both to technical systems and human cognition, highlighting universal constraints on throughput.
- Increasing bandwidth alone rarely solves performance problems if other bottlenecks (latency, processing power) remain unaddressed.

---

**See also:** [[Latency]], [[Throughput]], [[Packet Switching]], [[Congestion Control]], [[Quality of Service]]