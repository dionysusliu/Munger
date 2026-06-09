# Mixed Protocols Scenario with Single Gateway and Two Pairs of FTP Sources

## Definition

The **Mixed Protocols Scenario** is a network architecture pattern where multiple distinct protocols are routed through a single intermediary gateway, while maintaining separate communication channels for different source-target pairs. In the specific configuration described, a single gateway manages traffic for two pairs of FTP (File Transfer Protocol) sources, each pair communicating over potentially different protocol variants or configurations.

This scenario is common in enterprise environments where legacy FTP systems must coexist with modernized infrastructure, or where security requirements necessitate protocol isolation while maintaining centralized control.

## Key Characteristics

- **Single Gateway**: One centralized point of control and routing
- **Multiple Protocol Pairs**: At least two distinct FTP source-target relationships
- **Protocol Diversity**: Each pair may use different FTP variants (e.g., FTP vs FTPS, active vs passive mode)
- **Traffic Isolation**: Despite shared gateway, traffic remains logically separated

## Examples

### Example 1: Hybrid FTP Migration
```
Source Pair A: Legacy FTP (port 21) → Gateway → Target Server A
Source Pair B: FTPS (port 990) → Gateway → Target Server B
```
A company migrating from unencrypted FTP to FTPS uses a single gateway to handle both protocols during transition.

### Example 2: Active/Passive Mode Mixing
```
Source Pair 1: Active FTP → Gateway → Internal File Server
Source Pair 2: Passive FTP → Gateway → Cloud Storage
```
Different network configurations require different FTP modes, all routed through one gateway.

### Example 3: Multi-Department File Transfer
```
Finance FTP Source → Gateway → Finance Target (port 21)
Engineering FTP Source → Gateway → Engineering Target (port 2121)
```
Two departments using different FTP configurations share a centralized gateway for monitoring and access control.

## Related Mental Models

### [[Protocol Gateway Pattern]]
The concept of a single entry point that translates or routes between different protocol implementations. This is the foundational pattern underlying the mixed protocols scenario.

### [[Multi-Protocol Translation Layer]]
A broader architectural pattern where a system handles multiple communication protocols transparently. The FTP mixed scenario is a specific instance of this model.

### [[Traffic Segmentation]]
The practice of logically separating network traffic even when sharing physical infrastructure. This mental model explains how two FTP pairs can coexist on one gateway without interference.

### [[Legacy System Coexistence]]
A strategy for maintaining older systems alongside newer ones during migration. The mixed FTP scenario exemplifies this, as legacy FTP sources operate through the same gateway as modernized FTPS sources.

### [[Hub-and-Spoke Architecture]]
A centralized model where all traffic passes through a single hub (the gateway) to multiple spokes (targets). This describes the topological structure of the scenario.

## Implementation Considerations

- **Port Management**: Ensure the gateway can differentiate traffic by port, IP, or application-level headers
- **Security Policies**: Apply different rules for each protocol pair (e.g., encryption requirements)
- **Monitoring**: Track metrics separately for each source-target pair
- **Scalability**: Single gateway may become a bottleneck with increased traffic
- **Failover**: Redundancy planning for the gateway is critical

## See Also

- [[FTP Active vs Passive Mode]]
- [[Gateway Redundancy Patterns]]
- [[Protocol Translation Techniques]]
- [[Enterprise File Transfer Architecture]]