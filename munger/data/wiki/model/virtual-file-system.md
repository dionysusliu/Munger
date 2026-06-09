# Virtual File System

## Mental Model Overview
The **Virtual File System (VFS)** is the Linux kernel’s universal abstraction layer for file-like resources. Rather than treating disks, networks, memory, or synthetic interfaces as fundamentally different subsystems, the kernel models them through a consistent set of objects and operation tables. Think of the VFS as a **coordinated switching board**: it receives uniform requests from user space, routes them to the appropriate backend, caches frequently accessed metadata, and enforces isolation boundaries. 

This aligns with the kernel’s broader design philosophy: *separation of concerns, layered abstraction, and behavior-driven control*. The VFS doesn’t store data—it orchestrates access. In the mental model of the kernel, it sits at the intersection of `[[Process Isolation]]`, `[[System Calls]]`, and `[[Storage Abstraction]]`, translating intent into action without exposing implementation details.

## Core Architecture: Kernel Objects Reveal the Design
The VFS organizes filesystem state into four primary kernel objects. Each object acts as a contract between the kernel’s generic layer and backend-specific implementations:

- `[[Superblock]]`: Represents a mounted filesystem instance. Holds filesystem-wide metadata (block size, magic number, root inode pointer) and a `super_operations` table for mount-level behavior.
- `[[Inode]]`: Represents a single file or directory in storage. Contains permissions, timestamps, data block pointers, and an `inode_operations` table for metadata manipulation.
- `[[Dentry]]` (Directory Entry): Represents a path component in the namespace. Enables fast path resolution and forms the backbone of the `[[Dentry Cache]]`. Decouples logical paths from physical storage.
- `[[File Structure]]`: Represents an open file descriptor in a process context. Tracks current offset, access mode, active locks, and a `file_operations` table for I/O behavior.

Each object exposes a standardized operations structure. This object-oriented design (implemented in C) ensures that **functions only execute logic, while objects reveal the system’s structure**.

## Behavioral Flow: How the Kernel Responds
When a process calls `open("/mnt/data/report.txt", O_RDONLY)`, the VFS follows a reactive, layered resolution path:

1. **Path Resolution**: Breaks the string into components, walking the mount tree and consulting the `[[Dentry Cache]]`.
2. **Boundary Enforcement**: Validates mount points, chroot boundaries, and `[[Mount Namespaces]]`.
3. **Permission Check**: Applies DAC/MAC rules uniformly before delegating to the backend.
4. **Object Dispatch**: Locates the target filesystem’s `[[Superblock]]`, resolves the `[[Inode]]`, and instantiates a `[[File Structure]]`.
5. **I/O Routing**: Future `read()`/`write()` calls bypass path resolution and directly invoke the backend’s operation tables via the cached objects.

The VFS acts as a **stateless coordinator** for stateful backends. It isolates complexity, enforces policy, and serves as the universal contract between processes and resources.

## Examples
- **Unified Tooling**: Commands like `ls`, `cat`, and `cp` work identically across `[[ext4]]`, `[[NFS]]`, `[[procfs]]`, and `[[tmpfs]]` because the VFS normalizes their behavior.
- **Virtual Filesystems**: `/proc` and `/sys` expose kernel state as files. The VFS routes reads to dynamic generators rather than disk blocks, demonstrating virtualization over storage.
- **FUSE (`[[Filesystem in Userspace]]`)**: User-space programs implement filesystem logic; the VFS handles scheduling, permissions, and caching. This highlights the kernel’s delegation model.
- **Bind Mounts & OverlayFS**: Multiple directory trees are merged or remapped through VFS mount points, enabling `[[Containerization]]` and live system modification without backend changes.

## Applications
- **Cross-Backend Compatibility**: Developers write once, and the VFS routes to disk, network, memory, or synthetic backends transparently.
- **Performance Optimization**: Layered caching (`[[Page Cache]]`, `[[Dentry Cache]]`, `[[Inode Cache]]`) reduces redundant I/O and accelerates path resolution.
- **Security & Access Control**: The VFS enforces permission checks uniformly before backend execution, enabling consistent `[[Mandatory Access Control]]` and capability models.
- **Containerization & Sandboxing**: Mount propagation, namespace isolation, and `chroot` rely entirely on VFS mount tree management and path resolution.
- **Debugging & Observability**: Tools like `strace`, `lsof`, and `perf` trace VFS transitions to diagnose latency, permission failures, or cache thrashing.

## Design Philosophy
The VFS embodies the kernel’s layered, reactive architecture:
- **Virtual**: Abstracts physical and logical resources into a unified namespace.
- **Mapped**: Translates user-space paths to backend objects through deterministic resolution.
- **Isolated**: Enforces mount boundaries, namespace views, and permission scopes.
- **Controlled**: Centralizes policy enforcement before delegating to implementation-specific drivers.

As noted in *The Kernel in the Mind*, the kernel is not a monolith of functions—it is a structured system of layers. The VFS proves this by separating **what** a file is (inode, permissions, path) from **how** it is stored or generated (backend operations), ensuring that complexity is contained, behavior is predictable, and the system remains reactive.

## See Also
- `[[Linux Kernel]]`
- `[[System Calls]]`
- `[[Mount Namespaces]]`
- `[[Dentry Cache]]`
- `[[File System Hierarchy]]`
- `[[Process Isolation]]`
- `[[Kernel Object Model]]`
- `[[Page Cache]]`
- `[[Filesystem in Userspace]]`