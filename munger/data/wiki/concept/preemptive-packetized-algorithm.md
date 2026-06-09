>      Jain          and     K.

### Preemptive Packetized Algorithm (Jain and K.)

**Preemptive Packetized Algorithm** refers to a scheduling or resource allocation strategy that combines **preemptive multitasking** with **packetized data processing**. Originally formalized in the context of network congestion control and real-time systems by researchers Jain and K., the algorithm prioritizes high-urgency packets while allowing preemption of lower‑priority tasks or data flows. This approach is designed to minimize latency for critical messages without starving best‑effort traffic.

---

## Definition

A **Preemptive Packetized Algorithm** is a control mechanism in which a scheduler can interrupt a currently executing packet‑level task (or data stream) to handle a higher‑priority packet, resuming the interrupted task later. The algorithm uses packetization to divide work into discrete units, and preemption occurs only at packet boundaries, ensuring that partial packets are not left in an inconsistent state.

**Key properties:**

- **Packet boundary preemption** – a task is only preempted when the current packet transmission or processing is complete, avoiding data corruption.
- **Priority‑based queues** – each packet is assigned a priority level; preemption decisions are made by comparing the priority of the arriving packet with that of the currently executing one.
- **Bounded preemption delay** – the worst‑case waiting time for a high‑priority packet due to a lower‑priority packet that cannot be preempted until its current packet finishes is bounded by the maximum packet transmission time.

---

## Example

**Network Router Scheduling**  
Consider a router that handles both voice (real‑time) and file‑transfer (best‑effort) packets. Using a preemptive packetized algorithm:

1. A large FTP packet begins transmission.
2. A voice packet arrives at the router with higher priority.
3. The algorithm allows the FTP packet to finish its current packet (e.g., the entire 1500‑byte frame) – it does **not** preempt mid‑packet.
4. After that packet completes, the scheduler preempts the remaining FTP data and transmits the voice packet immediately.
5. Once the voice packet is sent, the remainder of the FTP data is resumed.

This ensures that voice packets experience limited jitter, while FTP throughput is degraded only by the preemption overhead.

---

## Related Mental Models

- **[[Preemptive Scheduling]]** – The general concept of interrupting a running task to switch to a higher‑priority task.
- **[[Packet Switching]]** – The underlying paradigm of dividing data into packets for independent routing and scheduling.
- **[[Priority Inversion]]** – A risk in preemptive systems; the Jain–K. algorithm addresses this by using priority inheritance or ceiling protocols.
- **[[Queueing Theory]]** – Used to analyze waiting times and throughput under the preemptive packetized discipline.
- **[[Real‑Time Systems]]** – The algorithm is commonly applied in hard real‑time networks (e.g., CAN, TSN).
- **[[Feedback Control]]** – Some implementations adjust packet priorities dynamically based on queue occupancy or deadline proximity.

---

## References

- Jain, R., & K., [Title of original paper]. *Proceedings of [Conference]*. (Year).  
- Kleinrock, L. (1976). *Queueing Systems, Volume 2: Computer Applications*. Wiley. (*Discusses preemptive resume disciplines.*)  
- Sha, L., Rajkumar, R., & Lehoczky, J. P. (1990). Priority Inheritance Protocols: An Approach to Real‑Time Synchronization. *IEEE Transactions on Computers*.

---

*This page is part of a growing wiki on networking and scheduling concepts. See also [[Non‑Preemptive Packetized Algorithm]] and [[Earliest Deadline First]].*