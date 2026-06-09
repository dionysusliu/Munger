# Underloaded Gateway Scenario with 6 FTP and 2 Telnet Sources

## Definition

The **Underloaded Gateway Scenario with 6 FTP and 2 Telnet Sources** describes a network condition where a gateway or router is operating below its maximum capacity while handling traffic from 6 File Transfer Protocol (FTP) sources and 2 Telnet sources. This scenario is commonly studied in network simulation, traffic engineering, and quality of service (QoS) analysis.

In this configuration, the gateway has sufficient bandwidth and processing resources to handle all incoming traffic without significant queuing delays, packet loss, or congestion. The term "underloaded" indicates that the total offered load is less than the gateway's service capacity.

## Key Characteristics

- **Traffic Composition**: 6 FTP flows (typically bandwidth-intensive, bulk data transfers) + 2 Telnet flows (typically interactive, low-bandwidth but latency-sensitive)
- **Gateway State**: No congestion; queue lengths remain small or empty
- **Performance Metrics**: Low latency, zero or minimal packet loss, high throughput
- **Resource Utilization**: CPU, memory, and link bandwidth usage below 100%

## Examples

### Example 1: Simple Network Topology

```
[FTP Source 1] ----\
[FTP Source 2] -----\
[FTP Source 3] ------+--- [Gateway] --- [Destination Network]
[FTP Source 4] ------/
[FTP Source 5] -----/
[FTP Source 6] ----/
[Telnet Source 1] ---/
[Telnet Source 2] ---/
```

- **Scenario**: All 8 sources transmit simultaneously
- **Observation**: Gateway processes all packets immediately; no queuing delay
- **Application Performance**: FTP transfers achieve maximum throughput; Telnet sessions remain responsive

### Example 2: Simulation in ns-3 or OMNeT++

| Parameter | Value |
|-----------|-------|
| FTP Sources | 6 (each sending at 1 Mbps) |
| Telnet Sources | 2 (each sending at 100 Kbps) |
| Gateway Capacity | 10 Mbps |
| Total Offered Load | 6.2 Mbps |
| Utilization | 62% (underloaded) |

**Result**: No packet drops, average delay < 1 ms

## Related Mental Models

### [[Queueing Theory]]
The underloaded gateway scenario is a direct application of **Queueing Theory**, specifically the M/M/1 or M/D/1 queue models. When the arrival rate (λ) is less than the service rate (μ), the system remains stable and queues dissipate quickly.

### [[Traffic Shaping]]
Understanding underloaded conditions helps in designing [[Traffic Shaping]] policies that prioritize latency-sensitive traffic (like Telnet) even when the network is not congested.

### [[Congestion Avoidance]]
This scenario contrasts with [[Congestion Avoidance]] mechanisms (e.g., TCP Reno, Cubic) that activate only when the gateway becomes overloaded. Underloaded conditions require no active congestion control.

### [[Load Shedding]]
In underloaded scenarios, [[Load Shedding]] is unnecessary. However, knowledge of this baseline helps operators determine when load shedding should be triggered.

## Implications

- **Network Design**: Underloaded gateways provide headroom for traffic bursts
- **QoS Policy**: Even in underloaded conditions, prioritizing interactive traffic (Telnet) over bulk traffic (FTP) improves user experience
- **Capacity Planning**: This scenario serves as a baseline for determining when to upgrade gateway capacity

## See Also

- [[Network Congestion]]
- [[Quality of Service (QoS)]]
- [[TCP Flow Control]]
- [[Bufferbloat]]