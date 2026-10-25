# Chronos

Source code, deployment automation, and experiment data for **Chronos: Scalable
and Cost-Effective Cloud-based RAN Emulation System** (ACM MobiCom 2026,
[doi:10.1145/3795866.3844156](https://doi.org/10.1145/3795866.3844156)).

Chronos is a cloud-deployable RAN emulation system built around four ideas:

1. Bypass the compute- and bandwidth-intensive PHY layer using nFAPI.
2. Virtualize time so cloud preemptions and network delays do not cause RAN
   deadlines to expire inside the emulation.
3. Advance components through RAN slots using distributed synchronization
   barriers.
4. Distribute the middlebox that forwards control- and data-plane traffic
   between gNBs and UEs.

At runtime, local slot monitors stop virtual time at slot boundaries. The
middleboxes and participating components report completion to the global slot
coordinator. Once all active components complete the slot, the coordinator
releases the next slot and local virtual clocks resume.

A video walkthrough of the deployment and plotting workflow is included as
[`chronos-artifact.mp4`](chronos-artifact.mp4).

## Repository layout

| Path | Contents |
| --- | --- |
| [`code/supervisor/`](code/supervisor/) | Patch for the Ubuntu Linux 5.15 KVM hypervisor that serves guest `RDTSC` reads from Chronos's virtual TSC (Intel VMX and AMD SVM). |
| [`code/slot_monitor/`](code/slot_monitor/) | `custom_tsc` kernel module and shared-memory utilities that control virtual time. |
| [`code/middlebox/`](code/middlebox/) | Distributed multi-UE nFAPI proxy, slot-completion logic, and global slot coordinator. |
| [`code/gnb/`](code/gnb/) | Modified OpenAirInterface gNB running in nFAPI VNF / emulated-L1 mode. |
| [`code/ue/`](code/ue/) | Modified OpenAirInterface UE (TDD) running in nFAPI PNF / emulated-L1 mode. |
| [`deployment/provisioning/`](deployment/provisioning/) | Powder/Emulab profile and provisioning scripts. |
| [`deployment/helm/`](deployment/helm/) | Kubernetes Helm charts, image build scripts, and experiment scripts. |
| [`results/data/`](results/data/) | Raw logs, packet captures, processed data, and plotting scripts. |
| [`results/output/`](results/output/) | Prepared PDF plots. |
| [`plot.ipynb`](plot.ipynb) | One plotting cell per paper figure or panel. |
| [`ae/`](ae/) | Artifact-evaluation document, as submitted for MobiCom 2026 artifact evaluation. |

Licensing differs per component; see [`LICENSES.md`](LICENSES.md).

## Reproducing the paper plots

Requirements: Linux or macOS, Python 3.10 or newer, and internet access for the
initial dependency installation. No GPU, LaTeX, or privileged access is needed.

```bash
./install_dependencies.sh
source .venv/bin/activate
jupyter notebook plot.ipynb
```

The installer creates a local `.venv` from [`requirement.txt`](requirement.txt)
and registers a `Python (Chronos Artifact)` kernel; select it if Jupyter asks.
To override the Python executable or environment location:

```bash
PYTHON_BIN=/path/to/python3 VENV_DIR=/path/to/venv ./install_dependencies.sh
```

Each notebook cell runs the corresponding plotting script under
`results/data/`, writes a fresh PDF to `results/output/`, and displays it. A
complete run produces 30 PDFs. To run non-interactively:

```bash
source .venv/bin/activate
jupyter nbconvert --to notebook --execute plot.ipynb \
  --output plot.executed.ipynb --ExecutePreprocessor.timeout=300
```

## Deploying Chronos

### Provisioning

[`deployment/provisioning/profile.py`](deployment/provisioning/profile.py) is
the Powder/Emulab profile. It allocates controller/compute, proxy, and global
slot-coordinator nodes and runs the role-specific scripts in
[`deployment/provisioning/scripts/`](deployment/provisioning/scripts/), which
build and install the patched kernel and `custom_tsc` module, configure
networking and SCTP, create nested Ubuntu/KVM guests, install the virtual-time
services, and build the Kubernetes cluster. See
[`deployment/provisioning/README.md`](deployment/provisioning/README.md).

### Building the patched kernel manually

```bash
git clone --depth 1 --branch Ubuntu-5.15.0-118.128 \
  https://git.launchpad.net/~ubuntu-kernel/ubuntu/+source/linux/+git/jammy linux
cd linux
patch -p1 < /path/to/chronos/code/supervisor/chronos-kernel.patch
```

Then build and install the kernel as usual, boot it, and load the
`custom_tsc` module from [`code/slot_monitor/`](code/slot_monitor/). See
[`code/supervisor/README.md`](code/supervisor/README.md).

### Running experiments

The Helm charts in [`deployment/helm/`](deployment/helm/) deploy:

| Chart | Component |
| --- | --- |
| `core/` | Mobile core and subscriber database |
| `globalsc/` | Global slot coordinator |
| `proxy/` | Distributed Chronos middleboxes |
| `gnb/` | OAI gNB instances |
| `ue/` | OAI UE instances and data-plane measurement sidecars |
| `persistue/` | Persistent UE support used by selected experiments |

[`deployment/helm/values.yaml`](deployment/helm/values.yaml) is the central
configuration file: container images, node counts, gNB/UE scale
(`numberGNB`, `numberUE`), and data-plane settings.

From the controller node:

```bash
cd deployment/helm
./run-experiment.sh        # deploy core, gNBs, UEs, coordinator, proxies; start UEs
./core-logs.sh             # check that all gNBs and UEs are connected
./teardown-experiment.sh   # remove the deployment
```

`run-experiment.sh` brings components up in order (core, gNBs, UEs, global
slot coordinator, proxies) and checks each stage before continuing. The global
slot coordinator reports the current dilation factor:

```bash
kubectl logs globalsc | grep 'Dilation factor'
```

A dilation factor near 1 means the emulation is keeping pace with real time;
values above 1 mean Chronos is granting extra wall-clock time per unit of
virtual time because compute is constrained.

Container images can be rebuilt from source with the `build.sh` script in each
chart's `docker/` directory (`gnb/`, `ue/`, `proxy/`).

## Citation

If you use Chronos, please cite:

```bibtex
@inproceedings{10.1145/3795866.3844156,
  author    = {Pawar, Ujjwal and Ferguson, Andrew E. and Xia, Yufeng and Foukas, Xenofon and Marina, Mahesh and Radunovic, Bozidar},
  title     = {Chronos: Scalable and Cost-Effective Cloud-based RAN Emulation System},
  booktitle = {Proceedings of the 32nd Annual International Conference on Mobile Computing and Networking},
  series    = {MobiCom '26},
  year      = {2026},
  pages     = {581--598},
  numpages  = {18},
  location  = {Austin, TX, USA},
  publisher = {Association for Computing Machinery},
  address   = {New York, NY, USA},
  isbn      = {9798400725050},
  doi       = {10.1145/3795866.3844156},
  url       = {https://doi.org/10.1145/3795866.3844156}
}
```
