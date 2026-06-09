>       

# Telnet-like Sources

## Definition

A **Telnet-like source** is any data source or interface that provides access to information or services with minimal abstraction, often requiring direct, text-based interaction and lacking modern security or usability features. The term draws an analogy to the Telnet protocol (RFC 854), which offered straightforward remote terminal access but with no encryption, limited authentication, and a bare‑bones user experience.

In modern contexts, Telnet-like sources are characterized by:
- **Low overhead**: No authentication, encryption, or session management
- **Text‑based**: Often plaintext, with structured data (e.g., CSV, JSON) embedded directly in the stream
- **Legacy compatibility**: May be maintained for backward compatibility or specific niche use cases
- **Implicit trust**: Relies on network‑level security or obscurity rather than application‑level safeguards

## Examples

- **Legacy database dumps** – Plaintext exports served via FTP or old HTTP endpoints  
- **Raw log streams** – Unstructured syslog or SNMP trap outputs  
- **Minimal REST APIs** – Endpoints returning data with no authentication (e.g., internal weather station data)  
- **Hardware serial consoles** – Devices exposing configuration menus over Telnet or raw TCP sockets  
- **Test or debugging interfaces** – Stubs or mock servers that accept anything and echo back simple responses

## Related Mental Models

- [[Leaky Abstractions]] – Telnet-like sources are a form of leaky abstraction, where underlying complexity is exposed directly to the user.
- [[Black Box]] – Unlike black boxes, Telnet-like sources are transparent but raw; they show the messy internals without filtering.
- [[Worse Is Better]] – The simplicity of Telnet-like sources can be an advantage for quick prototyping or minimal dependency scenarios.
- [[Security Theater]] – Using Telnet-like sources in production often gives a false sense of security, as they rely on obscurity rather than robust authentication.
- [[Jevons Paradox]] – Increasing the ease of access to raw data (via Telnet-like sources) can paradoxically increase overall complexity as more systems depend on them.