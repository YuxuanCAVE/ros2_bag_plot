#!/usr/bin/env python3

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot controller result figures from controller_record.csv files."
    )
    parser.add_argument(
        "input_path",
        help="Path to a bag directory, a controller_record.csv file, or a directory containing bag folders.",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Treat input_path as a directory containing multiple bag folders.",
    )
    return parser.parse_args()


def resolve_record_csv(path: Path) -> Path:
    if path.is_file():
        if path.name != "controller_record.csv":
            raise ValueError(f"Expected controller_record.csv, got: {path}")
        return path

    csv_path = path / "controller_record.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing controller_record.csv under {path}")
    return csv_path


def load_record_csv(csv_path: Path) -> dict[str, list[float]]:
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"No CSV header found in {csv_path}")

        data = {name: [] for name in reader.fieldnames}
        skipped_rows = 0
        for row in reader:
            try:
                values = [float(row[name]) for name in reader.fieldnames]
            except (TypeError, ValueError):
                skipped_rows += 1
                continue

            for name, value in zip(reader.fieldnames, values):
                data[name].append(value)

    if not data["stamp_sec"]:
        raise ValueError(f"No data rows found in {csv_path}")
    if skipped_rows:
        print(f"Skipped {skipped_rows} invalid rows in {csv_path}")
    return data


def build_time_axis(data: dict[str, list[float]]) -> list[float]:
    stamps = data["stamp_sec"]
    unique_stamps = len({stamp for stamp in stamps})
    is_strictly_increasing = all(curr > prev for prev, curr in zip(stamps, stamps[1:]))

    if unique_stamps > 1 and is_strictly_increasing:
        t0 = stamps[0]
        return [stamp - t0 for stamp in stamps]

    # `stamp_sec` comes from Float32MultiArray in the bag record stream. At Unix
    # time scales, float32 loses sub-second precision, so repeated values can
    # collapse the whole plot onto a vertical line. Reconstruct elapsed time from
    # the loop delta instead.
    time_axis = [0.0]
    for dt in data["actual_loop_dt"][1:]:
        time_axis.append(time_axis[-1] + dt)
    return time_axis


def save_path_tracking_plot(data: dict[str, list[float]], output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.plot(data["xr"], data["yr"], label="Reference", linewidth=2.0, color="#1f77b4")
    ax.plot(data["x"], data["y"], label="Actual", linewidth=1.8, color="#d62728")
    ax.set_title("Path Tracking")
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.axis("equal")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "path_tracking.png", dpi=180)
    plt.close(fig)


def save_speed_tracking_plot(
    time_axis: list[float], data: dict[str, list[float]], output_dir: Path
) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(time_axis, data["v_ref"], label="v_ref", linewidth=2.0, color="#1f77b4")
    ax.plot(time_axis, data["vx"], label="vx", linewidth=1.8, color="#ff7f0e")
    ax.set_title("Speed Tracking")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Speed [m/s]")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "speed_tracking.png", dpi=180)
    plt.close(fig)


def save_error_plot(time_axis: list[float], data: dict[str, list[float]], output_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(
        time_axis,
        data["e_longitudinal"],
        label="Longitudinal Error",
        linewidth=1.8,
        color="#2ca02c",
    )
    ax.plot(
        time_axis,
        data["e_lateral"],
        label="Lateral Error",
        linewidth=1.8,
        color="#d62728",
    )
    ax.axhline(0.0, color="black", linewidth=1.0, alpha=0.5)
    ax.set_title("Tracking Error")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Error [m]")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "tracking_error.png", dpi=180)
    plt.close(fig)


def save_steering_plot(
    time_axis: list[float], data: dict[str, list[float]], output_dir: Path
) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(
        time_axis,
        data["steering_command"],
        label="Steering Command",
        linewidth=1.8,
        color="#8c564b",
    )
    ax.set_title("Steering")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Steering [rad]")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "steering.png", dpi=180)
    plt.close(fig)


def save_actuation_plot(
    time_axis: list[float], data: dict[str, list[float]], output_dir: Path
) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(time_axis, data["throttle"], label="Throttle", linewidth=1.8, color="#ff7f0e")
    ax.plot(time_axis, data["brake"], label="Brake", linewidth=1.8, color="#1f77b4")
    ax.set_title("Throttle And Brake")
    ax.set_xlabel("Time [s]")
    ax.set_ylabel("Command")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output_dir / "throttle_brake.png", dpi=180)
    plt.close(fig)


def plot_one(record_csv_path: Path) -> None:
    data = load_record_csv(record_csv_path)
    time_axis = build_time_axis(data)
    output_dir = record_csv_path.parent

    save_path_tracking_plot(data, output_dir)
    save_speed_tracking_plot(time_axis, data, output_dir)
    save_error_plot(time_axis, data, output_dir)
    save_steering_plot(time_axis, data, output_dir)
    save_actuation_plot(time_axis, data, output_dir)

    print(f"Generated plots under {output_dir}")


def plot_batch(root_dir: Path) -> None:
    bag_dirs = sorted(path for path in root_dir.iterdir() if path.is_dir())
    for bag_dir in bag_dirs:
        record_csv_path = bag_dir / "controller_record.csv"
        if not record_csv_path.exists():
            print(f"Skipped {bag_dir}: missing controller_record.csv")
            continue
        plot_one(record_csv_path)


def main() -> int:
    args = parse_args()
    input_path = Path(args.input_path).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    if args.batch:
        if not input_path.is_dir():
            raise ValueError("--batch requires a directory input.")
        plot_batch(input_path)
        return 0

    plot_one(resolve_record_csv(input_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
