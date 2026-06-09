# Nodes

In the context of [[Data Communication Networks]] and [[Network Architecture]], a **node** is a computing entity capable of executing services, applications, or system-level programs. Nodes serve as the active participants in a network, functioning either as endpoints that consume or provide services, or as intermediate devices that facilitate data forwarding, routing, and network management.

The concept is formally characterized in [[RFC 1498]], which distinguishes nodes from other network destination types such as services, network attachment points, and paths. In this framework, nodes are treated as the fundamental computational units that host software and interact with the underlying transport infrastructure.

## Key Characteristics
- **Computational Agency:** Nodes possess processing capability and can run user programs, background daemons, or protocol stacks.
- **Role Fluidity:** A node may operate as a [[Client]] (requesting services), a [[Server]] (providing services), or an infrastructure component (executing [[Forwarding]] or [[Routing]] logic). These roles are not mutually exclusive.
- **Abstraction Boundary:** Nodes are conceptually separated from their physical interfaces ([[Network Attachment Points]]) and the logical routes ([[Paths]]) that connect them.
- **Identity & Naming:** Each node requires one or more identifiers (e.g., hostnames, [[IP Addresses]], [[MAC Addresses]]) to enable [[Addressing]], discovery, and service binding.
- **Statefulness:** Nodes maintain local state (memory, file systems, session data) that persists across network interactions, distinguishing them from stateless forwarding elements in some architectures.

## Examples
- **End-User Devices:** [[Desktop Computers]], [[Laptops]], [[Smartphones]], and [[IoT Devices]] running client applications
- **Service Hosts:** [[Web Servers]], [[Database Instances]], [[Time Synchronization Servers]], and [[Authentication Providers]]
- **Network Infrastructure:** [[Routers]], [[Layer 3 Switches]], [[Firewalls]], and [[Load Balancers]] executing packet forwarding services
- **Cloud & Distributed Units:** [[Virtual Machines]], [[Containers]], [[Kubernetes Pods]], and [[Edge Nodes]] in modern [[Distributed Systems]]

## Related Mental Models
- **[[Graph Theory]]:** Nodes (vertices) represent discrete entities connected by edges (links). This model underpins [[Network Topology]] mapping, shortest-path routing, and resilience analysis.
- **[[Client-Server Architecture]]:** Frames nodes by their functional relationship (requester vs. provider), though modern [[Microservices]] and [[Peer-to-Peer]] models treat nodes as interchangeable, role-agnostic participants.
- **[[Abstract Data Types (ADT)]]:** As highlighted in RFC 1498, classifying network destinations (services, nodes, attachment points, paths) borrows from ADT principles. Nodes are modeled as encapsulated objects with defined interfaces, state, and behavior.
- **[[Layered Protocol Model]]:** In [[OSI Model]] or [[TCP/IP]], nodes operate across multiple abstraction layers, from physical hardware to application logic, with each layer exposing specific node capabilities.
- **[[Distributed Consensus]]:** In systems like [[Blockchain]] or [[Distributed Databases]], nodes are voting/computing participants that must synchronize state despite [[Network Partitioning]] or latency.

## See Also
- [[Network Attachment Points]]
- [[Services and Users]]
- [[Paths (Networking)]]
- [[Addressing and Naming]]
- [[Forwarding Services]]
- [[Network Topology]]
- [[Distributed Systems]]

## References
- Saltzer, J. H. (1993). *RFC 1498: On the Naming and Binding of Network Destinations*. Internet Engineering Task Force.
- Tanenbaum, A. S., & Wetherall, D. J. (2011). *Computer Networks* (5th ed.). Pearson.
- Kurose, J. F., & Ross, K. W. (2021). *Computer Networking: A Top-Down Approach* (8th ed.). Pearson.
- Lamport, L. (1978). *Time, Clocks, and the Ordering of Events in a Distributed System*. Communications of the ACM.