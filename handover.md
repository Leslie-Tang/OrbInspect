# OrbInspect Windows paper handover

Updated: 2026-08-12, Asia/Shanghai

## Purpose

This handover is for finishing the manuscript on Windows. The required Ubuntu
24.04.4 / ROS 2 Jazzy / Gazebo Harmonic work for the paper's current,
single-task ROS claim is complete. Windows is for LaTeX, text, tables, and
already-generated figures; it is not expected to run or validate ROS.

## Evidence boundary to preserve

The manuscript claims one corrected ROS 2 closed-loop validation task. It does
not claim a corrected paired ROS ADP-versus-local-search campaign.

- Keep the one-task wording in `OrbInspectLatex/main.tex` and
  `OrbInspectLatex/sections/ros_verification_results.tex`.
- Do not restore numerical claims or figures from the obsolete
  translation-only ROS campaign.
- Do not describe Gazebo physics as the state source. The ROS-native HCW node
  propagated spacecraft state; Gazebo and RViz2 were visual interfaces.
- Coverage was credited from frozen geometric visibility masks, not image
  pixels or closed-loop image processing.

## Manuscript figure and video source of record

The manuscript's Fig. 7 and accepted video remain sourced from:

`data/results/ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812/`

This media-backed run contains the raw RViz and Gazebo-camera streams used to
generate the video and camera-view figure. Its paper-facing values are:

- 10 of 10 credited observations;
- 81.3314698% final coverage;
- mission completion at 900.0066 s;
- 18,918 recorded trajectory samples;
- zero swept mesh crossings;
- 5.692128 m minimum finite-body clearance above the required 2 m margin;
- peak filtered acceleration 0.0600 m/s^2.

Paper assets:

- `OrbInspectLatex/figures/ros_key_camera_views_trajectory.pdf`
- `OrbInspectLatex/figures/ros_key_camera_views_trajectory.png`
- `OrbInspectLatex/figures/ros_key_camera_views/`
- `OrbInspectLatex/scripts/generate_ros_key_camera_views_figure.py`
- `OrbInspectLatex/main.pdf`

The figure and video manifests were verified against all retained sources.
Do not regenerate Fig. 7 from a different ROS run without intentionally
updating every corresponding manuscript value and provenance record.

## Final rosbag-complete confirmation run

A second corrected graphical execution was recorded specifically to close the
paper-grade rosbag and environment-snapshot gaps:

`data/results/20260812_174012_ros_final_validation002_radius080/`

It contains:

- `config_snapshot/environment.json` with Ubuntu, kernel, CPU, Python, ROS,
  RViz, and Gazebo versions;
- `config_snapshot/run_manifest.json` with `record_bag: true` and the actual
  dirty execution checkout state;
- all six required CSV files;
- the retained ROS launch log;
- a 2.0 GiB Jazzy MCAP rosbag;
- `summary.json` and `summary.md`;
- the independent version-2 full-mesh finite-body audit;
- `SHA256SUMS.txt` for transfer verification.

Final confirmation result:

- 10 of 10 observations credited;
- 81.3314698% final coverage;
- mission completion at 900.0083 s;
- 18,927 trajectory samples and 18,926 control samples;
- zero swept mesh crossings;
- 5.707542 m minimum finite-body clearance above the required margin;
- all execution-audit gates passed.

The bag contains 152,348 messages on all 12 active mission topics. The requested
paper topic set also names online-planner/current-waypoint topics that were
inactive because this run replayed a frozen offline route. Its main MCAP
SHA-256 is:

`81f962360fd845b68608fb4b6d2daa970273a0c0392cb07a84bf02b0574744f6`

This run confirms the archived ROS topic record but did not capture replacement
raw videos. It therefore supplements rather than replaces the manuscript's
media-backed source run.

## Corrected route export

The final corrected route bundle is:

`data/results/ros_verification_inputs_full_transform_radius080_20260812/`

Its manifest records 124 routes: two methods for 12 validation, 30 test, and
20 distribution-shift scenarios. The routes use the complete glTF hierarchy
and a 0.80 m chaser radius. They are exported and hash-checked, but they have
not been executed as a new 124-run corrected ROS campaign. Such execution is
needed only if the paper is expanded to claim paired ROS method superiority.

