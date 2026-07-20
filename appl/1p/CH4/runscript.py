import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


APP_TARGET = "appl_1pnc_box_CH4"
DEFAULT_CASES_FILE = "optimised_validation_cases_ch4.json"
DEFAULT_NUM_CORES = os.environ.get("SLURM_NTASKS", "2")
DEFAULT_OPERATIONAL_CYCLES = float(os.environ.get("NUM_OPERATIONAL_CYCLES", "10"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run real CH4-cushion simulations for sampled optimised validation cases."
    )
    parser.add_argument(
        "--cases",
        default=os.environ.get("CH4_VALIDATION_CASES", DEFAULT_CASES_FILE),
        help="JSON file produced by PostFun/std_plot_optimisation.py.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Run only the first N cases from the JSON file.",
    )
    parser.add_argument(
        "--start-at",
        type=int,
        default=0,
        help="Zero-based case index to start from.",
    )
    parser.add_argument(
        "--num-cores",
        default=DEFAULT_NUM_CORES,
        help="MPI process count. Defaults to SLURM_NTASKS or 2.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Skip the make step.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without running simulations.",
    )
    return parser.parse_args()


def resolve_case_file(cases_arg: str) -> Path:
    candidate = Path(cases_arg)
    if candidate.exists():
        return candidate.resolve()

    script_dir = Path(__file__).resolve().parent
    candidate = script_dir / cases_arg
    if candidate.exists():
        return candidate.resolve()

    candidate = Path.cwd() / cases_arg
    if candidate.exists():
        return candidate.resolve()

    raise FileNotFoundError(
        f"Could not find validation case file '{cases_arg}'. "
        "Run PostFun/std_plot_optimisation.py first to create "
        f"{DEFAULT_CASES_FILE}, or pass --cases /path/to/cases.json."
    )


def load_cases(path: Path) -> list[dict[str, object]]:
    with path.open("r", encoding="utf-8") as f:
        cases = json.load(f)

    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{path} does not contain a non-empty list of cases.")

    return cases


def case_value(test_case: dict[str, object], key: str) -> str:
    if key not in test_case or test_case[key] is None:
        raise KeyError(f"Case {test_case.get('name', '<unnamed>')} is missing '{key}'")
    return str(test_case[key])


def calculate_t_end(test_case: dict[str, object]) -> str:
    cycle_duration = (
        float(case_value(test_case, "InjectionDurationOp"))
        + float(case_value(test_case, "ExtractionDurationOp"))
    )
    operational_cycles = float(test_case.get("OperationalCycles", DEFAULT_OPERATIONAL_CYCLES))
    t_end = (
        float(case_value(test_case, "InjectionDurationDev"))
        + operational_cycles * cycle_duration
    )
    return format(t_end, ".15g")


def cleanup_outputs(include_json: bool, protected_paths: set[Path] | None = None) -> None:
    protected_paths = protected_paths or set()
    patterns = ["*.vtu", "*.pvtu", "*.pvd"]
    if include_json:
        patterns.append("*.json")

    for pattern in patterns:
        for path in Path.cwd().glob(pattern):
            resolved = path.resolve()
            if resolved in protected_paths:
                continue
            path.unlink(missing_ok=True)


def build_command(test_case: dict[str, object], num_cores: str) -> list[str]:
    params = "params.input"
    return [
        "mpirun",
        "-np",
        str(num_cores),
        APP_TARGET,
        params,
        "-Problem.InitialTemperature",
        case_value(test_case, "InitialTemperature"),
        "-Problem.Name",
        case_value(test_case, "name"),
        "-TimeLoop.MaxTimeStepSize",
        case_value(test_case, "MaxTimeStepSize"),
        "-BoundaryConditions.CushionGasType",
        str(test_case.get("CushionGasType", "CH4")),
        "-BoundaryConditions.InjectionRateDev",
        case_value(test_case, "InjectionRateDev"),
        "-BoundaryConditions.InjectionRateOp",
        case_value(test_case, "InjectionRateOp"),
        "-BoundaryConditions.ProductionRate",
        case_value(test_case, "ProductionRate"),
        "-BoundaryConditions.Well_Height",
        case_value(test_case, "Well_Height"),
        "-BoundaryConditions.Pressure_TOP",
        case_value(test_case, "Pressure_TOP"),
        "-SpatialParams.ReferencePermeability",
        case_value(test_case, "ReferencePermeability"),
        "-SpatialParams.ReferencePorosity",
        case_value(test_case, "ReferencePorosity"),
        "-TimeLoop.TEnd",
        calculate_t_end(test_case),
        "-BoundaryConditions.InjectionDurationDev",
        case_value(test_case, "InjectionDurationDev"),
        "-BoundaryConditions.InjectionDurationOp",
        case_value(test_case, "InjectionDurationOp"),
        "-BoundaryConditions.ExtractionDurationOp",
        case_value(test_case, "ExtractionDurationOp"),
    ]


def main() -> None:
    args = parse_args()
    case_file = resolve_case_file(args.cases)
    cases = load_cases(case_file)

    selected_cases = cases[args.start_at :]
    if args.limit is not None:
        selected_cases = selected_cases[: args.limit]

    if not selected_cases:
        raise ValueError("No validation cases selected.")

    # if not args.skip_build:
    #     build_cmd = ["make", APP_TARGET]
    #     print(" ".join(build_cmd))
    #     if not args.dry_run:
    #         subprocess.run(build_cmd, check=True)

    if args.dry_run:
        print("Dry run: not deleting old output files.")
    else:
        cleanup_outputs(include_json=True, protected_paths={case_file})
        print("Deleted old .vtu, .pvtu, .pvd, and simulation .json files.")

    for idx, test_case in enumerate(selected_cases, start=args.start_at):
        print(f"\n[{idx + 1}/{len(cases)}] Running {case_value(test_case, 'name')}")
        command = build_command(test_case, args.num_cores)
        print(" ".join(command))
        if not args.dry_run:
            subprocess.run(command, check=True)

            merge_script = Path("vtk-merge-multi.py")
            if merge_script.exists():
                subprocess.run([sys.executable, str(merge_script)], check=True)

        if not args.dry_run:
            cleanup_outputs(include_json=False)


if __name__ == "__main__":
    main()
