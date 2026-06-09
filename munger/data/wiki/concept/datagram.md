# Datagram

A **datagram** is a self-contained, independent unit of data transmitted over a packet-switched network. It contains sufficient information (source and destination addresses, protocol metadata, and payload) to be routed from one network node to another without requiring a pre-established connection. Datagrams are the fundamental building blocks of connectionless communication protocols, most notably the Internet Protocol (IP) and the User Datagram Protocol (UDP).

## Definition

In the context of packet-switched networks, a datagram is a packet that:

- Carries both header and payload data.
- Is routed independently, meaning each datagram may take a different path to the destination.
- Does not rely on a continuous virtual circuit or session state.
- May arrive out of order, be duplicated, or be lost without automatic retransmission (unless handled by higher-layer protocols).

The term was popularised in early networking literature, including proposals by John Nagle (see [[Nagle's Algorithm]]), who discussed how sending many small datagrams could degrade network performance. Nagle's algorithm was specifically designed to reduce the number of tiny datagrams emitted by TCP connections, even though TCP itself is a stream-oriented protocol that encapsulates data into segments.

## Examples

### Internet Protocol (IP) Datagram
IP datagrams are the core units of data in the Internet layer. Each IP datagram contains a header (source/destination IP, version, length, time-to-live, etc.) and a payload (e.g., a TCP segment or UDP datagram). Example: sending a ping command sends an ICMP echo request encapsulated in an IP datagram.

### User Datagram Protocol (UDP) Datagram
UDP provides a minimal, connectionless transport layer built on top of IP. A UDP datagram consists of a header (source/destination ports, length, checksum) and a data payload. Example: DNS queries are sent as UDP datagrams because they are small, stateless, and tolerate loss.

### Network Simulator Example
Consider a simple file transfer using UDP over a network with varying latency:  

```
Datagram 1: 192.168.1.10 → 203.0.113.5  (payload: "Hello")
Datagram 2: 192.168.1.10 → 203.0.113.5  (payload: "World")
```
If Datagram 2 arrives before Datagram 1, the receiver must reassemble or process them independently – the network does not guarantee ordering.

## Related Mental Models

- **[[Packet Switching]]** – The overarching paradigm in which datagrams are one of the two main packet types (the other being virtual-circuit packets). Packet switching vs. circuit switching.
- **[[Connectionless vs. Connection-Oriented]]** – Datagrams are inherently connectionless; contrasted with streams or virtual circuits (e.g., TCP connections).
- **[[Store-and-Forward]]** – Each router along the path buffers the entire datagram before forwarding it to the next hop.
- **[[Best-Effort Delivery]]** – The network does not guarantee delivery, order, or duplicate removal – characteristics of datagram networks.
- **[[Nagle's Algorithm]]** – A congestion control mechanism to coalesce small datagram-like segments in TCP to avoid excessive tiny packets, originally inspired by the behavior of datagram networks.
- **[[Maximum Transmission Unit (MTU)]]** – The maximum size of a datagram payload that can be transmitted over a particular link without fragmentation.

## See Also

- [[IP Datagram Header]]
- [[UDP Datagram]]
- [[Fragmentation]]
- [[Connectionless Protocol]]
- [[John Nagle]]