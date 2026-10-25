# Licensing

Chronos is built on several existing open-source projects, so each component
keeps its own licence. The licence text for each component is in that
component's directory.

| Path | Based on | Licence |
| --- | --- | --- |
| `code/supervisor/` | Ubuntu Linux kernel (jammy, `Ubuntu-5.15.0-118.128`) | GPL-2.0 ([`COPYING`](code/supervisor/COPYING)) |
| `code/slot_monitor/` | — (original Chronos code; Linux kernel module) | GPL-2.0 ([`COPYING`](code/slot_monitor/COPYING)) |
| `code/middlebox/` | [EpiSci oai-lte-multi-ue-proxy](https://github.com/EpiSci/oai-lte-multi-ue-proxy) | EpiSci Public License 1.1 ([`LICENSE`](code/middlebox/LICENSE)) |
| `code/gnb/` | [OpenAirInterface 5G](https://gitlab.eurecom.fr/oai/openairinterface5g) | OAI Public License 1.1 ([`LICENSE`](code/gnb/LICENSE), [`NOTICE.md`](code/gnb/NOTICE.md)) |
| `code/ue/` | [OpenAirInterface 5G](https://gitlab.eurecom.fr/oai/openairinterface5g) | OAI Public License 1.1 ([`LICENSE`](code/ue/LICENSE), [`NOTICE.md`](code/ue/NOTICE.md)) |
| `deployment/` | — | MIT ([`LICENSE`](deployment/LICENSE)) |
| `plot.ipynb`, `install_dependencies.sh`, `requirement.txt` | — | MIT ([`LICENSES/MIT.txt`](LICENSES/MIT.txt)) |
| `results/` — scripts (`*.py`, `*.ipynb`, `*.sh`, `*.c`) | — | MIT ([`LICENSES/MIT.txt`](LICENSES/MIT.txt)) |
| `results/` — data and figures | — | CC BY-SA 4.0 ([`LICENSES/CC-BY-SA-4.0.txt`](LICENSES/CC-BY-SA-4.0.txt)); see [`results/LICENSE.md`](results/LICENSE.md) |
| `chronos-artifact.mp4`, `ae/`, documentation | — | CC BY-SA 4.0 ([`LICENSES/CC-BY-SA-4.0.txt`](LICENSES/CC-BY-SA-4.0.txt)) |

Third-party code bundled inside a component (for example open-nFAPI in
`code/middlebox/open-nFAPI/`, or the libraries listed in OAI's `NOTICE.md`)
remains under its own licence as stated in its files.
