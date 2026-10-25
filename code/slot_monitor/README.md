# Slot monitor (`custom_tsc`)

`custom_tsc` is a Linux kernel module that maintains Chronos's virtual TSC. It
exports `global_tsc`, which the patched KVM in [`../supervisor/`](../supervisor/)
returns to guests on `RDTSC`. A high-resolution timer advances `global_tsc`;
at each slot boundary the module pauses virtual time until the slot is released
through a shared-memory page (`/dev/shm/my-little-shared-memory`), so guests
never observe a missed RAN deadline.

| File | Purpose |
| --- | --- |
| `custom_tsc.c` | The kernel module. `dilation` (module parameter, writable at `/sys/module/custom_tsc/parameters/dilation`) slows guest time by that factor; `/proc/global_tsc` exposes the current value. |
| `init.c` | Initialises the shared-memory slot state. |
| `shared.c` | Debug helper that prints the shared-memory slot state continuously. |

## Build and load

Build against the running (patched) kernel, then load the module **before**
the KVM vendor module so KVM can find `global_tsc`:

```bash
gcc init.c -o init
gcc shared.c -o shared
make
sudo rmmod kvm_intel kvm   # or kvm_amd
sudo insmod custom_tsc.ko
sudo modprobe kvm_intel    # or kvm_amd
sudo ./init
```

[`deployment/provisioning/scripts/build_kernel.sh`](../../deployment/provisioning/scripts/build_kernel.sh)
automates these steps on Powder.

## Licence

GPL-2.0. See [`COPYING`](COPYING).
