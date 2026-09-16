#!/usr/bin/env python3
"""Materialize the independently certified all-solvable pilot benchmark.

The primary planner benchmark is selected from an independent feasibility
certificate produced before any ADP evaluation. Cases that fail that certificate
remain in a separate visibility-loss stress-test file; they are never silently
discarded from the experiment record.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import median


METHODS = (
    "incumbent",
    "one_step_adp",
    "adaptive_rollout_adp",
    "independent_milp",
)
SPLITS = ("reference", "nominal", "shifted")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def materialize(output: Path) -> dict:
    raw = output / "raw"
    certificates = json.loads((raw / "feasibility.json").read_text())
    scenarios = json.loads((raw / "scenarios.json").read_text())
    results = json.loads((raw / "benchmark_results.json").read_text())
    by_case = {row["scenario_id"]: row for row in certificates}
    assert len(by_case) == len(certificates)
    solvable = sorted(
        scenario["scenario_id"]
        for scenario in scenarios
        if by_case[scenario["scenario_id"]]["status"] == "feasible"
    )
    stress = sorted(
        scenario["scenario_id"]
        for scenario in scenarios
        if by_case[scenario["scenario_id"]]["status"] != "feasible"
    )
    assert len(solvable) + len(stress) == len(scenarios)
    solvable_set = set(solvable)
    stress_set = set(stress)
    subset = [row for row in results if row["scenario_id"] in solvable_set]
    stress_rows = [row for row in results if row["scenario_id"] in stress_set]
    assert len(subset) == len(solvable) * len(METHODS)
    assert len(stress_rows) == len(stress) * len(METHODS)

    case_rows = [
        {
            "scenario_id": scenario["scenario_id"],
            "graph_id": scenario["graph_id"],
            "split": scenario["split"],
            "seed": scenario["seed"],
            "independent_status": by_case[scenario["scenario_id"]]["status"],
            "independent_reason": by_case[scenario["scenario_id"]]["reason"],
            "independent_optimal": by_case[scenario["scenario_id"]]["optimal"],
        }
        for scenario in scenarios
    ]
    write_json(raw / "solvable_benchmark_cases.json", [
        row for row in case_rows if row["scenario_id"] in solvable_set
    ])
    write_csv(raw / "solvable_benchmark_cases.csv", [
        row for row in case_rows if row["scenario_id"] in solvable_set
    ])
    write_json(raw / "visibility_stress_cases.json", [
        row for row in case_rows if row["scenario_id"] in stress_set
    ])
    write_csv(raw / "visibility_stress_cases.csv", [
        row for row in case_rows if row["scenario_id"] in stress_set
    ])
    write_json(raw / "solvable_benchmark_results.json", subset)
    write_csv(raw / "solvable_benchmark_results.csv", subset)
    write_json(raw / "visibility_stress_results.json", stress_rows)
    write_csv(raw / "visibility_stress_results.csv", stress_rows)

    summary: dict = {
        "benchmark_name": "independently_certified_all_solvable_pilot",
        "selection_rule": "independent_feasibility_status == feasible",
        "selection_precedes_planner_evaluation": True,
        "all_generated_cases": len(scenarios),
        "all_solvable_cases": len(solvable),
        "visibility_stress_cases": len(stress),
        "unresolved_cases": sum(
            by_case[case]["status"] == "unresolved" for case in stress
        ),
        "case_ids": solvable,
        "stress_case_ids": stress,
        "splits": {},
        "methods": {},
    }
    for split in SPLITS:
        split_cases = [
            case for case in case_rows
            if case["scenario_id"] in solvable_set and case["split"] == split
        ]
        summary["splits"][split] = {"all_solvable_cases": len(split_cases)}
        for method in METHODS:
            rows = [
                row for row in subset
                if row["split"] == split and row["method"] == method
            ]
            assert len(rows) == len(split_cases)
            summary["methods"].setdefault(method, {})[split] = {
                "cases": len(rows),
                "completed": sum(bool(row["success"]) for row in rows),
                "completion_rate": (
                    sum(bool(row["success"]) for row in rows) / len(rows)
                    if rows else None
                ),
                "median_time_s": median(row["online_time_s"] for row in rows),
                "proven_optimum_cases": sum(
                    row["independent_optimal"] for row in rows
                ),
            }
    summary["methods"] = {
        method: {
            **summary["methods"][method],
            "all": {
                "cases": sum(summary["methods"][method][split]["cases"] for split in SPLITS),
                "completed": sum(summary["methods"][method][split]["completed"] for split in SPLITS),
                "completion_rate": sum(summary["methods"][method][split]["completed"] for split in SPLITS) / len(solvable),
                "proven_optimum_cases": sum(summary["methods"][method][split]["proven_optimum_cases"] for split in SPLITS),
            },
        }
        for method in METHODS
    }
    write_json(raw / "solvable_benchmark_summary.json", summary)

    manifest_files = [
        raw / name for name in (
            "feasibility.json",
            "scenarios.json",
            "benchmark_results.json",
            "solvable_benchmark_cases.json",
            "solvable_benchmark_cases.csv",
            "visibility_stress_cases.json",
            "visibility_stress_cases.csv",
            "solvable_benchmark_results.json",
            "solvable_benchmark_results.csv",
            "visibility_stress_results.json",
            "visibility_stress_results.csv",
            "solvable_benchmark_summary.json",
        )
    ]
    manifest = {
        "benchmark_name": summary["benchmark_name"],
        "source_hashes": {str(path.relative_to(output)): sha(path) for path in manifest_files[:3]},
        "derived_hashes": {str(path.relative_to(output)): sha(path) for path in manifest_files[3:]},
        "all_generated_cases": len(scenarios),
        "all_solvable_cases": len(solvable),
        "visibility_stress_cases": len(stress),
    }
    write_json(raw / "solvable_benchmark_manifest.json", manifest)
    print(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    materialize(args.output.resolve())


if __name__ == "__main__":
    main()
