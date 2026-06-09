# eBPF

**Extended Berkeley Packet Filter (eBPF)** is a safe, sandboxed, event-driven execution environment built directly into the Linux kernel. Originally designed for network packet filtering, eBPF has evolved into a foundational runtime that allows user-space developers to programmatically extend kernel behavior without modifying source code, recompiling the kernel, or loading traditional `[[Kernel Modules]]`.

---

## 🔑 Mental Model

Think of eBPF not as a tool, but as a **programmable indirection layer** inside the kernel. It transforms the Linux kernel from a static, monolithic OS into a dynamic, observable, and extensible platform.

| Traditional Kernel View | eBPF Mental Model |
|------------------------|-------------------|
| Kernel logic is fixed at compile time | Kernel exposes **hooks** where small programs can attach |
| Debugging requires static probes or recompilation | Observability is **event-driven** and attach/detach at runtime |
| Packet filtering happens late in the stack | Logic can run **early** (e.g., `[[XDP]]`) or **deep** (e.g., `[[LSM Hooks]]`) |
| State lives in user-space or kernel memory | State is shared safely via `[[eBPF Maps]]` with bounded access |
| Concurrency safety requires manual locking | `[[Verifier]]` guarantees termination, memory safety, and no privilege escalation |

**Core Abstraction:**  
`Event → Hook → Verified Program → Action/Telemetry`  
eBPF programs are **stateless per execution** but become **stateful across events** via maps. They run in the context of the kernel event that triggered them, inheriting its `[[Execution Path]]` and `[[Interrupt Context]]` without disrupting the core scheduler or memory manager.

---

## 🧱 Architecture & Execution Flow

1. **Write & Compile**  
   Developer writes logic in C/Rust → compiled to BPF bytecode using `clang`/`LLVM`.
2. **Load & Verify**  
   Bytecode is submitted to the kernel. The `[[Verifier]]` performs static analysis:
   - Bounded loops & termination guarantees
   - Valid memory bounds (no out-of-bounds reads/writes)
   - No unsafe kernel pointer dereferences
   - Concurrency-safe access patterns
3. **JIT Compile**  
   Verified bytecode is translated to native machine code (`[[JIT Compilation]]`) for near-zero overhead execution.
4. **Attach to Hooks**  
   Program binds to kernel entry points:
   - `[[Tracepoints]]` / `[[Kprobes]]` / `[[Uprobes]]`
   - Network (`[[XDP]]`, `[[TC]]`, `[[Socket Filters]]`)
   - Security (`[[LSM Hooks]]`)
   - Scheduler, cgroups, perf events
5. **Execute & Communicate**  
   Runs in-kernel when triggered. Updates `[[eBPF Maps]]` or pushes telemetry via `[[Ring Buffers]]` to user-space consumers.

---

## 💡 Examples

- **Network Packet Drop at Wire Speed**  
  Attach an `[[XDP]]` program to `eth0`. On each packet ingress, inspect headers and return `XDP_DROP` before the packet enters the network stack.
- **System Call Latency Histogram**  
  `bpftrace -e 'tracepoint:syscalls:sys_enter_read { @start[tid] = nsecs; } tracepoint:syscalls:sys_exit_read /@start[tid]/ { @lat = hist(nsecs - @start[tid]); delete(@start[tid]); }'`
- **Custom Security Policy**  
  Use `[[LSM Hooks]]` to block `execve()` for binaries running in untrusted containers, enforced entirely in-kernel without user-space daemons.
- **TCP Connection Tracking**  
  Maintain a hash map of active connections. Increment/decrement counters on `[[TCP]]` state transitions. Export metrics to Prometheus.

---

## 🌍 Applications

| Domain | Use Case | Key eBPF Feature |
|--------|----------|------------------|
| **Cloud-Native Networking** | Kubernetes service mesh, load balancing, network policies | `[[XDP]]`, `[[TC]]`, `[[eBPF Maps]]` |
| **Observability & Profiling** | Real-time tracing, CPU/memory profiling, flame graphs | `[[Tracepoints]]`, `[[Kprobes]]`, `[[Ring Buffers]]` |
| **Security & Compliance** | Runtime threat detection, syscall filtering, zero-trust enforcement | `[[LSM Hooks]]`, `[[Cgroups]]`, `[[Verifier]]` |
| **Performance Optimization** | Dynamic caching, packet acceleration, scheduler tuning | JIT compilation, early hook attachment |
| **Storage & I/O** | Filesystem tracing, I/O latency measurement, block layer filtering | `[[BPF_PROG_TYPE_TRACING]]`, `[[Kprobes]]` |

Popular ecosystems built on this model: `[[Cilium]]`, `[[bcc]]`, `[[Falco]]`, `[[Tracee]]`, `[[Pixie]]`, `[[bpftrace]]`.

---

## 🔄 Core Mental Shifts

- **From Polling → Push**: Stop sampling user-space logs. Let the kernel push events when they matter.
- **From Modules → Bytecode**: Replace heavyweight `[[Kernel Modules]]` with verified, sandboxed programs.
- **From Static → Composable**: Attach/detach logic at runtime. Mix and match hooks like LEGO blocks.
- **From Unsafe → Guaranteed**: The `[[Verifier]]` enforces `[[Concurrency Safety]]` and memory bounds. You trade raw power for predictable safety.
- **From Monolithic → Layered**: eBPF sits cleanly between `[[Device Model]]` abstractions, `[[Memory Management]]`, and `[[Execution Paths]]`, respecting kernel boundaries while extending them.

---

## 🔗 Related Concepts

- `[[Linux Kernel]]`
- `[[Kernel Execution Paths]]`
- `[[Tracing and Profiling]]`
- `[[Memory Management]]`
- `[[Concurrency and Locking]]`
- `[[Device Model]]`
- `[[JIT Compilation]]`
- `[[XDP]]`
- `[[eBPF Maps]]`
- `[[Verifier]]`
- `[[LSM Hooks]]`
- `[[Interrupts]]`
- `[[From vmlinuz to eBPF: What Actually Runs Inside the Linux Kernel]]`

---

## 📚 Further Reading

- Official `[[eBPF Documentation]]` (kernel.org)
- *What is eBPF?* by Liz Rice (O'Reilly)
- `[[The eBPF Book]]` – Architecture, verifier internals, and map types
- `[[Kernel Tracing]]` fundamentals: tracepoints vs kprobes vs uprobes
- `[[Concurrency Safety]]` in kernel space: why eBPF avoids race conditions by design

> 💡 **Editor's Note**: When modeling eBPF in system design, always ask: *Where does the event originate? What kernel state does it touch? How will I safely export or act on it?* The answers map directly to hook selection, map design, and verifier constraints.