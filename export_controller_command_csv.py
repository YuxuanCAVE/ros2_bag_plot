#!/usr/bin/env python3

import argparse
import csv
import sqlite3
import struct
from pathlib import Path
from typing import Iterable, Sequence


DEFAULT_TOPIC_CANDIDATES = ("/controller_command", "/command")
COMMAND_COLUMNS = [
    "bag_timestamp_ns",
    "brake",
    "throttle",
    "steering",
    "reserved_0",
    "reserved_1",
    "reserved_2",
    "reserved_3",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export controller command messages from a ROS 2 bag to CSV."
    )
    parser.add_argument("bag_path", help="Path to a ROS 2 bag directory or bag file.")
    parser.add_argument(
        "-o",
        "--output",
        help="Output CSV path. Defaults to <bag_path>/controller_command.csv.",
    )
    parser.add_argument(
        "--topic",
        help=(
            "Topic to export. If omitted, the script tries /controller_command "
            "first and then /command."
        ),
    )
    return parser.parse_args()


def resolve_db3_files(bag_path: Path) -> list[Path]:
    if bag_path.is_file():
        if bag_path.suffix != ".db3":
            raise ValueError(
                f"Only sqlite3 rosbag files are supported without a ROS runtime: {bag_path}"
            )
        return [bag_path]

    db3_files = sorted(bag_path.glob("*.db3"))
    if not db3_files:
        if any(candidate.suffix == ".mcap" for candidate in bag_path.iterdir()):
            raise ValueError(
                f"Found MCAP storage under {bag_path}, which this script does not decode directly."
            )
        raise FileNotFoundError(f"Could not detect sqlite3 rosbag files under {bag_path}")
    return db3_files


def build_output_path(bag_path: Path, output: str | None) -> Path:
    if output:
        return Path(output).expanduser().resolve()
    if bag_path.is_dir():
        return (bag_path / "controller_command.csv").resolve()
    return bag_path.with_name(f"{bag_path.stem}_controller_command.csv").resolve()


def resolve_topic(requested_topic: str | None, available_topics: Sequence[str]) -> str:
    if requested_topic:
        if requested_topic not in available_topics:
            available = ", ".join(sorted(available_topics))
            raise ValueError(
                f"Topic {requested_topic} not found in bag. Available topics: {available}"
            )
        return requested_topic

    for candidate in DEFAULT_TOPIC_CANDIDATES:
        if candidate in available_topics:
            return candidate

    available = ", ".join(sorted(available_topics))
    raise ValueError(
        "Could not find a controller command topic. "
        f"Tried {', '.join(DEFAULT_TOPIC_CANDIDATES)}. Available topics: {available}"
    )


def decode_interface_command(blob: bytes, topic: str) -> list[float]:
    # rosbag2 sqlite3 stores CDR payload bytes. For InterfaceCommand in this bag,
    # `command` is a fixed float32[7] array, preceded by a 4-byte CDR encapsulation header.
    expected_payload_size = 4 + 7 * 4
    if len(blob) != expected_payload_size:
        raise ValueError(
            f"Topic {topic} produced a {len(blob)}-byte payload, "
            f"expected {expected_payload_size} bytes for InterfaceCommand."
        )
    return list(struct.unpack("<7f", blob[4:]))


def load_available_topics(db3_files: Iterable[Path]) -> dict[str, str]:
    topic_types: dict[str, str] = {}
    for db3_file in db3_files:
        with sqlite3.connect(db3_file) as conn:
            rows = conn.execute("SELECT name, type FROM topics").fetchall()
        for name, msg_type in rows:
            topic_types.setdefault(str(name), str(msg_type))
    return topic_types


def export_topic_to_csv(
    bag_path: Path, output_path: Path, requested_topic: str | None
) -> tuple[int, str]:
    db3_files = resolve_db3_files(bag_path)
    topic_types = load_available_topics(db3_files)
    topic = resolve_topic(requested_topic, tuple(topic_types))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(COMMAND_COLUMNS)

        for db3_file in db3_files:
            with sqlite3.connect(db3_file) as conn:
                rows = conn.execute(
                    """
                    SELECT messages.timestamp, messages.data
                    FROM messages
                    JOIN topics ON messages.topic_id = topics.id
                    WHERE topics.name = ?
                    ORDER BY messages.timestamp ASC
                    """,
                    (topic,),
                )
                for timestamp_ns, blob in rows:
                    command_values = decode_interface_command(blob, topic)
                    writer.writerow([int(timestamp_ns), *command_values])
                    rows_written += 1

    return rows_written, topic


def main() -> int:
    args = parse_args()
    bag_path = Path(args.bag_path).expanduser().resolve()
    if not bag_path.exists():
        raise FileNotFoundError(f"Bag path does not exist: {bag_path}")

    output_path = build_output_path(bag_path, args.output)
    rows_written, topic = export_topic_to_csv(bag_path, output_path, args.topic)
    print(f"Exported {rows_written} messages from {topic} to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
