# Binding

## Definition
**Binding** is the process of establishing a correspondence between a symbolic name, identifier, or reference and a concrete entity, resource, or location within a system. In computer science, it determines *when*, *where*, and *how* an abstract label is resolved to a specific implementation, address, or value. The concept is foundational across [[Operating System]] design, [[Programming Language]] semantics, and [[Computer Network]] architecture, where it governs the mapping between logical abstractions and physical or executable targets.

## Key Characteristics
- **Timing**: Binding may occur **early** (static, at compile/link time) or **late** (dynamic, at runtime).
- **Scope & Context**: Bindings are often environment-dependent, varying by process, session, user, or network topology.
- **Mutability**: A binding can be immutable (fixed for the lifetime of a reference) or mutable (reassigned, refreshed, or revoked dynamically).
- **Resolution**: The act of dereferencing a name to retrieve its currently bound value, typically involving lookup tables, caches, or directory services.
- **Indirection**: Binding inherently introduces a level of indirection, decoupling references from implementations to enable flexibility and evolution.

## Examples
- **Networking & Routing**: As outlined in RFC 1498, network destinations involve layered bindings. A human-readable [[Domain Name System]] (DNS) hostname is bound to an [[IP Address]], which is further bound to a [[MAC Address]] on a local link, and ultimately to a physical network interface. Late binding in routing allows packets to adapt to topology changes without requiring senders to know the final destination path.
- **Programming Languages**: In [[Python]] or [[JavaScript]], variable names are bound to objects at assignment time (late binding). In [[C]] or [[Rust]], function calls are typically early-bound during compilation, though [[Virtual Function]]s in [[C++]] and [[Java]] use runtime dispatch tables (vtables) for late binding.
- **Operating Systems**: File paths are bound to filesystem inodes or NTFS records. [[Symbolic Link]]s and [[Mount Point]]s represent deferred bindings resolved only when accessed.
- **Security & Identity**: A user principal name is bound to a cryptographic key pair or access control list (ACL) during authentication, enabling [[Zero Trust]] architectures to enforce context-aware policies.

## Related Mental Models
- `[[Name Resolution]]`: The operational counterpart to binding; focuses on the lookup mechanism used to retrieve the current bound value rather than the establishment of the mapping itself.
- `[[Abstraction Layer]]`: Binding typically occurs at layer boundaries, translating high-level semantic concepts into low-level executable instructions or physical addresses.
- `[[Indirection]]`: Recognizes that binding is a deliberate detour that trades direct access for flexibility, versioning, and fault tolerance.
- `[[Late vs Early Binding]]`: A fundamental engineering trade-off between performance/predictability (early) and adaptability/polymorphism (late).
- `[[Contextual Mapping]]`: The understanding that the same identifier may bind to different entities depending on environment, time, or policy (e.g., DNS geo-routing, session-scoped variables).
- `[[Stateful Routing]]`: In distributed systems, binding decisions often carry implicit or explicit state, meaning the same name may resolve differently across retries or network partitions.

## References & Further Reading
- Saltzer, J. (1993). *[RFC 1498: On the Naming and Binding of Network Destinations](https://www.rfc-editor.org/rfc/rfc1498)*. MIT Laboratory for Computer Science.
- [[Compiler Design]]
- [[Distributed Systems]]
- [[Resource Locator]]
- [[Dynamic Linking]]