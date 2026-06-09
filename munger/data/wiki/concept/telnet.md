#Telnet

**Telnet** is a network protocol that provides bidirectional, interactive text-oriented communication using a virtual terminal connection. It is commonly used for remote terminal access to servers, routers, and other network devices. In the context of gateway performance and traffic analysis, Telnet is characterized as an **interactive packet source** that generates small, sporadic packets (typically 40 bytes) and is sensitive to delays and packet loss under overload conditions. It is also referenced in discussions of traffic quantity and policy enforcement.

## Definition

- **Protocol**: Telnet (RFC 854) operates over TCP port 23, providing a command-line interface for remote login.
- **Packet characteristics**: As an interactive source, it transmits short bursts of data (e.g., keystrokes) resulting in small packets (often 40 bytes, including TCP/IP headers).
- **Behavior under overload**: When network gateways become congested, Telnet sessions experience increased latency and packet drops, degrading the user experience.
- **Relevance to policy**: Telnet traffic is often subject to **quantity** (bandwidth limits) and **policy** (access control, prioritization) rules in network management.

## Examples

- A system administrator uses Telnet to log into a remote router and issue commands. Each keystroke generates a 40-byte packet.
- In a gateway simulation, Telnet is modeled as a low-bandwidth, delay-sensitive traffic source alongside bulk data transfers like FTP.
- Network policies might prioritize Telnet traffic over downloads to maintain responsiveness, or block Telnet due to security concerns (e.g., lack of encryption).

## Related Mental Models

- [[Interactive vs Bulk Traffic]] – Telnet represents interactive traffic, which is bursty and latency-sensitive, contrasting with bulk flows.
- [[Packet Loss]] – Under overload, Telnet packets are dropped, leading to retransmissions and noticeable lag.
- [[Quality of Service (QoS)]] – Mechanisms like prioritization and shaping are applied to protect Telnet’s performance.
- [[Gateway Congestion]] – The gateway becomes a bottleneck where Telnet’s small packets can be delayed or discarded.
- [[Policy-Based Routing]] – Rules that direct or limit Telnet traffic based on source, destination, or time.
- [[Small Packet Problem]] – The overhead of many tiny packets can consume gateway processing resources.

## See Also

- [[Telnet Protocol]] (technical details)
- [[Remote Terminal Access]]
- [[Secure Shell (SSH)]] – encrypted alternative to Telnet
- [[Traffic Shaping]]
- [[Network Simulation]]