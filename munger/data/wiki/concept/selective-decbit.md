# Selective DECbit

Selective DECbit is a congestion control mechanism that refines the original [[DECbit]] (Digital Equipment Corporation bit) scheme by selectively marking packets to indicate network congestion. Unlike the original DECbit, which marks every packet when the average queue length exceeds a threshold, Selective DECbit marks only a subset of packets – typically based on a probability function or congestion severity – to provide smoother and more stable feedback to senders.

## How It Works

Selective DECbit operates at network routers. The router maintains a moving average of the queue length (or a similar congestion metric). When this average exceeds a minimum threshold, the router begins to mark a fraction of passing packets by setting a special bit in the packet header. The marking probability increases as congestion worsens, similar to [[Random Early Detection]] (RED), but the feedback is binary (marked/unmarked) rather than dropping packets.

Key steps:
1. **Queue monitoring** – The router computes an average queue length (e.g., using exponential weighted moving average).
2. **Threshold comparison** – If the average queue length is below a low threshold, no packets are marked. If it is above a high threshold, all packets are marked (or dropped). Between the thresholds, the router marks packets with a probability that increases linearly (or according to a chosen function) with the average queue length.
3. **Selective marking** – Each incoming packet is marked with probability `p` derived from the congestion level.
4. **Sender reaction** – The sender detects marked packets via the congestion bit and reduces its congestion window (typically using [[Additive Increase Multiplicative Decrease]]).

## Examples

- **Internet routers implementing Active Queue Management (AQM):** Selective DECbit can be used as a lighter-weight alternative to packet dropping, especially when end-to-end loss is undesirable. For instance, a router in a video streaming network might mark packets instead of dropping them, allowing senders to throttle throughput without retransmissions.
- **Wireless networks:** Selective DECbit helps avoid excessive retransmissions caused by packet drops due to transient wireless errors. By selectively marking packets during mild congestion, senders can adjust their rate without mistaking a drop for severe congestion.
- **Data center TCP:** Variants of Selective DECbit are used in [[Data Center TCP]] (DCTCP) to provide early, multi-bit feedback via ECN marking, which is a form of selective marking.

## Related Mental Models

- [[Congestion Control]] – The overarching framework for managing network traffic to avoid collapse.
- [[Additive Increase Multiplicative Decrease]] (AIMD) – The typical sender response algorithm that works with DECbit feedback.
- [[Random Early Detection]] (RED) – A closely related AQM algorithm that drops (or marks) packets probabilistically.
- [[Explicit Congestion Notification]] (ECN) – A standard that uses a two-bit field to provide binary congestion feedback; Selective DECbit is a specific marking policy for ECN.
- [[Feedback Loop]] – The concept of using router signals to influence sender behavior, forming a control loop.
- [[TCP Vegas]] – A delay-based congestion control that can be contrasted with DECbit’s queue-based marking.

## References

- Ramakrishnan, K. K., & Jain, R. (1990). *A Binary Feedback Scheme for Congestion Avoidance in Computer Networks*. ACM Transactions on Computer Systems. (Original DECbit paper.)
- Floyd, S., & Jacobson, V. (1993). *Random Early Detection Gateways for Congestion Avoidance*. IEEE/ACM Transactions on Networking. (Probability-based marking, precursor to Selective DECbit.)
- Alizadeh, M., et al. (2010). *Data Center TCP (DCTCP)*. ACM SIGCOMM. (Uses selective ECN marking inspired by Selective DECbit.)