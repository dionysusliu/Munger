# KVM

## Overview
**KVM** (Kernel-based Virtual Machine) is a Linux kernel module that transforms the Linux kernel into a hardware-assisted hypervisor. By leveraging CPU virtualization extensions (Intel VT-x or AMD-V), KVM enables unmodified guest operating systems to run directly on the host CPU while maintaining strict isolation, security, and near-native performance. Unlike traditional emulators, KVM does not translate instructions; it delegates execution control to the hardware and manages VM state transitions.

---

## 🧠 Mental Model
To understand KVM effectively, shift from thinking of a VM as a "simulated computer" to viewing it as a **scheduled execution context with isolated hardware state**:

1. **The CPU Has Two Worlds**  
   Modern processors split execution into *Root* (host/kernel control) and *Non-Root* (guest/user) modes. KVM doesn't emulate the CPU—it orchestrates safe transitions between these modes. Think of KVM as a traffic controller, not a car builder.

2. **VMs Are Heavyweight Processes**  
   Each virtual CPU (`vCPU`) is simply a Linux thread. The kernel's [[Process Scheduler]] schedules them alongside regular processes. Memory isolation is handled by the MMU, and I/O is routed through virtualized channels.

3. **Kernel + Userspace = Complete Hypervisor**  
   KVM handles CPU/memory execution in kernel space, while userspace tools (like [[QEMU]]) handle device emulation, configuration, and lifecycle management. This split keeps the kernel lean and userspace flexible.

4. **Virtualization ≠ Emulation**  
   Emulation translates instructions across architectures. KVM assumes the guest matches the host architecture and runs instructions natively. Only I/O, privileged instructions, and hardware events trigger kernel intervention.

---

## 🏗️ Architecture & Key Concepts

| Component | Role |
|-----------|------|
| `/dev/kvm` | Character device exposing `ioctl()` interfaces for VM creation, memory mapping, and vCPU execution |
| vCPU Threads | Regular POSIX threads scheduled by the Linux kernel |
| EPT/NPT | Extended Page Tables (Intel) / Nested Page Tables (AMD) enabling direct guest-to-host physical memory translation without shadow page tables |
| [[VirtIO]] | Paravirtualized I/O framework bypassing emulation overhead for disk, network, and memory sharing |
| [[libvirt]] | Management daemon providing declarative VM configuration, networking, and lifecycle APIs |

### Core Workflow
1. Userspace opens `/dev/kvm` and creates a VM via `KVM_CREATE_VM`
2. Memory is mapped using `KVM_SET_USER_MEMORY_REGION`
3. vCPU threads are created and assigned guest register state
4. `KVM_RUN` enters non-root mode; the CPU executes guest code until an exit event occurs
5. Hardware exits trap back to kernel → userspace handles I/O, interrupts, or emulation → resumes execution

---

## 📖 Examples

- **Local Development**  
  ```bash
  qemu-system-x86_64 -enable-kvm -m 4G -cpu host -hda ubuntu.qcow2 -nic user
  ```
  Delegates CPU/memory to KVM while QEMU emulates NIC and disk. Performance approaches bare metal.

- **Cloud Infrastructure**  
  [[OpenStack]] and [[Proxmox VE]] use KVM as the default compute driver, provisioning thousands of isolated tenant VMs across physical nodes.

- **MicroVMs for Serverless**  
  [[Firecracker]] strips QEMU's device emulation down to the essentials, using KVM to launch lightweight VMs in <125ms for secure multi-tenant workloads.

- **Nested Virtualization**  
  Running a KVM VM inside another KVM VM (requires `nested=1` module parameter and CPU support) enables hypervisor testing and sandboxed CI runners.

---

## 🌍 Applications

| Domain | Use Case |
|--------|----------|
| **Cloud Computing** | Foundation for AWS EC2, Google Compute Engine, Azure (hybrid/legacy), and private clouds |
| **Security Isolation** | Running untrusted code, browser sandboxes, or confidential computing workloads |
| **CI/CD & DevOps** | Ephemeral, reproducible VM environments for kernel, driver, or OS-level testing |
| **Edge & IoT** | Lightweight isolation on constrained hardware without container namespace limitations |
| **Legacy Support** | Running Windows XP, DOS, or proprietary OSes without source modifications or translation layers |
| **Kernel Development** | Safe, fast VM-based testing for new kernel patches, [[Kernel Modules]], and filesystem drivers |

---

## 🔗 Related Pages
- [[The Kernel's Role in Virtualization]]
- [[Two Worlds, One CPU: Root and Non-Root Operation]]
- [[The Kernel and VirtIO]]
- [[Kernel Modules]]
- [[User Space and Kernel Space]]
- [[QEMU]]
- [[Firecracker]]
- [[Hypervisor Types]]
- [[Process Scheduler]]
- [[EPT/NPT Memory Virtualization]]

---

## 📝 Notes
- Merged into mainline Linux in `2.6.20` (2007)
- Requires hardware virtualization extensions (`vmx` for Intel, `svm` for AMD)
- I/O performance bottlenecks are typically device emulation, not CPU execution; [[VirtIO]] or [[vhost-net]] mitigates this
- KVM does not manage networking, storage, or graphics natively—it relies on the Linux network stack, [[libvirt]]/QEMU, and GPU passthrough (VFIO)

> 💡 *Alignment Is Understanding:* KVM succeeds because it doesn't reinvent the wheel. It extends the kernel's existing scheduling, memory, and process models to hardware-isolated contexts, proving that the most robust abstractions build on what already works.