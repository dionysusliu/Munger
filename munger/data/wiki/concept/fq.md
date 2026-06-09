# Fair Queuing (FQ)

**Fair Queuing** is a network scheduling discipline designed to allocate bandwidth equitably among competing traffic flows. By maintaining separate queues for each flow and servicing them in a round-robin or weighted round-robin fashion, FQ prevents any single connection from monopolizing link capacity while ensuring low latency for interactive applications like VoIP or online gaming.

## Definition

Fair Queuing (also known as per-flow queuing) is a queuing algorithm that:
- Creates a distinct FIFO (First-In, First-Out) queue for each traffic flow.
- Services these queues in a round-robin manner, giving each flow an equal opportunity to transmit.
- Optionally applies weights to flows to provide differentiated service levels (Weighted Fair Queuing, WFQ).

The key principle is **max-min fairness**: no flow should receive more bandwidth than any other unless excess capacity remains after satisfying all flows' minimum requirements.

## Examples

### Example 1: Home Router with Multiple Users
- **Scenario**: A household has 4 people streaming video, browsing, and gaming on a 100 Mbps connection.
- **Without FQ**: A single large download (e.g., a game update) could consume all bandwidth, causing video buffering and lag.
- **With FQ**: The router assigns separate queues to each device or flow. Each queue gets ~25 Mbps, preventing one user from starving others.

### Example 2: Data Center Traffic
- **Scenario**: A server handles hundreds of TCP connections, including bulk data transfers and latency-sensitive queries.
- **Without FQ**: Long-lived TCP flows (e.g., backups) fill the buffer, causing packet drops for short queries.
- **With FQ**: Each connection gets a fair share, so interactive queries experience minimal delay.

### Example 3: Quality of Service (QoS) in VoIP
- **Scenario**: A network carries both voice calls and file downloads.
- **With Weighted Fair Queuing**: Voice packets are assigned higher weight, ensuring they are served promptly even during heavy file transfers.

## Related Mental Models

- **[[Bufferbloat]]**: FQ is a primary mitigation strategy against bufferbloat, where excessive buffering in routers causes high latency.
- **[[Traffic Shaping]]**: Unlike traffic shaping (which limits total bandwidth), FQ focuses on equitable distribution among flows.
- **[[Latency vs. Throughput Tradeoff]]**: FQ prioritizes low latency for interactive flows, sometimes at the cost of slightly reduced throughput for bulk transfers.
- **[[TCP Congestion Control]]**: FQ complements TCP algorithms like CUBIC or BBR by preventing one TCP flow from unfairly dominating others.
- **[[Pareto Efficiency]]**: In networking, fair queuing aims for a Pareto-optimal allocation where no flow can improve its throughput without harming another.

## Key Characteristics

- **Isolation**: Misbehaving or aggressive flows cannot degrade service for well-behaved flows.
- **Low Latency**: Interactive flows (e.g., SSH, VoIP) experience minimal queueing delay.
- **Fairness**: Each flow receives bandwidth proportional to its weight (default: equal shares).
- **Complexity**: Requires per-flow state management, which can be resource-intensive on high-speed links.

## Practical Implementations

- **FQ-CoDel** (Fair Queuing with Controlled Delay): Combines FQ with active queue management (CoDel) to limit bufferbloat.
- **CAKE** (Common Applications Kept Enhanced): A Linux queuing discipline that integrates FQ, bandwidth shaping, and DiffServ.
- **Weighted Fair Queuing (WFQ)**: Used in Cisco routers to assign different weights to traffic classes.

## Limitations

- **Scalability**: Maintaining per-flow queues becomes expensive as the number of flows grows (e.g., in core routers).
- **State Overhead**: Requires memory to track flow states, which can be problematic in high-speed hardware.
- **Burst Sensitivity**: Pure round-robin can be inefficient for bursty traffic; variants like Deficit Round Robin (DRR) address this.

## See Also

- [[Active Queue Management (AQM)]]
- [[DiffServ (Differentiated Services)]]
- [[Network Congestion]]
- [[Quality of Service (QoS)]]