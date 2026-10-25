#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = ["matplotlib"]
# ///

# How to run:
#   python3 analyse_proxy.py /path/to/proxy.pcap --csv-out results.csv --out plot.pdf
#
# Measures proxy wait time from the latest aligned gNB SLOT_INDICATION to the
# proxy ACK sent to globalsc. Misaligned or incomplete gNB rounds are excluded.
# allow: SIZE_OK - user requested one self-contained script with no local module dependencies.

from __future__ import annotations

import argparse
import csv
import ipaddress
import struct
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterable, List, Optional, Sequence, TextIO, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

LINUX_SLL2: Final = 276
SLL2_HEADER_LEN: Final = 20
IPV4_ETHERTYPE: Final = 0x0800
UDP_PROTOCOL: Final = 17
SLOT_INDICATION: Final = 0x82
ACK_PROXY: Final = 1
MAX_GNBS: Final = 250
GnbKey = Tuple[str, int, int]


class PcapError(Exception):
    """Raised when a pcap cannot be parsed or analyzed."""


@dataclass(frozen=True)
class UdpDatagram:
    packet_index: int
    timestamp_us: int
    src_ip: str
    src_port: int
    dst_ip: str
    dst_port: int
    payload: bytes


@dataclass(frozen=True)
class SlotEvent:
    packet_index: int
    timestamp_us: int
    gnb: GnbKey
    sfn: int
    slot: int


@dataclass(frozen=True)
class AckEvent:
    packet_index: int
    timestamp_us: int
    proxy_id: int
    slot_byte: int


@dataclass(frozen=True)
class Config:
    proxy_ip: str
    globalsc_ip: str
    globalsc_port: int
    gnb_network: ipaddress.IPv4Network
    expected_gnb_count: Optional[int]


@dataclass(frozen=True)
class TimingRow:
    round_index: int
    ack: AckEvent
    sfn: int
    slot: int
    first_slot_ts_us: int
    latest_slot_ts_us: int
    gnb_count: int
    gnb_ips: Tuple[str, ...]

    @property
    def slot_spread_us(self) -> int:
        return self.latest_slot_ts_us - self.first_slot_ts_us

    @property
    def wait_us(self) -> int:
        return self.ack.timestamp_us - self.latest_slot_ts_us


@dataclass(frozen=True)
class Analysis:
    path: Path
    rows: Tuple[TimingRow, ...]
    gnb_keys: Tuple[GnbKey, ...]
    rejections: Counter
    slot_events: int
    ack_events: int


def pcap_endian_and_scale(magic: bytes) -> Tuple[str, int]:
    if magic == b"\xd4\xc3\xb2\xa1":
        return "<", 1
    if magic == b"\xa1\xb2\xc3\xd4":
        return ">", 1
    if magic == b"\x4d\x3c\xb2\xa1":
        return "<", 1000
    if magic == b"\xa1\xb2\x3c\x4d":
        return ">", 1000
    if magic == b"\x0a\x0d\x0d\x0a":
        raise PcapError("pcapng is not supported; provide classic pcap")
    raise PcapError("unrecognized pcap magic")


