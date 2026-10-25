from __future__ import annotations

from dataclasses import dataclass
from typing import NewType
import ipaddress


ParticipantId = NewType("ParticipantId", int)


ACK_PROXY = 1
ACK_COMPONENT = 2


@dataclass(frozen=True)
class UdpDatagram:
    timestamp_s: float
    src_ip: ipaddress.IPv4Address
    dst_ip: ipaddress.IPv4Address
    dst_port: int
    payload: bytes


@dataclass(frozen=True)
class AckEvent:
    timestamp_s: float
    ack_type: int
    participant_id: ParticipantId

    @property
    def participant(self) -> tuple[int, ParticipantId]:
        return (self.ack_type, self.participant_id)


@dataclass(frozen=True)
class IssueBurst:
    slot: int
    start_time_s: float
    end_time_s: float


@dataclass(frozen=True)
class CandidateRound:
    slot: int
    issue_time_s: float
    acks: tuple[AckEvent, ...]

    @property
    def participants(self) -> frozenset[tuple[int, ParticipantId]]:
        return frozenset(ack.participant for ack in self.acks)


@dataclass(frozen=True)
class ArrivalRow:
    round_index: int
    slot: int
    role: str
    participant_id: ParticipantId
    arrival_offset_ms: float


@dataclass(frozen=True)
class Analysis:
    arrivals: tuple[ArrivalRow, ...]
    component_count: int
    proxy_count: int
    skipped_round_count: int
    complete_round_count: int

    @property
    def arrival_sample_count(self) -> int:
        return len(self.arrivals)
