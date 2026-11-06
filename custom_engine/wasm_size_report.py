#!/usr/bin/env python3
"""Write a size breakdown of a WebAssembly binary."""

import argparse
from pathlib import Path


SECTION_NAMES = {
    0: "custom",
    1: "type",
    2: "import",
    3: "function",
    4: "table",
    5: "memory",
    6: "global",
    7: "export",
    8: "start",
    9: "element",
    10: "code",
    11: "data",
    12: "data-count",
    13: "tag",
}


def read_uleb128(data: bytes, offset: int) -> tuple[int, int]:
    """Read an unsigned LEB128 integer and return (value, next_offset)."""
    value = 0
    shift = 0

    while True:
        if offset >= len(data):
            raise ValueError("Unexpected end of file while reading section length")

        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift

        if byte & 0x80 == 0:
            return value, offset

        shift += 7
        if shift >= 70:
            raise ValueError("Invalid LEB128 integer")


def custom_section_name(payload: bytes) -> str:
    """Get the name stored at the start of a custom section."""
    try:
        name_length, offset = read_uleb128(payload, 0)
        end = offset + name_length
        if end > len(payload):
            return "custom"
        return payload[offset:end].decode("utf-8", errors="replace") or "custom"
    except ValueError:
        return "custom"


def make_report(wasm_path: Path) -> str:
    data = wasm_path.read_bytes()
    if len(data) < 8 or data[:4] != b"\0asm":
        raise ValueError(f"{wasm_path} is not a valid WebAssembly binary")

    sections = []
    offset = 8  # Skip the WebAssembly magic and version header.

    while offset < len(data):
        start = offset
        section_id = data[offset]
        offset += 1

        payload_length, offset = read_uleb128(data, offset)
        payload_end = offset + payload_length
        if payload_end > len(data):
            raise ValueError("Section extends past the end of the WebAssembly file")

        name = SECTION_NAMES.get(section_id, f"section-{section_id}")
        if section_id == 0:
            name = custom_section_name(data[offset:payload_end])

        sections.append((name, payload_end - start))
        offset = payload_end

    total_size = len(data)
    lines = [
        f"WebAssembly size report: {wasm_path}",
        f"Total: {total_size:,} bytes",
        "",
        f"{'Section':<24} {'Bytes':>12} {'Percent':>9}",
        f"{'-' * 24} {'-' * 12} {'-' * 9}",
    ]

    for name, size in sorted(sections, key=lambda section: section[1], reverse=True):
        percent = size * 100 / total_size if total_size else 0
        lines.append(f"{name:<24} {size:>12,} {percent:>8.2f}%")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wasm_file", type=Path)
    parser.add_argument("output_file", type=Path)
    args = parser.parse_args()

    report = make_report(args.wasm_file)
    args.output_file.write_text(report, encoding="utf-8")
    print(report, end="")


if __name__ == "__main__":
    main()