## Files that Git will not transfer automatically

The four curated evidence directories below are explicitly included despite
the general `data/results/*` ignore rule. The MCAP and retained videos use Git
LFS. A Windows clone must install Git LFS and successfully download the LFS
objects; a pointer-only clone does not contain usable media or rosbag data.

At minimum preserve:

1. `data/results/ros_rviz_full_planning_demo_corrected_validation002_radius080_20260812/`
2. `data/results/20260812_174012_ros_final_validation002_radius080/`
3. `data/results/ros_verification_inputs_full_transform_radius080_20260812/`
4. `data/results/adp_future_full_transform_radius080_20260812/`
5. `OrbInspectLatex/figures/ros_key_camera_views_trajectory.pdf`
6. `OrbInspectLatex/figures/ros_key_camera_views_trajectory.png`
7. `OrbInspectLatex/figures/ros_key_camera_views/`
8. `OrbInspectLatex/scripts/generate_ros_key_camera_views_figure.py`
9. all current modified and untracked source/LaTeX files reported by
   `git status --short`.

The repository also has many intentional source and manuscript modifications.
Do not assume a checkout, pull, reset, or branch switch preserves changes that
have not yet been committed and pushed.

On Windows, install Git LFS before cloning or fetching the evidence:

```powershell
git lfs install
git lfs pull
```

## Windows checksum verification

Run PowerShell from the repository root after copying the final bag bundle:

```powershell
$manifest = "data/results/20260812_174012_ros_final_validation002_radius080/SHA256SUMS.txt"
$failed = $false
Get-Content $manifest | ForEach-Object {
    if ($_ -match '^([0-9a-f]{64})  (.+)$') {
        $expected = $Matches[1]
        $path = $Matches[2]
        $actual = (Get-FileHash -Algorithm SHA256 $path).Hash.ToLower()
        if ($actual -ne $expected) {
            Write-Error "Hash mismatch: $path"
            $failed = $true
        }
    }
}
if ($failed) { throw "OrbInspect transfer verification failed" }
```

The command should finish without an error. Hashing the 2.0 GiB MCAP may take
some time.

## Windows manuscript workflow

The current manuscript builds as a 15-page PDF. From PowerShell with a TeX Live
installation:

```powershell
Set-Location OrbInspectLatex
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
```

If `latexmk` is unavailable, run `pdflatex`, `bibtex`, and `pdflatex` twice.
Fig. 7 should appear on page 14. No ROS installation is required to compile the
paper because the publication PDFs are already present.

## Known, non-blocking details

- `planner.csv` is header-only because planning was performed offline and ROS
  replayed a frozen route. No online planner node was part of these executions.
- Both 5x graphical runs passed the reference-count completion gate, although
  the nominal maximum inter-message-gap subcheck was false. The paper correctly
  defines and claims the reference-count gate, not a strict per-gap guarantee.
- Absolute Linux paths remain in some provenance JSON fields. Hashes and
  paper-facing paths are portable; do not rewrite archived JSON merely to make
  the paths look Windows-native.
- The old translation-only ROS evidence remains quarantined and must not be
  cited as valid safety or comparison evidence.

## Last Linux validation

Completed successfully on Ubuntu 24.04.4 LTS with ROS 2 Jazzy and Gazebo Sim
8.11.0 (Harmonic):

- `colcon build --symlink-install`: 12 packages built;
- package discovery: 12 `orbinspect_*` packages;
- focused dynamics/controller/safety/evidence tests: 47 passed;
- full `colcon test`: 148 tests, 0 failures, 10 expected skips;
- manuscript `latexmk`: successful, 15 pages;
- final rosbag inspection: valid Jazzy MCAP, 152,348 messages on 12 active topics;
- final full-mesh audit: passed.

## Returning to Ubuntu

If ROS evidence must be regenerated, use Ubuntu 24.04.4 and ROS 2 Jazzy:

```bash
cd /home/rugang/robotics/projects/OrbInspect
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch orbinspect_bringup demo_corrected_rviz.launch.py
```

The corrected demo now records the paper topic rosbag by default. Pass
`record_bag:=false` only for a disposable visualization check. Always use a new
run ID and never overwrite either retained source-of-record directory.
