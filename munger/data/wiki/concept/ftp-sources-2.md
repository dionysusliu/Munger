# FTP Sources

FTP sources refer to traffic generators in network bandwidth allocation studies and simulations that model file transfers using the File Transfer Protocol (FTP). In network research, FTP sources are typically abstracted as **bulk data transfer sources** that produce a continuous stream of packets for the duration of a file transfer. They are a fundamental workload model used to evaluate network performance, congestion control algorithms, and bandwidth allocation policies.

## Definition

An FTP source is a synthetic traffic source that mimics the behavior of an actual FTP session. In network simulations (e.g., ns-2, ns-3, OMNeT++), FTP sources are often implemented as:

- **Application-layer agents** that generate a TCP connection (or multiple connections) to send a finite or infinite amount of data.
- **Bulk senders** that fill available bandwidth as aggressively as the underlying TCP congestion control allows.
- **On-off or persistent sources**, depending on the modeling fidelity required.

Key characteristics:

| Property | Description |
|----------|-------------|
| **Transport protocol** | Typically TCP (e.g., Reno, NewReno, Cubic) – FTP relies on TCP for reliable delivery. |
| **Traffic pattern** | Continuous burst of data – no idle gaps (unless modeling user think time). |
| **Packet size** | Usually MTU-sized (e.g., 1460 bytes payload for Ethernet) or application-defined. |
| **File size** | Can be fixed (e.g., 10 MB) or variable (e.g., heavy-tailed distribution like Pareto). |
| **Start time** | Often randomized (e.g., Poisson process) to model multiple concurrent flows. |

## Examples

### 1. Persistent FTP source in simulation
In ns-3, a single FTP source is created as:

```
FtpHelper ftp;
ftp.SetAttribute("MaxBytes", UintegerValue(0)); // infinite file
ApplicationContainer app = ftp.Install(serverNode);
app.Start(Seconds(0.0));
```

This sends TCP data continuously from t=0, used to measure steady-state throughput, fairness, or queue dynamics.

### 2. Finite file transfer with multiple sources
A common setup in bandwidth allocation studies is to have \( N \) FTP sources, each transferring a file of size \( S_i \) starting at random times. For example:
- 10 FTP sources, each transferring 1 MB file, start uniformly distributed over 0–10 s.
- Used to study TCP throughput sharing, buffer sizing, or AQM performance.

### 3. Realistic web-like traffic
FTP sources are sometimes combined with **Pareto-distributed file sizes** to model heavy-tailed traffic observed in practice (e.g., large file uploads, video streaming, or software downloads).

## Relation to Other Traffic Models

| Model | Contrast with FTP Sources |
|-------|----------------------------|
| **HTTP sources** | HTTP includes request-response pattern, object sizes, and think times; FTP is simpler (one long flow). |
| **VoIP sources** | Voice generates small, periodic packets (e.g., 20 ms, 160 bytes) – opposite of bursty FTP. |
| **Video streaming** | Can be CBR or VBR, but often uses UDP or adaptive TCP – FTP is pure TCP bulk. |
| **On-off traffic sources** | FTP can be modeled as on-off where “on” is entire file transfer; but often just a single “on” period. |

## Related Mental Models

- [[TCP Congestion Control]] – FTP sources are the classic workload for testing TCP variants (e.g., AIMD, BIC, CUBIC).
- [[Bandwidth Allocation]] – FTP flows compete for bottleneck capacity; allocation is determined by TCP’s fairness model.
- [[Traffic Modeling]] – FTP sources represent a simple, heavy-tailed workload; contrasts with Poisson or Markovian models.
- [[Network Simulators]] – Most simulators (ns-2, ns-3, OMNeT++) include built-in FTP application models.
- [[Queueing Theory]] – FTP sources create persistent queues; used to study AQM (RED, CoDel), bufferbloat, and drop-tail behavior.
- [[File Size Distribution]] – Heavy-tailed file sizes (e.g., Pareto) significantly affect throughput and fairness in multi-flow scenarios.
- [[Flow Completion Time]] – FTP sources are used to measure how long flows take under different congestion control or scheduling schemes.

## Conclusion

FTP sources are a simple yet powerful abstraction in network research. They provide a clean, reproducible workload for evaluating how bandwidth allocation protocols behave under bulk data transfer. Despite the rise of more complex traffic mixes, FTP sources remain a cornerstone of simulation studies due to their strong connection to real-world file downloads, software updates, and background data transfers.