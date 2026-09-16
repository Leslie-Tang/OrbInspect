# Viewpoint feasibility pilot evidence

This is a verified copy of the completed local development experiment
`data/results/20260914_073800_viewpoint_feasibility_pilot/` in the parent repository.
The original result is preserved. `artifact_manifest.json` records hashes for
the 70 audited pilot files; this explanatory README was added for the
manuscript package and is outside that frozen inventory. The derived benchmark
files are hashed separately in `raw/solvable_benchmark_manifest.json`.

Start with [review.md](review.md). The aggregate data are in
[summary.json](summary.json). The primary planner comparison is the
[independently certified all-solvable benchmark](raw/solvable_benchmark_summary.json):
59 cases (3 reference, 30 nominal and 26 shifted), with 59 rows per method.
The four excluded shifted cases are retained in the
[visibility-loss stress-test inventory](raw/visibility_stress_cases.json).
The full per-case results, independent certificates, candidate attempts, three
directed graphs and HCW state/control arrays are in `raw/`. The configuration and
source snapshots are in `config_snapshot/`. The record includes every generated
case and time-limited MILP route.

The copied reports describe the state when the pilot finished, before its results
were incorporated into the manuscript. Their statements that the manuscript was
unchanged refer to that earlier experiment stage. The subsequent manuscript
revision is documented in
[the revision record](../../docs/VIEWPOINT_PILOT_MANUSCRIPT_20260914.md).

The all-solvable subset is selected by an independent feasibility certificate
before planner evaluation, without using any planner result. It is therefore a
feasibility-conditioned success-rate benchmark. This is development evidence on
the same ISS geometry and nine required targets, not a replacement for the
original confirmation or a new independent confirmation.
The artifact reproduces reported numerical claims without requiring a ROS run.
The frozen source snapshots support reconstruction in the parent OrbInspect
repository; they are not claimed to be a standalone ROS workspace. LaTeX uses
only the inlined text/table in `main.tex` and does not execute the experiment.
