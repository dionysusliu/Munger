# Kernel Space

## Definition
**Kernel space** is the privileged, protected region of virtual memory where the core components of an operating system execute. Unlike [[User Space]], which hosts application code and runs with restricted permissions, kernel space operates at the highest CPU privilege level. It is loaded into memory during system boot, remains resident for the duration of the session, and governs all direct interactions between hardware and software. Kernel space provides the foundational abstractions for [[Process Management]], [[Memory Management]], [[I/O Scheduling]], and [[Network Stacks]], while enforcing security and stability boundaries that prevent user applications from directly accessing physical resources.

## Architecture & Execution Model
Kernel space does not execute as a conventional scheduled task. It has no PID, is never explicitly started or stopped, and is initialized once during the boot sequence. After the bootloader transfers control, the kernel begins execution in `start_kernel()`, where it initializes memory allocators, device interfaces, and core subsystems. Following this one-time setup, the kernel transitions into a **reactive execution layer**, invoked only when triggered by:

1. **System Calls:** User processes request privileged operations via the [[System Call Interface]], causing a controlled trap into kernel space.
2. **Interrupt Handlers:** Hardware events (e.g., disk I/O completion, network packet arrival, timer ticks) asynchronously invoke interrupt service routines (ISRs) in kernel space.
3. **Kernel Threads:** Long-lived, kernel-managed execution contexts that run entirely in kernel space to handle background maintenance tasks. These threads appear in process listings (typically enclosed in square brackets) but are distinct from userland daemons and never execute user-space code.

The first kernel thread is `kthreadd`, assigned PID 2. Created during the final phase of initialization in the `rest_init()` function, `kthreadd` acts as the parent for all subsequent kernel threads. While PID 1 (`init` or `systemd`) boots the [[User Space]] environment, PID 2 marks the beginning of the kernel's threaded runtime. The number of kernel threads is not fixed: at boot, a system typically spawns 20–40 essential threads (e.g., per-core soft IRQ handlers, watchdogs, migration helpers, and early worker queues). As the system becomes active, additional threads are dynamically spawned to handle deferred work, I/O backlogs, and subsystem-specific maintenance.

## Key Examples
| Category | Examples | Description |
|----------|----------|-------------|
| **Core Threads** | `kthreadd` (PID 2), `kworker/*`, `ksoftirqd/*`, `rcu_sched` | Handle deferred work, soft interrupts, and RCU synchronization. |
| **Device Drivers** | Network card drivers, NVMe block drivers, GPU DRM drivers | Translate hardware-specific protocols into kernel subsystem APIs. |
| **Subsystems** | [[Virtual File System]], [[TCP/IP Stack]], [[Page Allocator]] | Provide abstracted, secure interfaces for storage, networking, and memory. |
| **Execution Contexts** | System call handlers, top-half/bottom-half IRQ handlers, NMI handlers | Manage synchronous user requests and asynchronous hardware events. |

## Related Mental Models
Understanding kernel space is often aided by the following conceptual frameworks:

* **[[Privilege Ring Model]]** – CPU architectures divide execution into rings (Ring 0 for kernel, Ring 3 for user). Kernel space operates in the most privileged ring, granting direct hardware access and memory control.
* **[[User-Kernel Boundary]]** – The strict isolation layer that prevents accidental or malicious user-space code from corrupting kernel state. Cross-boundary transitions occur only via validated [[System Call]] or [[Interrupt]] pathways.
* **[[Monolithic vs Microkernel]]** – Design philosophies dictating what resides in kernel space. Monolithic kernels place drivers and filesystems inside kernel space for performance; microkernels minimize kernel space to only IPC, scheduling, and basic memory management, moving other services to user space.
* **[[Event-Driven Architecture]]** – Kernel space behaves as a highly concurrent event processor. Rather than running linearly, it reacts to external stimuli (user requests, hardware signals, timers) using queues, workqueues, and interrupt contexts.
* **[[Hardware Abstraction Layer]]** – Kernel space standardizes heterogeneous hardware into consistent APIs. Applications interact with abstracted devices (e.g., `/dev/sda`, `eth0`), while the kernel space handles the translation to physical controller commands.

## See Also
* [[User Space]]
* [[System Call]]
* [[Interrupt Handler]]
* [[Context Switch]]
* [[Kernel Mode vs User Mode]]
* [[Boot Process]]