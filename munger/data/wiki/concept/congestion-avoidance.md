>    Equipment       

# Congestion Avoidance Equipment

## Definition

**Congestion avoidance** is a set of mechanisms used in computer networks to prevent data traffic from exceeding the capacity of network links or switching equipment. It is distinct from congestion control (which reacts after congestion has occurred) in that it proactively monitors network load and reduces the sending rate or discards packets before the network becomes saturated. The term "congestion avoidance equipment" refers to the hardware devices—such as routers, switches, and dedicated traffic shapers—that implement these algorithms to maintain stable throughput and low latency.

In a broader sense, congestion avoidance can also be applied to any system of shared resources (e.g., CPU scheduling, memory allocation, supply chains) where equipment or infrastructure must be managed to prevent overload.

## Examples

### Network Equipment Implementing Congestion Avoidance
- **Routers with Active Queue Management (AQM)** – Devices that use algorithms like RED (Random Early Detection) or CoDel (Controlled Delay) to drop packets before buffers fill completely. This prevents [[Bufferbloat]] and reduces latency.
- **Traffic Shapers** – Specialized appliances (e.g., from vendors like Cisco, Juniper, or open-source tools on Linux) that enforce rate limits using token bucket or leaky bucket algorithms.
- **TCP Offload Engines (TOE)** – Network interface cards that handle TCP congestion avoidance (e.g., TCP Reno, Cubic) in hardware to free up CPU cycles.

### Non-Network Examples
- **Factory Production Lines** – Equipment that monitors work-in-progress inventory and slows down input conveyor belts to avoid jams.
- **Data Center Power Distribution** – Power distribution units (PDUs) that throttle non-critical loads when total current approaches equipment limits.

## Related Mental Models

- [[Leaky Bucket]] – A traffic shaping model where packets are buffered and released at a constant rate; used by many congestion avoidance devices.
- [[Token Bucket]] – Allows bursts up to a certain size while enforcing a long-term average rate; common in QoS equipment.
- [[Exponential Backoff]] – A delay-based approach used in Ethernet (CSMA/CD) and TCP retransmission; a form of congestion avoidance for shared media.
- [[Bufferbloat]] – The negative effects of oversized buffers in network equipment; congestion avoidance aims to mitigate this.
- [[TCP Congestion Control]] – The end‑to‑end algorithms (slow start, congestion avoidance, fast recovery) that work in concert with equipment-level AQM.
- [[Hysteresis]] – Using different thresholds for entering and exiting a congested state to avoid oscillation; often implemented in equipment firmware.
- [[Pacing]] – Deliberately spacing out packet transmissions to avoid bursts that trigger congestion; supported by some network interface equipment.

## See Also

- [[Active Queue Management]]
- [[Quality of Service]]
- [[Traffic Shaping]]
- [[Network Scheduler]]
- [[Bandwidth Throttling]]