def iter_pcap_udp(path: Path) -> Iterable[UdpDatagram]:
    with path.open("rb") as handle:
        endian, ts_scale = pcap_endian_and_scale(handle.read(4))
        header = handle.read(20)
        if len(header) != 20:
            raise PcapError("truncated pcap global header")
        _major, _minor, _zone, _sigfigs, _snaplen, linktype = struct.unpack(endian + "HHIIII", header)
        if linktype != LINUX_SLL2:
            raise PcapError("unsupported linktype %d; expected Linux cooked v2 (%d)" % (linktype, LINUX_SLL2))
        packet_index = 0
        while True:
            record_header = handle.read(16)
            if not record_header:
                return
            if len(record_header) != 16:
                raise PcapError("truncated packet record header")
            sec, fraction, included_len, _original_len = struct.unpack(endian + "IIII", record_header)
            packet = handle.read(included_len)
            if len(packet) != included_len:
                raise PcapError("truncated packet record data")
            packet_index += 1
            datagram = parse_sll2_udp(packet, packet_index, sec * 1_000_000 + fraction // ts_scale)
            if datagram is not None:
                yield datagram


def parse_sll2_udp(packet: bytes, packet_index: int, timestamp_us: int) -> Optional[UdpDatagram]:
    if len(packet) < SLL2_HEADER_LEN + 28 or struct.unpack("!H", packet[:2])[0] != IPV4_ETHERTYPE:
        return None
    ip_start = SLL2_HEADER_LEN
    version_ihl = packet[ip_start]
    ihl = (version_ihl & 0x0F) * 4
    if version_ihl >> 4 != 4 or ihl < 20 or len(packet) < ip_start + ihl + 8:
        return None
    ip_packet = packet[ip_start:]
    total_len = struct.unpack("!H", ip_packet[2:4])[0]
    flags_fragment = struct.unpack("!H", ip_packet[6:8])[0]
    if ip_packet[9] != UDP_PROTOCOL or total_len < ihl + 8 or total_len > len(ip_packet) or flags_fragment & 0x3FFF:
        return None
    udp_start = ip_start + ihl
    src_port, dst_port, udp_len, _checksum = struct.unpack("!HHHH", packet[udp_start:udp_start + 8])
    if udp_len < 8 or ihl + udp_len > total_len:
        return None
    return UdpDatagram(packet_index, timestamp_us, dotted(packet[ip_start + 12:ip_start + 16]), src_port, dotted(packet[ip_start + 16:ip_start + 20]), dst_port, packet[udp_start + 8:udp_start + udp_len])


def dotted(raw: bytes) -> str:
    return ".".join(str(part) for part in raw)


def parse_slot_event(datagram: UdpDatagram, config: Config) -> Optional[SlotEvent]:
    if datagram.dst_ip != config.proxy_ip or ipaddress.IPv4Address(datagram.src_ip) not in config.gnb_network:
        return None
    payload = datagram.payload
    if len(payload) < 20 or struct.unpack("!H", payload[2:4])[0] != SLOT_INDICATION:
        return None
    if struct.unpack("!H", payload[4:6])[0] != len(payload):
        return None
    phy_id = struct.unpack("!H", payload[:2])[0]
    sfn, slot = struct.unpack("!HH", payload[16:20])
    if sfn >= 1024 or slot >= 320:
        return None
    return SlotEvent(datagram.packet_index, datagram.timestamp_us, (datagram.src_ip, datagram.src_port, phy_id), sfn, slot)


def parse_ack_event(datagram: UdpDatagram, config: Config) -> Optional[AckEvent]:
    if datagram.src_ip != config.proxy_ip or datagram.dst_ip != config.globalsc_ip or datagram.dst_port != config.globalsc_port or len(datagram.payload) != 6:
        return None
    ack_type, proxy_id, slot_byte = struct.unpack("<BIB", datagram.payload)
    if ack_type != ACK_PROXY:
        return None
    return AckEvent(datagram.packet_index, datagram.timestamp_us, proxy_id, slot_byte)


def collect_events(path: Path, config: Config) -> Tuple[List[SlotEvent], List[AckEvent]]:
    slots: List[SlotEvent] = []
    acks: List[AckEvent] = []
    for datagram in iter_pcap_udp(path):
        slot_event = parse_slot_event(datagram, config)
        ack_event = parse_ack_event(datagram, config)
        if slot_event is not None:
            slots.append(slot_event)
        if ack_event is not None:
            acks.append(ack_event)
    return slots, acks


def expected_gnbs(slots: Sequence[SlotEvent], expected_count: Optional[int]) -> Tuple[GnbKey, ...]:
    keys = tuple(sorted({slot.gnb for slot in slots}))
    if not keys:
        raise PcapError("no gNB-to-proxy SLOT_INDICATION packets found")
    if len(keys) > MAX_GNBS:
        raise PcapError("discovered %d gNBs; maximum supported is %d" % (len(keys), MAX_GNBS))
    if expected_count is not None and len(keys) != expected_count:
        raise PcapError("expected %d gNBs, discovered %d" % (expected_count, len(keys)))
    return keys


def analyze_capture(path: Path, config: Config) -> Analysis:
    slots, acks = collect_events(path, config)
    gnb_keys = expected_gnbs(slots, config.expected_gnb_count)
    rows, rejections = match_rounds(slots, acks, gnb_keys)
    if not rows:
        raise PcapError("no aligned gNB rounds matched a proxy ACK")
    return Analysis(path, tuple(rows), gnb_keys, rejections, len(slots), len(acks))


def match_rounds(slots: Sequence[SlotEvent], acks: Sequence[AckEvent], gnb_keys: Sequence[GnbKey]) -> Tuple[List[TimingRow], Counter]:
    latest = {}
    rows: List[TimingRow] = []
    rejections: Counter = Counter()
    seen_rounds = set()
    events = sorted([("slot", event.packet_index, event) for event in slots] + [("ack", event.packet_index, event) for event in acks], key=lambda item: item[1])
    for kind, _packet_index, event in events:
        if kind == "slot":
            latest[event.gnb] = event
            continue
        reason, row, round_key = classify_ack(event, latest, gnb_keys, len(rows))
        if reason == "accepted" and row is not None and round_key is not None and round_key not in seen_rounds:
            seen_rounds.add(round_key)
            rows.append(row)
        else:
            rejections["duplicate_ack" if round_key in seen_rounds else reason] += 1
    return rows, rejections


def classify_ack(ack: AckEvent, latest, gnb_keys: Sequence[GnbKey], round_index: int) -> Tuple[str, Optional[TimingRow], Optional[Tuple[int, ...]]]:
    if any(gnb not in latest for gnb in gnb_keys):
        return "missing_gnb", None, None
    current = tuple(latest[gnb] for gnb in gnb_keys)
    slot_keys = {(event.sfn, event.slot) for event in current}
    if len(slot_keys) != 1:
        return "misaligned_gnb", None, None
    latest_ts = max(event.timestamp_us for event in current)
    if ack.timestamp_us <= latest_ts:
        return "ack_before_latest_slot", None, None
    sfn, slot = next(iter(slot_keys))
    row = TimingRow(round_index, ack, sfn, slot, min(event.timestamp_us for event in current), latest_ts, len(gnb_keys), tuple(sorted({event.gnb[0] for event in current})))
    return "accepted", row, tuple(event.packet_index for event in current)


def write_csv(summary: Analysis, handle: TextIO) -> None:
    writer = csv.writer(handle)
    writer.writerow(["round_index", "proxy_id", "sfn", "slot", "gnb_count", "gnb_ips", "first_slot_ts_us", "latest_slot_ts_us", "ack_ts_us", "slot_spread_us", "wait_us", "wait_ms", "ack_packet", "ack_slot_byte"])
    for row in summary.rows:
        writer.writerow([row.round_index, row.ack.proxy_id, row.sfn, row.slot, row.gnb_count, ";".join(row.gnb_ips), row.first_slot_ts_us, row.latest_slot_ts_us, row.ack.timestamp_us, row.slot_spread_us, row.wait_us, "%.6f" % (row.wait_us / 1000.0), row.ack.packet_index, row.ack.slot_byte])


def plot_cdfs(summary: Analysis, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8))
    plot_one_cdf(axes[0], [row.wait_us / 1000.0 for row in summary.rows], "Proxy wait after latest gNB slot indication (ms)")
    plot_one_cdf(axes[1], [float(row.slot_spread_us) for row in summary.rows], "gNB slot indication spread (us)")
    fig.suptitle("Proxy wait CDF (n=%d)" % len(summary.rows), fontsize=10)
    fig.tight_layout()
    fig.savefig(out_path, format="pdf", bbox_inches="tight")
    plt.close(fig)


