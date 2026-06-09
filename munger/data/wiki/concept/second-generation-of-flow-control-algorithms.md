> t     bandwidth                hogs achie

# Second Generation of Flow Control Algorithms

## Definition

The **second generation of flow control algorithms** refers to a class of modern congestion control protocols that evolved from earlier, loss-based algorithms (e.g., TCP Reno) to overcome their poor performance in high‑bandwidth, high‑latency networks. These algorithms are designed to achieve high throughput without behaving as aggressive “bandwidth hogs” – i.e., they avoid unnecessarily filling router buffers, causing excessive queuing delay, and penalizing other flows. They often employ delay‑based or hybrid signals (RTT, bandwidth estimates) instead of relying solely on packet loss, leading to better fairness, lower latency, and higher utilisation.

## Key Characteristics

- **Loss‑independent probing**: Unlike first‑generation algorithms (e.g., TCP Reno) that only reduce window upon packet loss, second‑generation algorithms use metrics such as measured round‑trip time, estimated bottleneck bandwidth, or explicit congestion signals.
- **Targeted for high BDP networks**: Optimised for environments with large [[Bandwidth-Delay Product]], where loss‑based algorithms suffer from underutilisation and bufferbloat.
- **Fairness and friendliness**: Strive to coexist fairly with both legacy TCP flows and other modern algorithms, while avoiding monopolising bandwidth.
- **Multiple control modes**: Often switch between slow start, congestion avoidance, and probe phases based on real‑time network conditions.

## Examples

- **[[TCP CUBIC]]** – Default in Linux since 2.6.19. Uses a cubic function for window growth, making it more aggressive over long‑distance links but still fair over time.
- **[[BBR (Bottleneck Bandwidth and Round-trip propagation time)]]** – Developed at Google. Estimates the bottleneck bandwidth and minimum RTT to model the path, then paces at the estimated rate while keeping queuing minimal.
- **Compound TCP** – Default in Windows. Combines loss‑based and delay‑based components to improve throughput on high‑speed links.
- **Vegas** – Early delay‑based TCP that reduces window when RTT increases, preempting queue buildup.
- **Westwood+** – Uses end‑to‑end bandwidth estimation to set the congestion window after a loss event.

## Evolution from First Generation

| Aspect | First Generation (e.g., Reno) | Second Generation |
|--------|-------------------------------|-------------------|
| Congestion signal | Packet loss | Loss + delay + bandwidth estimates |
| Operating principle | AIMD (Additive Increase Multiplicative Decrease) | Hybrid or model‑based (e.g., rate‑based pacing) |
| Performance in high BDP | Poor utilisation, frequent loss | High utilisation, low queuing delay |
| Buffer occupancy | Often fills buffers (“bufferbloat”) | Attempts to keep queues short |
| Aggressiveness | Fixed increase per RTT | Adaptive probing based on network state |

## Related Mental Models

- **[[Bandwidth-Delay Product]]** – Fundamental concept for understanding why second‑generation algorithms are needed: when the product is large, loss‑based algorithms require many RTTs to fill the pipe.
- **[[Fairness vs Efficiency Tradeoff]]** – Second‑generation algorithms seek to balance high throughput (efficiency) with fair sharing among flows, avoiding the “bandwidth hog” problem.
- **[[AIMD (Additive Increase Multiplicative Decrease)]]** – The classical model underlying first‑generation protocols; second‑generation algorithms often augment or replace it with smoother control laws.
- **[[Bufferbloat]]** – Excessive buffering in network devices; second‑generation algorithms actively combat this by reacting to delay rather than filling buffers.
- **[[TCP CUBIC]]** – Detailed explanation of the most widely deployed second‑generation algorithm.
- **[[BBR]]** – A model‑based algorithm that exemplifies the shift toward bandwidth‑delay product estimation.

## Practical Considerations

- Second‑generation algorithms are essential for modern high‑speed WANs, data centre networks (e.g., DCTCP), and cellular links where latency and throughput vary dynamically.
- Deployment requires careful tuning – some algorithms (e.g., BBR v1) can be mildly unfair to loss‑based flows in certain conditions; later revisions (BBR v3) improve coexistence.
- In environments with deep buffers and sporadic loss, delay‑based algorithms may underperform if RTT estimation is noisy – thus hybrid approaches remain common.

## See Also

- [[Congestion Control]]
- [[TCP Tahoe and Reno]]
- [[Explicit Congestion Notification (ECN)]]
- [[Pacing vs Bursty Transmission]]

---

> *“Second‑generation flow control algorithms represent a paradigm shift from reactive, loss‑driven windows to proactive, model‑based rate control – fundamentally changing how the internet utilises its capacity without becoming a bandwidth hog.”*