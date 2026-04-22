#!/usr/bin/env python3

import argparse
import csv
import sqlite3
import struct
from pathlib import Path
from typing import Iterable


CONTROLLER_RECORD_TOPIC = "/controller_record"
CONTROLLER_RECORD_COLUMNS = [
    "stamp_sec",
    "actual_loop_dt",
    "control_update_dt",
    "ref_idx",
    "x",
    "y",
    "yaw",
    "vx",
    "vy",
    "yaw_rate",
    "ax",
    "xr",
    "yr",
    "psi_ref",
    "kappa_ref",
    "v_ref",
    "e_longitudinal",
    "e_lateral",
    "e_heading",
    "steering_rad",
    "steering_command",
    "accel_cmd",
    "throttle",
    "brake",
    "f_resist",
    "f_required",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export /controller_record messages from a ROS 2 sqlite3 bag to CSV."
    )
    parser.add_argument("bag_path", help="Path to a ROS 2 bag directory or .db3 file.")
    parser.add_argument(
        "-o",
        "--output",
        help="Output CSV path. Defaults to <bag_path>/controller_record.csv.",
    )
    parser.add_argument(
        "--topic",
        default=CONTROLLER_RECORD_TOPIC,
        help=f"Topic to export. Defaults to {CONTROLLER_RECORD_TOPIC}.",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Treat bag_path as a directory containing multiple bag folders.",
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
        raise FileNotFoundError(f"Could not detect sqlite3 rosbag files under {bag_path}")
    return db3_files


def build_output_path(bag_path: Path, output: str | None) -> Path:
    if output:
        return Path(output).expanduser().resolve()
    if bag_path.is_dir():
        return (bag_path / "controller_record.csv").resolve()
    return bag_path.with_name(f"{bag_path.stem}_controller_record.csv").resolve()


def load_available_topics(db3_files: Iterable[Path]) -> dict[str, str]:
    topic_types: dict[str, str] = {}
    for db3_file in db3_files:
        with sqlite3.connect(db3_file) as conn:
            rows = conn.execute("SELECT name, type FROM topics").fetchall()
        for name, msg_type in rows:
            topic_types.setdefault(str(name), str(msg_type))
    return topic_types


def decode_float32_multiarray(blob: bytes, topic: str) -> list[float]:
    value_count = len(CONTROLLER_RECORD_COLUMNS)
    expected_tail_size = 8 + value_count * 4
    if len(blob) < expected_tail_size:
        raise ValueError(
            f"Topic {topic} produced a {len(blob)}-byte payload, which is too small."
        )

    data_offset, actual_count = struct.unpack("<II", blob[-expected_tail_size:-expected_tail_size + 8])
    if data_offset != 0:
        raise ValueError(f"Topic {topic} has unexpected data_offset={data_offset}.")
    if actual_count != value_count:
        raise ValueError(
            f"Topic {topic} produced {actual_count} values, expected {value_count}."
        )

    values = struct.unpack("<" + "f" * value_count, blob[-value_count * 4 :])
    return [float(value) for value in values]


def export_topic_to_csv(bag_path: Path, output_path: Path, topic: str) -> int:
    db3_files = resolve_db3_files(bag_path)
    topic_types = load_available_topics(db3_files)
    if topic not in topic_types:
        available = ", ".join(sorted(topic_types))
        raise ValueError(f"Topic {topic} not found in bag. Available topics: {available}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0

    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(CONTROLLER_RECORD_COLUMNS)

        for db3_file in db3_files:
            with sqlite3.connect(db3_file) as conn:
                rows = conn.execute(
                    """
                    SELECT messages.data
                    FROM messages
                    JOIN topics ON messages.topic_id = topics.id
                    WHERE topics.name = ?
                    ORDER BY messages.timestamp ASC
                    """,
                    (topic,),
                )
                for (blob,) in rows:
                    writer.writerow(decode_float32_multiarray(blob, topic))
                    rows_written += 1

    return rows_written


def export_batch(root_dir: Path, topic: str) -> None:
    bag_dirs = sorted(path for path in root_dir.iterdir() if path.is_dir())
    for bag_dir in bag_dirs:
        try:
            output_path = build_output_path(bag_dir, None)
            rows_written = export_topic_to_csv(bag_dir, output_path, topic)
            print(f"Exported {rows_written} messages from {topic} to {output_path}")
        except Exception as exc:
            print(f"Skipped {bag_dir}: {exc}")


def main() -> int:
    args = parse_args()
    bag_path = Path(args.bag_path).expanduser().resolve()
    if not bag_path.exists():
        raise FileNotFoundError(f"Bag path does not exist: {bag_path}")

    if args.batch:
        if not bag_path.is_dir():
            raise ValueError("--batch requires bag_path to be a directory.")
        export_batch(bag_path, args.topic)
        return 0

    output_path = build_output_path(bag_path, args.output)
    rows_written = export_topic_to_csv(bag_path, output_path, args.topic)
    print(f"Exported {rows_written} messages from {args.topic} to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
