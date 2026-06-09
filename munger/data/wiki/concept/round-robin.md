> first-serv

# Round-Robin

**Round-robin** is a scheduling and allocation method in which participants or items take turns receiving access or service in a fixed, repeating sequence. The core principle is equal opportunity through cyclic rotation, ensuring no single element is prioritized over others.

## Definition

Round-robin is a process where resources, time slots, or opportunities are distributed sequentially and cyclically to all eligible recipients in a predetermined order. After the last participant receives service, the cycle repeats from the beginning. The term originates from medieval French "ruban rond" (round ribbon), referring to petitions with signatures arranged in a circle to obscure who signed first.

## Key Characteristics

- **Cyclic rotation**: Participants take turns in a fixed sequence
- **Equal allocation**: Each participant receives roughly equal service time or opportunity
- **Predictable ordering**: The sequence is known in advance
- **No starvation**: Every participant eventually gets access
- **Simple implementation**: Requires minimal overhead or decision-making

## Examples

### Computer Science
- **CPU scheduling**: Operating systems use round-robin to allocate processor time among running processes. Each process gets a fixed time slice (quantum) before the next process in the queue receives control
- **DNS load balancing**: Requests are distributed across multiple servers in rotation
- **Network packet routing**: Data packets are forwarded through multiple paths cyclically

### Everyday Life
- **Sports tournaments**: In round-robin tournaments, each team plays every other team
- **Meeting facilitation**: A round-robin approach ensures all participants speak in turn
- **Customer service**: Call center systems distribute incoming calls to available agents in rotation
- **Classroom activities**: Teachers call on students in sequence for participation

### Business and Management
- **Task assignment**: Team members rotate through different responsibilities or shifts
- **Interview scheduling**: Candidates interviewed in predetermined order
- **Project review cycles**: Each department presents updates in turn

## Advantages

- **Fairness**: Guarantees equitable resource distribution
- **Simplicity**: Easy to understand and implement
- **Deadlock prevention**: In computing, prevents process starvation
- **Predictability**: Consistent performance for real-time systems

## Limitations

- **Inefficiency**: May not account for varying task complexity or priority
- **Context-switching overhead**: In computing, frequent switching reduces throughput
- **Poor priority handling**: Treats urgent tasks same as routine ones
- **Wasted cycles**: Participants may not need their full turn

## Related Mental Models

- [[Queuing Theory]]: Round-robin is a specific queuing discipline within queue management
- [[Equality vs Equity]]: Round-robin provides equal treatment, not necessarily equitable outcomes
- [[Scheduling Algorithms]]: One family of approaches alongside priority-based, FIFO, and shortest-job-first
- [[Fairness Heuristic]]: Round-robin embodies procedural fairness perceptions
- [[Cyclic Patterns]]: Rotating systems in nature and human organization

## Related Wiki Pages

- [[Fair Division Methods]]
- [[Resource Allocation]]
- [[Load Balancing]]
- [[Time-Sharing Systems]]
- [[Proportional Representation]]