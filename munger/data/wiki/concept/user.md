# Entity

**Entity** is a fundamental concept in networking, distributed systems, and communication protocols, referring to any identifiable object or actor that can send, receive, or process data. The interpretation of "entity" depends on the context and the level of abstraction, but it uniformly serves as the subject or object of communication.

## Definition

An entity represents a distinct, addressable unit within a system. It can be defined at various granularities:

- **Source-Destination Pairs**: Endpoints in a communication channel (e.g., IP addresses + ports).
- **Conversations**: Logical interactions between two or more entities over time (e.g., TCP sessions).
- **Processes**: Active programs or threads on a host that generate or consume data.
- **Other abstractions**: Users, sessions, devices, or virtual machines.

The treatment (routing, filtering, logging, analytics) applied to an entity remains consistent across these interpretations.

## Associated with Packets

In packet-switched networks, an entity may be represented by:

- **Source**: The origin of a packet (e.g., sender IP address).
- **Destination**: The target of a packet (e.g., receiver IP address).
- **Source-Destination Pair**: A flow identifier combining both addresses and ports.
- **Process on Source Host**: The specific application or OS-level process generating the packet (e.g., PID, socket descriptor).

## Examples

| Interpretation | Example |
|----------------|---------|
| Source-destination pair | (192.168.1.10:443 → 10.0.0.5:5000) in a firewall rule |
| Conversation | All HTTP requests/responses between a client and server during a session |
| Process | `httpd` (Apache) serving web traffic on port 80 |
| User | A logged-in user account (`jdoe`) whose traffic is being monitored |
| Device | A camera sending video streams to a recording server |

## Related Mental Models

- [[Flow]] – A sequence of packets sharing the same entity (e.g., source-destination pair), often used in network traffic analysis.
- [[Session]] – A higher-level conversation encapsulating multiple entities, with state management.
- [[Socket]] – A software abstraction representing an endpoint in network communication, binding IP and port.
- [[Identity]] – The unique label or credential associated with an entity (e.g., username, certificate).
- [[Principal]] – In security models, an entity that can be authenticated and authorized (e.g., user, service account).

## Applications

- **Network monitoring**: Classifying traffic by entity (source, destination, or pair) for bandwidth accounting or anomaly detection.
- **Access control**: Applying policies per entity (e.g., permit/deny based on source-destination pair).
- **Logging**: Recording entity information for audit trails (source IP, user, process ID).
- **Quality of Service (QoS)**: Prioritizing traffic by entity type (e.g., voice vs. bulk data conversations).

## See Also

- [[Packet]]
- [[Endpoint]]
- [[Communication Channel]]
- [[Abstraction Layer]]