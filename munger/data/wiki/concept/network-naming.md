# Network Naming

## Definition
**Network Naming** is a conceptual framework in computer networking that defines how entities are identified, tracked, and associated across dynamic network environments. Rather than treating names as static addresses, network naming treats them as persistent identities maintained through **bindings** between different types of network objects. The core principle is the decoupling of *identity* from *location*, allowing network components to move, scale, or reconfigure without losing their recognized names or operational continuity.

## Core Requirements
Effective network naming systems must satisfy three fundamental requirements centered on identity preservation:
1. **Service Mobility**: A service may run on one or more nodes and must retain its identity when migrated across them.
2. **Node Mobility**: A node may connect to multiple attachment points and must retain its identity when switching between them.
3. **Path Agility**: The connection between attachment points may change over time (e.g., routing updates, link failures) without affecting the identity of the endpoints.

## The Four Network Objects
Network naming architectures typically model systems using four primary object types:
- **Service**: A logical function or application capability (e.g., a database, web API, or file server).
- **Node**: A physical or virtual computing device that hosts one or more services.
- **Attachment Point**: A network interface, port, or logical endpoint where a node connects to the network fabric.
- **Path/Route**: The sequence of links, switches, or tunnels connecting two attachment points.

## Binding & Identity Preservation
In this framework, a *name* is not an address but a reference that points to a current binding. By maintaining associations as lists of bindings (e.g., `Service → Node → Attachment Point → Path`), the system can update underlying mappings without changing the public identifier. This indirection ensures that:
- Clients continue to use the same name regardless of backend or topology changes.
- Network state changes are handled at the binding layer, not the naming layer.
- Identity remains stable across maintenance windows, scaling events, or failures.

## Engineering Considerations
The degree of flexibility in a naming system is a deliberate design choice:
- **Static/Design-Time Bindings**: Fixed mappings established during network configuration. Simpler to manage, lower resolution latency, but inflexible.
- **Dynamic/Runtime Bindings**: Mappings updated automatically via protocols, registries, or control planes. Highly adaptable but introduces complexity, potential resolution delays, and consistency challenges.
- **Judgment Call**: Engineers must evaluate whether a particular binding *should* be mutable. Not all flexibility is beneficial; over-engineering dynamic resolution can harm performance, security, and debuggability.

## Examples
| Requirement | Real-World Implementation | How It Preserves Identity |
|---|---|---|
| Service moves across nodes | `[[Kubernetes Service]]` / `[[Service Discovery]]` | A stable DNS name or virtual IP routes to changing pod/node IPs via a control plane registry. |
| Node moves across attachment points | `[[Mobile IP]]` / `[[Virtual MAC]]` | A logical identifier remains constant while the physical uplink or underlying network interface changes. |
| Paths change between attachment points | `[[BGP]]` / `[[SDN]]` / `[[Anycast]]` | Endpoint addresses stay fixed while routing tables dynamically update paths based on congestion or failures. |

## Related Mental Models
- `[[Separation of Identity and Locator]]` – The foundational principle that what something *is* should be distinct from where it *is* (or how to reach it).
- `[[Indirection]]` – Using an intermediate mapping layer (registries, DNS, control planes) to resolve stable names to volatile locations.
- `[[Binding Time]]` – The stage (design, compile, load, runtime) at which a name-to-location association is established and whether it can be updated later.
- `[[Location Independence]]` – Architectural pattern enabling resources to be accessed without knowledge of their physical or logical placement.
- `[[Abstraction Layering]]` – Storing naming, routing, and delivery concerns in separate layers to manage complexity and enable independent evolution.

## References & Further Reading
- Sunshine, C. *Naming in Distributed Systems* [3] – Foundational review of network naming requirements, binding flexibility, and identity preservation.
- RFC 2775: *Internet Transparency* – Discusses how naming and addressing strategies impact network architecture and end-to-end principles.
- Saltzer, J. H., Reed, D. P., & Clark, D. D. *End-to-End Arguments in System Design* – Contextualizes where naming/bindings belong in layered architectures.
- `[[Distributed Systems]]` | `[[Network Architecture]]` | `[[Service Mesh]]`