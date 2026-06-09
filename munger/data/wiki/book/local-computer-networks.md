# Local Computer Networks

> **Status:** Informational Memo  
> This memo provides information for the [[Internet community]]. It does not specify an [[Internet standard]]. Distribution of this memo is unlimited.

## Abstract
This brief paper offers a perspective on the subject of names of destinations in [[Data Communication Networks]]. It suggests two ideas:
1. First, it is helpful to distinguish among four different kinds of objects that may be named as the destination of a [[Packet]] in a network.
2. Second, the [[Operating System]] concept of [[Binding]] is a useful way to describe the relations among the four kinds of objects.

To illustrate the usefulness of this approach, the paper interprets some more subtle and confusing properties of two real-world network systems for naming destinations.

## Publication History & Copyright
| Field | Details |
|-------|---------|
| **Original Publication** | "Local Computer Networks", edited by P. Ravasio et al. |
| **Publisher** | North-Holland Publishing Company, Amsterdam |
| **Year** | 1982 |
| **Pages** | 311–317 |
| **Copyright** | [[IFIP]], 1982 |
| **Funding** | [[DARPA]] (U.S. Government), monitored by the [[Office of Naval Research]] under contract N00014-75-C-0661 |

**Reproduction Notice:**  
Permission is granted by IFIP for reproduction for non-commercial purposes. Permission to copy without fee this document is granted provided that:
- The copies are not made or distributed for commercial advantage.
- The IFIP copyright notice, the title of the publication, and its date appear.
- Notice is given that copying is by permission of IFIP.

*To copy otherwise, or to republish, requires a specific permission.*

## What is the Problem?
De...  
*(Editor's Note: The source text provided is truncated at this point. The full section typically addresses the ambiguity between logical, physical, routing, and application-level identifiers in early network architectures.)*

## Core Concepts
Based on the abstract, the paper establishes several foundational principles for network design:
* **Destination Taxonomy:** Classification of the four object types that can serve as packet targets.
* **Layered Naming Separation:** Distinction between how endpoints are addressed at different protocol layers.
* **Dynamic vs. Static Mapping:** How [[Binding]] resolves names to actual network resources during runtime or configuration.

## See Also
* [[Network Addressing]]
* [[Name Resolution Protocols]]
* [[Layered Network Architecture]]
* [[History of Computer Networking]]
* [[RFC 822]] & [[RFC 1034]] (Historical naming/addressing standards)

## References
1. Ravasio, P., et al. (Eds.). (1982). *Local Computer Networks*. North-Holland Publishing Company. pp. 311–317.
2. IFIP (International Federation for Information Processing). (1982). Copyright & Reproduction Guidelines.
3. [[Internet Engineering Task Force|IETF]]. Informational Memo Distribution Policy.

---
[[Category:Computer Networking]]
[[Category:Network Architecture]]
[[Category:Historical Technical Papers]]
[[Category:IFIP Publications]]