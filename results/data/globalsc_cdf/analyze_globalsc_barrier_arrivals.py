#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ipaddress
import sys
from collections.abc import Sequence
from pathlib import Path

from globalsc_barrier.analysis import DEFAULT_CONFIG, AnalysisConfig, analyze_pcap
from globalsc_barrier.pcap import PcapParseError
from globalsc_barrier.report import MatplotlibUnavailableError, write_csv, write_pdf_cdf


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze globalsc barrier arrival offsets from an SLL2 PCAP.")
    parser.add_argument("input_pcap", type=Path)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--globalsc", default=f"{DEFAULT_CONFIG.globalsc_ip}:{DEFAULT_CONFIG.globalsc_port}")
    parser.add_argument("--component-net", default=str(DEFAULT_CONFIG.component_net))
    parser.add_argument("--proxy-net", default=str(DEFAULT_CONFIG.proxy_net))
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> AnalysisConfig:
    host, port_text = args.globalsc.rsplit(":", 1)
    return AnalysisConfig(
        globalsc_ip=ipaddress.IPv4Address(host),
        globalsc_port=int(port_text),
        component_net=ipaddress.IPv4Network(args.component_net),
        proxy_net=ipaddress.IPv4Network(args.proxy_net),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        analysis = analyze_pcap(args.input_pcap, config_from_args(args))
        write_csv(args.csv, analysis.arrivals)
        write_pdf_cdf(args.pdf, analysis.arrivals)
    except (OSError, PcapParseError, MatplotlibUnavailableError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(
        "\n".join(
            (
                f"inferred component count: {analysis.component_count}",
                f"inferred proxy count: {analysis.proxy_count}",
                f"complete round count: {analysis.complete_round_count}",
                f"skipped/incomplete round count: {analysis.skipped_round_count}",
                f"arrival sample count: {analysis.arrival_sample_count}",
                f"csv output: {args.csv}",
                f"pdf output: {args.pdf}",
            )
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
