# 5 [Saltzer82a] On the naming and binding of network destinations.pdf

## Overview
[[RFC 1498]] resolves longstanding confusion in network naming by adapting the operating system concept of [[binding (computing)]] to distributed networking. The paper establishes that network architectural clarity is achieved not through rigid name formats, but through dynamic, layered bindings between distinct destination objects.

## Core Framework
The author argues that **object identity**, **naming syntax**, and **dynamic resolution** must be strictly decoupled. Key premises include:
- Name formats (e.g., strings, binaries, hierarchical, flat) are syntactically independent of the underlying object types and should not be conflated.
- Network clarity emerges from **dynamic bindings** between conceptual layers.
- Bindings are inherently **layered** and **mutable**; changes at lower levels (e.g., routing paths or physical attachments) do not alter the fundamental identity of a [[Service/User]].

## Destination Object Types
The model categorizes network destinations into four distinct conceptual objects:
1. **[[Service/User]]**: The application-level entity requesting or providing data.
2. **[[Node]]**: The logical or physical computing host.
3. **[[Network Attachment Point]]**: The specific interface or endpoint connecting a node to the network fabric.
4. **[[Path]]**: The sequence of network links and switches used to forward traffic.

> **Note:** The paper emphasizes that naming syntax is orthogonal to these object types. A single format can reference any object depending on the resolution context.

## Sequential Binding & Resolution Process
Delivering a packet requires resolving three sequential bindings, each mapping directly to a core network function:

| Binding Sequence | Network Function | Purpose |
|---|---|---|
| `[[Service]] → [[Node]]` | [[Service Name Resolution]] | Maps a logical service identifier to a specific computing host. |
| `[[Node]] → [[Network Attachment Point]]` | [[Node Location]] | Determines the physical/logical interface where the host connects to the network. |
| `[[Network Attachment Point]] → [[Path]]` | [[Routing]] | Selects the optimal sequence of network segments for packet forwarding. |

## Design Principles & Architectural Warnings
Based on this binding model, the paper outlines critical guidelines for network designers:
- **Avoid Hardcoded/Static Bindings**: Static mappings reduce system flexibility, hinder fault tolerance, and complicate network evolution.
- **Do Not Assume Fixed Name Formats**: Naming syntax must remain agnostic to the underlying resolution mechanism.
- **Embrace Mutability**: Architectures must support dynamic rebinding (e.g., during failover, mobility, or load balancing) without breaking higher-layer service identities.
- **Maintain Layer Independence**: Each binding layer should operate with minimal assumptions about adjacent layers to preserve modularity.

## Significance & Legacy
By decoupling object identity, naming syntax, and dynamic resolution, this framework provides a flexible, systematic model for understanding and architecting [[Network Destination Naming]] and [[Routing]]. Its principles have directly influenced:
- Modern [[Name Resolution Protocols]] (e.g., DNS, distributed directories)
- The [[End-to-End Principle]] and layered network stack design
- Contemporary mobility frameworks and [[Software-Defined Networking]] (SDN) architectures

## See Also
- [[RFC 1498]]
- [[Network Architecture]]
- [[Name Resolution]]
- [[Routing]]
- [[Binding (Computing)]]
- [[Layered Protocol Design]]

## References
- Saltzer, J. H. (1982). *On the Naming and Binding of Network Destinations*.
- [[RFC 1498]]: "On the naming and binding of network destinations" (FYI RFC, formalizing the foundational 1982 research).