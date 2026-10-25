# Supervisor (patched KVM)

`chronos-kernel.patch` modifies KVM in the Ubuntu Linux 5.15 kernel so that
guest `RDTSC` instructions trap to the hypervisor and return Chronos's virtual
TSC instead of the hardware TSC. Both Intel (`arch/x86/kvm/vmx/vmx.c`) and AMD
(`arch/x86/kvm/svm/svm.c`) hosts are supported.

The virtual TSC is the `global_tsc` symbol exported by the `custom_tsc` module
in [`../slot_monitor/`](../slot_monitor/). KVM looks the symbol up when it is
loaded; if `custom_tsc` is not loaded first, guests see the real TSC.

## Build

The patch applies to Ubuntu tag `Ubuntu-5.15.0-118.128`:

```bash
git clone --depth 1 --branch Ubuntu-5.15.0-118.128 \
  https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/jammy linux
cd linux
patch -p1 < /path/to/chronos-kernel.patch
cp /boot/config-"$(uname -r)" .config
make olddefconfig
make -j"$(nproc)"
sudo make INSTALL_MOD_STRIP=1 modules_install
sudo make install
```

Reboot into the new kernel, load `custom_tsc`, then (re)load `kvm_intel` or
`kvm_amd`. [`deployment/provisioning/scripts/build_kernel.sh`](../../deployment/provisioning/scripts/build_kernel.sh)
automates these steps on Powder.

## Licence

GPL-2.0, the licence of the Linux kernel. See [`COPYING`](COPYING).