def plot_one_cdf(ax, values: Sequence[float], xlabel: str) -> None:
    ordered = sorted(values)
    y_values = [(index + 1) / len(ordered) for index in range(len(ordered))]
    ax.step(ordered, y_values, where="post", linewidth=1.5)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("CDF")
    ax.set_ylim(0.0, 1.0)
    ax.grid(True, which="both", linestyle=":", linewidth=0.6)


def percentile_text(values: Sequence[float]) -> str:
    ordered = sorted(values)
    return "n={n} min={min:.6f} p50={p50:.6f} p90={p90:.6f} p99={p99:.6f} max={max:.6f}".format(n=len(ordered), min=ordered[0], p50=ordered[(len(ordered) - 1) // 2], p90=ordered[int((len(ordered) - 1) * 0.90)], p99=ordered[int((len(ordered) - 1) * 0.99)], max=ordered[-1])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Measure proxy wait time from gNB SLOT_INDICATION to proxy globalsc ACK.")
    parser.add_argument("pcap", type=Path, help="classic Linux-SLL2 pcap file")
    parser.add_argument("--csv-out", "--csv", dest="csv_out", type=Path, required=True, help="raw timing CSV output path")
    parser.add_argument("--out", "--pdf", dest="out", type=Path, required=True, help="output PDF path")
    parser.add_argument("--proxy-ip", default="10.3.1.1", help="proxy IP address")
    parser.add_argument("--globalsc-ip", default="10.4.1.1", help="globalsc IP address")
    parser.add_argument("--globalsc-port", type=int, default=6000, help="globalsc UDP ACK port")
    parser.add_argument("--gnb-network", type=ipaddress.IPv4Network, default=ipaddress.IPv4Network("10.2.0.0/16"), help="IPv4 network containing gNBs")
    parser.add_argument("--expected-gnb-count", type=int, help="require this many discovered gNB P7 flows")
    return parser


def config_from_args(args: argparse.Namespace) -> Config:
    if args.expected_gnb_count is not None and not 1 <= args.expected_gnb_count <= MAX_GNBS:
        raise PcapError("--expected-gnb-count must be between 1 and %d" % MAX_GNBS)
    return Config(args.proxy_ip, args.globalsc_ip, args.globalsc_port, args.gnb_network, args.expected_gnb_count)


def main(argv: Sequence[str]) -> int:
    try:
        args = build_parser().parse_args(argv)
        summary = analyze_capture(args.pcap, config_from_args(args))
        with args.csv_out.open("w", newline="", encoding="utf-8") as handle:
            write_csv(summary, handle)
        plot_cdfs(summary, args.out)
    except (OSError, PcapError, struct.error) as error:
        print("error: %s" % error, file=sys.stderr)
        return 1
    print("Capture: %s" % summary.path)
    print("Discovered gNB flows: %d" % len(summary.gnb_keys))
    print("Slot indications: %d; proxy ACKs: %d" % (summary.slot_events, summary.ack_events))
    print("Rows written: %d" % len(summary.rows))
    print("Rejected ACKs: %s" % dict(sorted(summary.rejections.items())))
    print("wait_ms: %s" % percentile_text([row.wait_us / 1000.0 for row in summary.rows]))
    print("slot_spread_us: %s" % percentile_text([float(row.slot_spread_us) for row in summary.rows]))
    print("CSV: %s" % args.csv_out)
    print("PDF: %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
