# Malicious Source

A **malicious source** is any network entity (e.g., compromised device, botnet node, or intentionally programmed host) that consumes an unlimited amount of bandwidth by flooding multiple destinations with unwanted packets, thereby starving legitimate sources of network capacity. It acts unfairly, monopolizing shared resources and denying other participants fair access to the communication medium.

## Characteristics

- **Unlimited consumption**: Does not respect flow control or congestion signals.
- **Unwanted traffic**: Packets carry no useful payload for the receiver; often spoofed or amplified.
- **Multi-destination aggression**: Hits many targets simultaneously (e.g., distributed denial-of-service).
- **Resource monopolization**: Saturates links, switch buffers, or server connections.
- **Unfairness**: Violates principles of [[Cooperative Bandwidth Sharing]] and [[Network Neutrality]].

## Examples

1. **Botnet DDoS attack** – Thousands of compromised IoT devices send SYN floods to a single web server, exhausting its connection table.
2. **Amplification attack** – A malicious source sends small queries to open DNS resolvers with a forged victim IP, causing large responses directed at the victim.
3. **Bandwidth hogging malware** – A worm that spreads by scanning random IP addresses, consuming all available upstream capacity on an infected LAN.
4. **Intentional network sabotage** – An insider throttles all traffic to a competitor’s cloud service by constantly requesting large files.

## Related Mental Models

- [[Tragedy of the Commons]] – The malicious source overuses the shared “commons” of network bandwidth, causing degradation for all.
- [[Feedback Loop]] – No negative feedback (e.g., packet drops) deters the source; instead, it may increase sending rate.
- [[Zero-Sum Game]] – Bandwidth is finite; the malicious source’s gain (throughput) forces equivalent loss on other sources.
- [[Prisoner’s Dilemma]] – If all sources cooperate, everyone benefits; one defector (malicious source) can ruin the system.
- [[Cascading Failure]] – A single malicious source can trigger congestion collapse across multiple routers.

## Countermeasures

- Rate limiting and traffic shaping (e.g., using [[Traffic Policing]]).
- Ingress filtering (e.g., [[BCP 38]] to prevent spoofed source addresses).
- [[Black Hole Routing]] to drop traffic from known malicious sources.
- Collaboration via [[DDoS Mitigation Services]] and [[Anycast Networks]].

## See Also

- [[Denial of Service Attack]]
- [[Bandwidth Hogging]]
- [[Distributed Denial of Service (DDoS)]]
- [[Spoofing Attack]]
- [[Congestion Collapse]]
- [[Fairness in Networking]]