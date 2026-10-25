from __future__ import annotations

import ipaddress
import struct
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from globalsc_barrier.model import (
    ACK_COMPONENT,
    ACK_PROXY,
    AckEvent,
    Analysis,
    ArrivalRow,
    CandidateRound,
    IssueBurst,
    ParticipantId,
    UdpDatagram,
)
from globalsc_barrier.pcap import iter_pcap_udp


@dataclass(frozen=True)
class AnalysisConfig:
    globalsc_ip: ipaddress.IPv4Address
    globalsc_port: int
    component_net: ipaddress.IPv4Network
    proxy_net: ipaddress.IPv4Network


DEFAULT_CONFIG = AnalysisConfig(
    ipaddress.IPv4Address("10.4.1.1"),
    6000,
    ipaddress.IPv4Network("10.1.0.0/16"),
    ipaddress.IPv4Network("10.3.0.0/16"),
)


def analyze_pcap(path: Path, config: AnalysisConfig = DEFAULT_CONFIG) -> Analysis:
    bursts: list[IssueBurst] = []
    acks: list[AckEvent] = []
    for datagram in iter_pcap_udp(path):
        slot = issue_slot_from_datagram(datagram, config)
        if slot is not None:
            append_issue_burst(bursts, slot, datagram.timestamp_s)
        ack = ack_from_datagram(datagram, config)
        if ack is not None:
            acks.append(ack)
    return complete_rounds(candidate_rounds(bursts, acks))


def ack_from_datagram(datagram: UdpDatagram, config: AnalysisConfig) -> AckEvent | None:
    if datagram.dst_ip != config.globalsc_ip or datagram.dst_port != config.globalsc_port:
        return None
    if len(datagram.payload) != 6:
        return None

    ack_type, participant_id, _slot = struct.unpack("<BIB", datagram.payload)
    if ack_type == ACK_PROXY:
        if datagram.src_ip not in config.proxy_net:
            return None
    elif ack_type == ACK_COMPONENT:
        if datagram.src_ip not in config.component_net:
            return None
    else:
        return None
    return AckEvent(datagram.timestamp_s, ack_type, ParticipantId(participant_id))


def issue_slot_from_datagram(datagram: UdpDatagram, config: AnalysisConfig) -> int | None:
    if datagram.src_ip != config.globalsc_ip or len(datagram.payload) != 1:
        return None
    if datagram.dst_ip not in config.component_net and datagram.dst_ip not in config.proxy_net:
        return None
    return datagram.payload[0]


def append_issue_burst(bursts: list[IssueBurst], slot: int, timestamp_s: float) -> None:
    if bursts and bursts[-1].slot == slot:
        last = bursts[-1]
        bursts[-1] = IssueBurst(last.slot, last.start_time_s, timestamp_s)
        return
    bursts.append(IssueBurst(slot, timestamp_s, timestamp_s))


def candidate_rounds(bursts: Sequence[IssueBurst], acks: Sequence[AckEvent]) -> tuple[CandidateRound, ...]:
    rounds: list[CandidateRound] = []
    for index in range(len(bursts) - 1):
        start = bursts[index].end_time_s
        stop = bursts[index + 1].start_time_s
        round_acks = tuple(ack for ack in acks if start < ack.timestamp_s < stop)
        rounds.append(CandidateRound(bursts[index].slot, start, round_acks))
    return tuple(rounds)


def complete_rounds(candidates: Sequence[CandidateRound]) -> Analysis:
    participant_sets = [candidate.participants for candidate in candidates if candidate.participants]
    if not participant_sets:
        return Analysis(tuple(), 0, 0, len(candidates), 0)

    complete_set = infer_complete_participant_set(participant_sets)
    arrivals: list[ArrivalRow] = []
    skipped = 0
    complete_round_count = 0
    for candidate in candidates:
        if candidate.participants != complete_set:
            skipped += 1
            continue
        arrivals.extend(arrival_rows(complete_round_count, candidate))
        complete_round_count += 1

    component_count = sum(1 for ack_type, _id in complete_set if ack_type == ACK_COMPONENT)
    proxy_count = sum(1 for ack_type, _id in complete_set if ack_type == ACK_PROXY)
    return Analysis(tuple(arrivals), component_count, proxy_count, skipped, complete_round_count)


def infer_complete_participant_set(
    participant_sets: Iterable[frozenset[tuple[int, ParticipantId]]],
) -> frozenset[tuple[int, ParticipantId]]:
    counts: Counter[frozenset[tuple[int, ParticipantId]]] = Counter(participant_sets)
    return max(counts, key=lambda participant_set: (counts[participant_set], len(participant_set)))


def arrival_rows(round_index: int, candidate: CandidateRound) -> tuple[ArrivalRow, ...]:
    return tuple(
        ArrivalRow(
            round_index=round_index,
            slot=candidate.slot,
            role=role_from_ack_type(ack.ack_type),
            participant_id=ack.participant_id,
            arrival_offset_ms=round((ack.timestamp_s - candidate.issue_time_s) * 1000.0, 6),
        )
        for ack in sorted(candidate.acks, key=lambda event: (event.timestamp_s, event.ack_type, event.participant_id))
    )


def role_from_ack_type(ack_type: int) -> str:
    if ack_type == ACK_PROXY:
        return "proxy"
    return "component"
