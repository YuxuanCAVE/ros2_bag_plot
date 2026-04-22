# Bag Analysis Scripts

These scripts export ROS 2 bag data to CSV and generate basic result plots for controller analysis.

## Workspace Layout

Recommended workspace structure:

```text
workspace/
├─ bags/
│  ├─ run_001/
│  ├─ run_002/
│  └─ ...
└─ scripts/
   ├─ export_controller_record_csv.py
   ├─ export_controller_command_csv.py
   ├─ plot_controller_results.py
   └─ README.md
```

The scripts do not depend on a fixed absolute path. You only need to pass the correct bag directory or CSV path when running them.

## Requirements

- Python 3.10 or newer
- ROS 2 bag storage format: `sqlite3` / `.db3`
- `matplotlib` is required only for plotting

Install plotting dependency if needed:

```bash
python3 -m pip install matplotlib
```

## What Each Script Does

- `export_controller_record_csv.py`
  Exports `/controller_record` to `controller_record.csv`
- `export_controller_command_csv.py`
  Exports `/controller_command` if present, otherwise falls back to `/command`, and writes `controller_command.csv`
- `plot_controller_results.py`
  Reads `controller_record.csv` and generates:
  - `path_tracking.png`
  - `speed_tracking.png`
  - `tracking_error.png`
  - `steering.png`
  - `throttle_brake.png`

## Linux Usage

From the workspace root:

```bash
python3 scripts/export_controller_record_csv.py bags/run_001
python3 scripts/export_controller_command_csv.py bags/run_001
python3 scripts/plot_controller_results.py bags/run_001
```

Batch plotting for all bag folders:

```bash
python3 scripts/plot_controller_results.py bags --batch
```

## Windows Usage

From the workspace root:

```powershell
python .\scripts\export_controller_record_csv.py .\bags\run_001
python .\scripts\export_controller_command_csv.py .\bags\run_001
python .\scripts\plot_controller_results.py .\bags\run_001
```

Batch plotting for all bag folders:

```powershell
python .\scripts\plot_controller_results.py .\bags --batch
```

## Output Files

By default, the scripts write outputs into the bag directory:

- `controller_record.csv`
- `controller_command.csv`
- `path_tracking.png`
- `speed_tracking.png`
- `tracking_error.png`
- `steering.png`
- `throttle_brake.png`

## Notes

- The export scripts currently support `.db3` bags only.
- The plotting script reads `controller_record.csv` only.
- `steering.png` plots `steering_command` only.
- If a CSV contains invalid empty rows, the plotting script skips them automatically.
