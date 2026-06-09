# Network Attachment Points

## Definition
**Network Attachment Points** (NAPs) are the physical or logical interfaces where a [[Node (computing)|node]] connects to a [[Computer Network]]. In foundational networking architecture, NAPs represent the exact demarcation lines or "ports" where end systems attach to the transmission medium. As formally noted in [[RFC 1498]], the term [[Network Address]] in many data communication contexts specifically serves as an identifier for a network attachment point, rather than for the device itself, the service running on it, or the communication path. NAPs act as the fundamental anchors for [[Addressing]], [[Routing]], and [[Binding]] within layered network models.

## Historical Context
The concept was systematically categorized by Jerome H. Saltzer in [[RFC 1498]] (*On the Naming and Binding of Network Destinations*, August 1993). Saltzer abstracted network architecture into four primary object types to clarify naming and binding:
1. **Services and Users**: Functions provided and the clients that consume them.
2. **Nodes**: Computers that run services, act as clients, or implement network forwarding.
3. **Network Attachment Points**: The network ports/interfaces where nodes physically or logically attach.
4. **Paths**: Routes traversing forwarding nodes and communication links between attachment points.

This framework deliberately separates *where* communication terminates (the attachment point) from *what* is communicating (the node/service) and *how* data travels (the path).

## Examples
Network attachment points exist at multiple layers of abstraction, each with its own scope and identifier:
* **Physical Layer**: RJ-45 Ethernet jacks, SFP+ fiber optic transceivers, cellular modem antennas, or Wi-Fi radio interfaces.
* **Data Link Layer**: A [[MAC Address]] assigned to a [[Network Interface Controller]] (NIC), identifying the attachment point on a local link.
* **Network Layer**: An [[IPv4 Address]] or [[IPv6 Address]] bound to a specific interface, defining a globally or locally routable attachment point.
* **Transport Layer**: A [[Socket (networking)]] endpoint, formed by combining an IP address with a [[Port (computer networking)|port number]] to distinguish between concurrent services on the same node.
* **Logical/Virtual**: [[Tunnel Endpoint]]s, [[VLAN]] sub-interfaces, [[Loopback Interface]]s, or [[Cloud Computing|virtual machine]] vNICs that function as software-defined attachment points.

## Related Mental Models
Understanding NAPs is essential for network design, troubleshooting, and protocol development. Several mental models help conceptualize their role in modern systems:

* **Locator vs. Identity**: A network attachment point is fundamentally a *locator* (indicating *where* data should be delivered) rather than an *identity* (indicating *who* or *what* should receive it). This separation becomes critical in [[Mobile IP]], [[NAT|Network Address Translation]], and [[Anycast Routing]], where the same logical service migrates across different attachment points.
* **Binding and Resolution**: The relationship between a [[Service]] or [[User]] and a NAP is established through *binding*. Higher-level names (like hostnames) are resolved to NAP identifiers (like IP addresses), which are then mapped to physical data-link identifiers (like MAC addresses) via protocols such as [[ARP]] or [[Neighbor Discovery Protocol]].
* **Layered Scope**: NAPs operate at different layers of the [[OSI Model]] or [[TCP/IP Model]], each defining a different scope of reachability. A MAC address defines a link-local attachment point, while an IP address defines an internetwork-attachable point. Recognizing this scope prevents routing and switching confusion.
* **Endpoint vs. Transit**: In network topology, NAPs represent the *endpoints* of communication. This contrasts with [[Forwarding Node]]s (routers and switches) that intermediate traffic, and [[Network Path]]s that describe the traversal between endpoints.
* **Namespace & Topology**: The structure of NAP identifiers (flat vs. hierarchical) directly impacts [[Routing Protocols]], [[Subnetting]], and [[Address Allocation]] strategies. Hierarchical NAPs (like IP prefixes) enable scalable routing, while flat NAPs (like traditional MACs) require different forwarding and bridging mechanisms.

## See Also
* [[Network Address]]
* [[Endpoint (networking)]]
* [[Binding (computing)]]
* [[Jerome H. Saltzer]]
* [[RFC 1498]]
* [[Layered Network Architecture]]
* [[Address Resolution Protocol]]
* [[Network Topology]]
* [[Socket (networking)]]