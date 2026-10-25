from __future__ import annotations

import ipaddress
import struct
from collections.abc import Iterator
from pathlib import Path

from globalsc_barrier.model import UdpDatagram


SLL2_LINKTYPE = 276
SLL2_HEADER_LEN = 20
IPV4_ETHERTYPE = 0x0800
UDP_PROTOCOL = 17


class PcapParseError(Exception):
    """Raised when the input is not a supported classic SLL2 PCAP."""


def parse_pcap_format(header: bytes) -> tuple[str, float]:
    formats = {
        b"\xd4\xc3\xb2\xa1": ("<", 1_000_000.0),
        b"\xa1\xb2\xc3\xd4": (">", 1_000_000.0),
        b"\x4d\x3c\xb2\xa1": ("<", 1_000_000_000.0),
        b"\xa1\xb2\x3c\x4d": (">", 1_000_000_000.0),
    }
    parsed = formats.get(header[:4])
    if parsed is None:
        raise PcapParseError("unsupported PCAP magic")
    return parsed


def iter_pcap_udp(path: Path) -> Iterator[UdpDatagram]:
    with path.open("rb") as handle:
        header = handle.read(24)
        if len(header) != 24:
            raise PcapParseError("truncated PCAP global header")
        endian, timestamp_divisor = parse_pcap_format(header)
        linktype = struct.unpack(endian + "I", header[20:24])[0]
        if linktype != SLL2_LINKTYPE:
            raise PcapParseError(f"expected SLL2 link type 276, found {linktype}")

        while True:
            record_header = handle.read(16)
            if record_header == b"":
                return
            if len(record_header) != 16:
                raise PcapParseError("truncated PCAP packet header")
            sec, frac, incl_len, _orig_len = struct.unpack(endian + "IIII", record_header)
            frame = handle.read(incl_len)
            if len(frame) != incl_len:
                raise PcapParseError("truncated PCAP packet data")
            datagram = parse_sll2_ipv4_udp(sec + (frac / timestamp_divisor), frame)
            if datagram is not None:
                yield datagram


def parse_sll2_ipv4_udp(timestamp_s: float, frame: bytes) -> UdpDatagram | None:
    if len(frame) < SLL2_HEADER_LEN + 28:
        return None
    protocol = struct.unpack("!H", frame[:2])[0]
    if protocol != IPV4_ETHERTYPE:
        return None

    ip_packet = frame[SLL2_HEADER_LEN:]
    version_ihl = ip_packet[0]
    if version_ihl >> 4 != 4:
        return None
    ihl = (version_ihl & 0x0F) * 4
    if ihl < 20 or len(ip_packet) < ihl + 8 or ip_packet[9] != UDP_PROTOCOL:
        return None

    total_len = struct.unpack("!H", ip_packet[2:4])[0]
    if total_len < ihl + 8 or total_len > len(ip_packet):
        return None
    udp_header = ip_packet[ihl : ihl + 8]
    _src_port, dst_port, udp_len, _checksum = struct.unpack("!HHHH", udp_header)
    if udp_len < 8 or ihl + udp_len > total_len:
        return None

    return UdpDatagram(
        timestamp_s=timestamp_s,
        src_ip=ipaddress.IPv4Address(ip_packet[12:16]),
        dst_ip=ipaddress.IPv4Address(ip_packet[16:20]),
        dst_port=dst_port,
        payload=ip_packet[ihl + 8 : ihl + udp_len],
    )
