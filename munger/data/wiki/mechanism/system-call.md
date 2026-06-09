# System Call

A **system call** (often abbreviated **syscall**) is a controlled execution boundary that allows a [[User Process]] to request privileged services from the [[Kernel]]. It forms the primary interface between unprivileged application code and the [[Operating System]], enabling secure access to hardware, memory, process control, and inter-process communication.

## Mechanism Overview
System calls rely on a hardware-enforced privilege transition. Because user-space applications run in a restricted protection ring (typically Ring 3), they cannot directly execute kernel instructions or touch kernel memory. The CPU provides a dedicated trap mechanism that safely switches execution to [[Kernel Space]] (typically Ring 0), runs the requested routine, and returns control without compromising system integrity.

## Causal Execution Chain
The system call lifecycle is deterministic. Each state triggers the next in a strict causal sequence, forming a closed loop from user invocation to kernel completion and return.

1. **User-Space Invocation**
   - **Cause:** Application code invokes a standard library wrapper (e.g., `libc`'s `write()`, `mmap()`, `clone()`).
   - **Effect:** The wrapper loads the architecture-specific syscall number into a designated register and places arguments in the ABI-defined parameter registers.
   - **→ Next Cause:** Wrapper executes the privilege-transition instruction (`syscall` on x86-64, `svc` on ARM, `int 0x80` on legacy x86).

2. **Hardware Trap & Context Preservation**
   - **Effect:** CPU synchronously traps to kernel mode, automatically switching to the [[Kernel Stack]] and saving the user instruction pointer, flags, and stack pointer.
   - **Cause:** Trap vector redirects execution to the kernel entry point (e.g., `entry_SYSCALL_64`).
   - **Effect:** Kernel entry code validates the saved context, disables preemption, and prepares for syscall dispatch.

3. **Syscall Dispatch & Routing**
   - **Cause:** Entry code reads the syscall number from the saved register state.
   - **Effect:** Number is bounds-checked against `NR_syscalls`. If invalid, chain branches to error handling.
   - **Cause:** Valid number indexes into the `[[System Call Table]]` (e.g., `sys_call_table`).
   - **Effect:** CPU jumps to the corresponding kernel handler function (e.g., `sys_read`, `sys_fork`).

4. **Kernel Execution & Resource Access**
   - **Cause:** Handler executes with full kernel privileges and access to [[Device Drivers]], [[Virtual Memory]], and [[File System]] subsystems.
   - **Effect:** Kernel validates arguments (permissions, pointer ranges, capability masks), performs the requested operation, and may block if resources are unavailable.
   - **Cause:** Operation completes or encounters an error condition.
   - **Effect:** Return value or negative error code is written to the designated return register (e.g., `rax`).

5. **Kernel Exit & User Resumption**
   - **Cause:** Kernel exit routine (`syscall_return_slowpath` / `exit_to_user_mode_loop`) prepares the CPU for mode transition.
   - **Effect:** Saved user context is restored from the kernel stack, CPU switches back to [[User Mode]], and interrupts are re-enabled.
   - **Cause:** CPU resumes execution at the instruction immediately following the syscall trap.
   - **Effect:** C library wrapper reads the return register, converts negative values to `errno` if needed, and returns to the original application call site.

## Key Architectural Properties
- **Synchronous Blocking:** By default, the invoking [[Process Control Block|PCB]] yields the CPU until the syscall completes or is interrupted by a signal.
- **Security Boundary:** Every syscall undergoes mandatory validation (credential checks, memory bounds, capability enforcement) before kernel code executes.
- **Context Inheritance:** The syscall runs within the security context, namespace, and resource limits of the calling process.
- **Interruptibility:** Long-running syscalls can be preempted by hardware interrupts or kernel timers, but the causal chain is preserved via saved state.

## Related Mechanisms
- `[[Interrupt Handling]]` – Asynchronous hardware-triggered execution path
- `[[Context Switch]]` – State preservation during privilege transitions
- `[[Process Scheduling]]` – How blocking syscalls yield CPU time to other tasks
- `[[Kernel Threads]]` – Background execution units (e.g., `kthreadd`) that operate independently of user syscalls
- `[[Application Binary Interface|ABI]]` – Standardized register layout and calling conventions for syscall invocation

## Diagnostics & Tooling
- `[[strace]]` – Traces syscall entry/exit, arguments, and return values
- `[[perf]]` – Profiles syscall latency and frequency
- `[[eBPF]]` – Attaches probes to syscall entry/exit hooks for runtime observability

*Implementation details vary by CPU architecture and kernel version, but the causal chain remains conceptually consistent across modern Unix-like systems.*