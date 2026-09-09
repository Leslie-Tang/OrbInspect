# IEEE TAES revision plan: complete inspection of predefined targets

Date: 2026-09-05. Status: proposed revision plan; no new experiments have been run and no manuscript results or figures have been replaced under this plan.

## 1. Recommendation and evidence behind it

Reframe the primary task as completing a predefined set of inspection requirements at minimum audited graph cost. Let the planner choose the observation viewpoints and their order. Report broader surface coverage as a separate contextual measurement. Preserve the existing figure style and layout throughout the revision.

The concern is justified, but there is no demonstrated universal percentage at which an inspection paper becomes convincing. The current 80% threshold is a stipulated stopping condition, not evidence that the planner can cover only 80%. The more consequential questions are what must be inspected, why those regions matter, and whether every required observation is completed to a stated geometric or imaging criterion.

Current evidence establishes the following:

| Item | Verified interpretation | Revision consequence |
| --- | --- | --- |
| Current primary target | At least 80% of scenario-weighted target mass in a 41-target candidate-observable library, sampled from 90 surface targets | Do not call this overall ISS coverage |
| Priority weights | Scenario weights combine represented area with randomized priority multipliers | Separate physical area weights from mission priorities |
| Representative route | 33/41 observable samples and 33/90 total samples: 80.49% and 36.67% by count, versus the reported 80.41% priority-weighted score | The three denominators are not interchangeable; the sampled-area estimate is not a dense physical surface audit |
| Candidate-library ceiling | 41/90 = 45.56% of the original sampled targets can be seen by at least one retained observation | Raising the stopping threshold alone cannot establish whole-station inspection |
| Existing 95%/98% experiment | Success in 23/30 and 10/30 scenarios; available-view unions pass the corresponding threshold in 27/30 and 19/30 | Distinguish a visibility upper-bound screen from directed-route feasibility |
| Existing six sentinels | Selected using observability across all 50 test and shifted inventories; imposing them changed no route or outcome | Retain as exploratory history; these are not independently justified mission-critical targets |
| Existing ROS case | All ten planned observations were credited; coverage derives from frozen geometric masks | It validates execution of that route, not defect detection or a new required-region mission |

Evidence anchors: `OrbInspectLatex/main.tex`, especially the coverage definition, frozen mesh problem, coverage stress test, and representative case; `data/results/adp_future_full_transform_radius080_20260812/`; `data/results/high_coverage_key_targets_20260904/`; and `OrbInspectLatex/sections/ros_verification_results.tex`.

Mission-directed inspection has an operational rationale: NASA's [VIPIR description](https://technology.nasa.gov/patent/GSC-TOPS-360) describes visual inspection of specific spacecraft components and restricted locations. NASA's [Robotic External Leak Locator](https://www.nasa.gov/isam/robotic-external-leak-locator/) addresses locating a cooling-system leak and confirming a repair. These support targeted inspection as an application concept; RELL uses different sensing, and neither source supplies a critical-target list or numerical acceptance threshold for this mesh.

High-coverage research also exists: [van Wijk et al.](https://arxiv.org/abs/2308.02743) report an interquartile mean inspected-point percentage of 98.82% for their simulated illumination-aware task. That percentage is not directly comparable without matching geometry, sensors, denominators, and constraints. The manuscript should explain its mission specification rather than use another study's percentage as an acceptance rule.

## 2. Lock the revised argument and terminology

Proposed argument to test: OrbInspect uses viability-preserving rollout over audited orbital arcs to complete all predefined inspection requirements, and its resource cost is compared with matched feasible baseline planners under the same task specification.

This is a proposed claim, not a result already demonstrated. Any claim of lower cost, superior completion, or 100% execution success must follow the new experiments.

Use these terms consistently:

- **Required inspection region / region of interest (ROI):** a physical surface patch or component region specified by the mission.
- **Required inspection target:** a sampled point or inspection item within that region, with an explicit acceptance rule.
- **Candidate observation viewpoint:** a possible camera pose; the planner may choose among alternative poses that satisfy the same target.
- **Required-target completion:** the fraction of required items that have met their acceptance rules.
- **Mission success:** every required item is accepted, within the budget and enabled safety constraints.
- **Inspectable surface coverage:** coverage conditional on the fixed observation library.
- **Whole-sample area coverage:** an area-weighted estimate over the original surface samples, with sampling limitations stated.
- **Priority-weighted coverage score:** a separate utility measurement, not a physical area percentage.

Avoid defining success as visiting every preselected camera pose unless the mission actually prescribes those poses. Required viewpoints would turn much of the task into ordering a fixed visit list and reduce the viewpoint-selection contribution.

## 3. Define targets before evaluating the new test set

Create a versioned YAML mission manifest and an annotation table. Select physical regions from task intent and verified mesh geometry, before comparing planner outcomes. Use the original full transformed mesh, not only the currently observable 41 samples, as the annotation domain.

Each record should contain a stable ROI/target identifier, component label and provenance, mesh-node/triangle membership or reproducible patch definition, coordinate frame, sampled positions/normals, represented area, mandatory status, mission rationale, accepted view conditions, and the manifest/mesh hashes. Keep area and priority as distinct fields.

The present target sampler assigns identifiers such as `mesh_00010` and retains sample geometry, but it does not retain a component/criticality mapping. Establishing the annotation provenance is a real data-preparation step, not a relabeling of existing semantic metadata.

Proposed benchmark profiles, contingent on identifying the corresponding geometry, are: interface-region inspection, truss/appendage-connection inspection, and a mixed distributed component inspection task. Exact regions and counts are not yet established. If a label cannot be substantiated from the model, use an explicitly declared synthetic ROI; do not label a coordinate extreme as an actual critical ISS component.

For every profile:

1. Document the requirement before examining new test outcomes. Treat the old test and shifted sets as development/exploratory material for this revision.
2. Represent each meaningful region by several surface samples or explicit inspection items. A single visible centroid does not establish full inspection of a component.
3. Check whether required items have suitable viewpoints and connected safe routes. If the library misses a required region, expand candidate observations using a deterministic development rule; do not remove that region from the denominator to make completion easier.
4. Freeze target definitions, camera model, candidate generation/reduction, transfer model, planning budget, and parameter-selection procedure before the new test campaign.
5. Report unavailable requirements as unmet/infeasible according to the level of proof available. Retain the fixed requirement set when observations are lost in a scenario.

The number of regions should follow the inspection task and manageable computational scale, not the desire to obtain a visually attractive 100% result. Evaluate multiple independently specified profiles so that one small convenient target set does not carry the entire argument.

## 4. Formal task and observation acceptance

Let the fixed nonempty required set be \(\mathcal K\). For a route \(\pi\), let \(z_i(\pi)=1\) only if target \(i\) receives an accepted observation. The primary task is

\[
\min_{\pi} J(\pi)=\sum_{(u,v)\in\pi}\ell_{uv},\qquad
z_i(\pi)=1\ \ \forall i\in\mathcal K,
\]

subject to the same stated transfer, safety, and action/time-budget constraints. Preserve the current nonnegative graph stage cost for the first comparison and report physical velocity increment separately. Additional area coverage can be reported without adding an arbitrary reward that changes the cost comparison.

Define

\[
C_{\mathrm{req}}(\pi)=\frac{1}{|\mathcal K|}\sum_{i\in\mathcal K}z_i(\pi),
\qquad
\operatorname{goal}(s)\equiv(m(s)\mathbin{\&}K)=K.
\]

For the basic fixed-mask implementation, a required target is one bit. With required surface regions, define patch completion explicitly: the simple version requires every prescribed sample in every patch to receive an accepted view. If each ROI instead has its own area threshold, report “all ROI requirements satisfied” and the thresholds; do not describe that as 100% physical area coverage.

Keep three task modes for a controlled comparison:

| Mode | Terminal requirement | Purpose |
| --- | --- | --- |
| Required targets, proposed primary | All required items accepted | Direct mission specification |
| Hybrid | All required items accepted and a separately specified background survey threshold reached | Optional broader-context mission |
| Coverage only | Original 80%, plus 95%/98% sensitivity on the new common benchmark | Shows how an aggregate objective relates to missed required items |

Do not silently retain an 80% background condition in the primary required-only task. Any hybrid background threshold needs its own mission rationale.

Observation acceptance should state range, field of view, incidence, full-mesh occlusion, and exposure/dwell assumptions. For the stronger visual-inspection claim, add a projected-resolution criterion based on the actual camera and target feature/patch size, and count the dwell in mission duration. Distinguish a geometric planning criterion from demonstrated image-based defect detection. Existing rendered frames alone do not validate detection performance.

For a first bounded implementation, retain deterministic masks using prescribed camera attitude and fixed accepted exposures. If continuous dwell accumulation, multiple independent look directions, illumination state, or partial image quality changes acceptance over time, augment the state accordingly and revise the Markov argument; one coverage bit is then insufficient.

## 5. Planner and execution changes required before writing new results

Existing hard-mask support makes this a focused extension, but a text-only change would be incomplete.

| Area and source | Planned change | Verification needed |
| --- | --- | --- |
| `advanced_safe_planner.py`: `SafeGraphProblem`, `_goal_reached`, configuration validation | Add explicit coverage-only, required-only, and hybrid semantics with backward-compatible defaults; propagate one frozen required mask | 80% plus a missing required bit must fail the required/hybrid task; all required bits below 80% must succeed in required-only mode; reject an empty required-only task |
| Base completion and action ranking in the same module | Make the base policy aware of missing required targets; document the ranking and validate it before the test campaign | A finite terminal completion must actually meet the selected goal; all compared policies use the same requirements |
| `_safe_actions` and other candidate/sequence filters | Audit every positive-new-coverage filter; support safe transit with zero inspection gain if needed by the declared action space | A small directed graph requiring a zero-gain connecting action must remain solvable, or the restriction must be explicit and shared by the oracle |
| `offline_adp_superiority_study.py`: scenarios, graph reduction, reference construction, `_problem_for_scenario` | Carry mission IDs and required masks throughout; regenerate references for the new goal; make any node reduction preserve required observability and relevant connectivity | No old 80% reference or incumbent-success rejection silently defines the new benchmark |
| `ros_route_exporter.py` | Export the requirement manifest, target IDs/masks per observation, acceptance data, and separately named planned metrics; remove hard-coded 0.80 assumptions in the new mode | Exported route cost, mask, target counts, and mission predicate reproduce the offline result |
| `verification_evaluator_node.py`: `_load_observations`, `_tick`, `_publish_coverage`, `_finish` | Keep actual per-view target IDs and union only accepted target sets; derive target completion and mission success from that union | Rejecting an early observation and accepting a later one must not credit targets seen only by the rejected observation; duplicate observations must not double-count |
| Campaign summaries, CSVs, manifests and plotting inputs | Add required, accepted, and missing IDs/counts; separate area and priority scores; add failed-observation and infeasibility reasons | Figures and summary tables reconstruct exactly from the logs |

Audit partial-plan ranking, feature calculations, and memoization as well: a new mission must not reuse cached values from a different required set, and a failed route must not be ranked as complete because it has high background coverage. If the fitted-critic ablation remains in the new primary experiment, its features/checkpoint must be retrained or revalidated for the new objective; otherwise move its old result to the historical supplement.

The current evaluator advances coverage with the maximum planned cumulative value of a later accepted observation. That can over-credit earlier rejected observations; its loader retains counts rather than the full target set. Correct set-based accounting is a prerequisite for the new completion claim. This does not by itself invalidate the existing accepted case in which every observation passed.

Keep ROS interfaces stable. Add optional configuration and versioned manifest/log fields; use supplemental diagnostic data rather than breaking existing message definitions. Keep ROS-native HCW as state source of truth and all physical collision/occlusion queries against the full ISS mesh, including areas outside the inspection task.

Proof revisions must be explicit. For a fixed mission manifest and deterministic binary acceptance masks, the required-goal predicate is monotone and the existing covered mask records remaining requirements. Recheck feasibility preservation and the base-cost bound using an actual goal-reaching completion and its admissible tail. These results remain conditional on the base completion and declared action space. Failure to find a greedy completion does not prove graph infeasibility. Exact optimality remains limited to the finite graph and all restrictions actually enforced by the exact search.

Use “no certified completion found” for a rollout failure unless an exact search or a necessary-condition failure proves infeasibility. Do not include a positive coverage-gain heuristic in the definition of physical safety.

## 6. New experiment protocol

### Development and freezing

Use the existing data to diagnose implementation and feasibility only. Predefine fresh disjoint scenario identities for the new campaign. Select ROI definitions, depth, task-aware base ranking, budget, any repair rule, and computational limits using development/validation cases. Record the freeze and all configuration hashes. Depth three can remain the initial engineering setting, but its earlier coverage-only advantage and the post-selection depth sweep cannot establish its quality for the new mission.

As an initial planning estimate, use three mission profiles with 50 new test scenarios and 30 shifted scenarios per profile. Finalize sample size once using development variability and a chosen precision for completion and cost estimates, before new test results are opened. These are proposed design numbers, not a power calculation or existing results. A new seed set on the same ISS mesh supports that benchmark distribution; it does not provide external-mesh or flight validation.

### Essential comparisons

1. Compare rollout ADP, a task-aware safe-greedy incumbent, fixed-completion rollout, and audited local search on identical required-target tasks. Give every method the same masks, graph, budgets, safety rules, and information. If a stronger local-search neighborhood is needed for credibility, select and freeze it on development data and report its effort.
2. Compare coverage-only, priority-weighted coverage, required-only, and hybrid formulations while measuring the same fixed required-target completion for all. This tests whether hard requirements contribute beyond simply increasing priority weights.
3. Include exact reduced-graph instances with feasible, infeasible, and zero-gain-connector cases. Quantify cost gaps only where the oracle completes and certifies the answer; a timeout is unresolved.
4. Stress required-target count/region extent, spatial spread, observation loss, budget, and observation-quality thresholds. Select a small predefined set of settings; do not tune the test until the preferred planner wins.
5. Demonstrate at least one newly planned and logged ROS mission satisfying the new requirement manifest. Include an intentional rejected-observation check. If claiming execution-level method superiority, run a paired ROS campaign; one demonstration supports only that demonstration.

### Feasibility and statistics

Report the full generated population, not just cases on which the incumbent succeeded. A separately labeled incumbent-feasible stratum is useful for testing the conditional rollout guarantee.

Classify each scenario using available evidence: required item absent from all available views; no admissible route proven by exact/exhaustive search; feasible route known but the method did not find one; solver timeout or unresolved feasibility; successful route. Passing the union-of-views test is only a necessary condition and must not be labeled proof of structural route feasibility.

Primary reporting order is all-required mission success and missing-item counts, then resource cost at matched completion. Give completion proportions with confidence intervals; compare paired binary outcomes with an appropriate paired test and effect interval. Report paired cost/velocity-increment differences on jointly successful pairs with the pair count and selection caveat. Also report all-scenario results with a failure penalty specified before testing, so inexpensive incomplete routes cannot appear advantageous. Separate each profile and use predefined aggregation; do not pool repeated cases as if they were independent missions.

Report per-target/per-ROI completion, worst-region performance, graph cost, physical velocity increment, transfer-plus-inspection time, action count, runtime, safety margins, and contextual area coverage. A 100% per-route completion observation is distinct from 100% success over a population and from proof of future reliability.

## 7. Manuscript revision map

Retain IEEE Transactions style, current section order where practical, and the SOOA/rollout algorithm as the central contribution.

| Current location in `OrbInspectLatex/main.tex` | Planned revision |
| --- | --- |
| Title and abstract, lines approximately 49–77 | Consider “Viability-Preserving Rollout Planning for Task-Directed Orbital Inspection.” Write the abstract last; state the required-target mission and insert new success/cost statistics only after validation. Do not carry the old 3.96% improvement into the new task |
| Introduction, lines 80–108 | Lead with mission-directed component inspection; explain why aggregate coverage can leave a required region unobserved. Distinguish viewpoint choice from required physical targets and add the revised contribution and limits |
| Related Work, lines 109–121 | Distinguish broad survey, priority-weighted coverage, and task-prescribed inspection; use verified primary sources without claiming that mandatory-set planning itself is new |
| System and Observation Model, lines 122–225 | Add mission ROI/target definitions, acceptance rules, separate area/priority weights, and explicit denominators. Retain full-mesh geometry for visibility and safety |
| Candidate Graph and Markov State, lines 229–257 | Add the fixed requirement manifest to problem inputs; replace the scalar stopping rule with the mission predicate. Extend state only if acceptance needs information beyond binary masks |
| Base policy, rollout, Algorithm 1, lines 282–342 | Show task-aware completion; update all terminal cases and failure semantics. Keep cost minimization under hard constraints |
| Properties and Exact Oracle, lines 344–415 | Recheck monotonicity, state sufficiency, certificate continuation, and cost bound. State exact-search and zero-gain-action restrictions precisely |
| Experimental Protocol, lines 417–509 | Present target provenance, independent mission profiles, fresh freeze/splits, observation criteria, full-population feasibility reporting, paired methods, and completion-first statistics |
| Results, lines 511–638 | Lead with all-required completion and per-ROI evidence, then matched resource costs, ablations, stress tests, and an audited representative task |
| Existing post-selection study, lines 607–611 | Preserve as explicitly exploratory context, preferably in the supplement; do not reuse the six sentinels as a validated mission specification |
| ROS results in `sections/ros_verification_results.tex` | Replace the central demonstration only after a new required-target run and target-credit audit; report accepted IDs and the geometric/imaging scope |
| Discussion and conclusion, lines 643–671 | Explain mission relevance, opportunity cost of broader surveys, annotation and library limitations, unresolved feasibility, and inspection-quality assumptions; use only the new measured effects for the new task |
| Data/code availability and package | Add ROI manifests, annotations, freeze record, target-event logs, updated source tables and hashes; preserve old archives with their original interpretation |

Line numbers describe the present snapshot and will move during editing.

## 8. Figure changes with the existing style and layout fixed

The author's style preference is a requirement. Preserve panel count/order, overall aspect ratios, font family and sizes, established method colors, marker/line conventions, line weights, camera orientations, and LaTeX placement/widths. Change data, compact labels, and necessary target overlays. Do not constrain a valid route to have ten observations merely to fill the current ten-frame montage.

| Existing figure label | Content change within the existing arrangement |
| --- | --- |
| `fig:sooa-framework`, current four-panel overview | Overlay numbered required regions in the existing geometry panels; show required/optional masks using outline/marker distinctions and the existing palette. Keep the full ISS as context and safety geometry |
| `fig:adp-architecture`, current workflow | Replace generic coverage-goal labels with required-target completion and the updated completion predicate. Keep box coordinates, connectors and proportions |
| `fig:adp-depth-sensitivity`, current three panels | If used for the new primary task, regenerate cost/time/evaluation values on its frozen validation cases. Preserve axes and three-panel arrangement; put completion counts in the accompanying table. Otherwise identify it as the historical coverage-only diagnostic in the supplement |
| `fig:paired-performance`, current four panels | Regenerate the existing paired comparison plots for the new common task. State the jointly successful pair count where plotting physical costs; account for all failures in the adjacent success table and penalized comparison |
| `fig:paired-safety`, current four panels | Define the success panel as all-required mission completion; preserve cost, clearance and input panels with new evidence. Add per-ROI counts as a compact table rather than redesigning the panel grid |
| `fig:representative-trajectory`, current three panels | Retain route, progress and cumulative-effort panels. Mark required regions on the route panel and use required-target completion, ending at 100%, in the progress panel. Report background coverage in the caption or table |
| `fig:ros-key-camera-views`, current two projections with camera insets | Use a new audited run and annotate ROI/target IDs and accepted completion. Preserve projections and inset arrangement. If route length differs, select frames by a fixed milestone rule, label omissions, and retain all observations in the logs/supplement |

Reuse the existing Python sources: `generate_adp_future_figures.py`, `generate_depth_tradeoff_figure.py`, `generate_representative_case_figures.py`, and `generate_ros_key_camera_views_figure.py`. Preserve their respective palettes; for example, the current main-method colors are `#750014` for rollout ADP and `#587E92` for local search, with Arial/Helvetica/DejaVu Sans fallbacks. Record source-table and manifest hashes. Compare rendered before/after pages to detect panel shifts, font changes, clipped text, misleading legends, and altered data scales. Keep the present 14-page composition as the layout reference; allow evidence-driven pagination rather than shrinking text to force a page count.

The framework artwork also has an editable source at `OrbInspectLatex/figures/orbinspect_sooa_framework_complete.pptx`; update that source and its exported PDF consistently. Identify the generator actually used by each current provenance manifest before regenerating numerical panels, since historical alternative scripts are also present.

## 9. Delivery sequence and completion criteria

1. **Mission specification:** annotation table, acceptance criteria, fixed denominators, and development-only observability/route audit. Deliver a concrete target map before planner evaluation.
2. **Implementation:** goal modes, task-aware completion, consistent baselines/oracle, target-preserving export, and accepted-target accounting. Run focused mathematical and credit-accounting tests and the required ROS 2 Jazzy build on the supported Ubuntu environment.
3. **Protocol freeze:** write the scenario-generation and analysis specification, target/config hashes, fresh split IDs and stopping/sample-size rules.
4. **Evidence:** run the new primary, ablation, reduced-oracle, stress, and ROS checks. Report failures and inconclusive comparisons without selecting a new favorable target set from test outcomes.
5. **Manuscript and figures:** revise from measured evidence, regenerate only affected figure contents, retain the requested style/layout, compile and visually inspect the entire paper.
6. **Reproducibility package:** archive each campaign under `data/results/<timestamp>/` with `config_snapshot/`, `raw/`, `rosbag/`, `figures/`, `videos/`, `summary.json`, and `summary.md`; retain the six required CSV streams and add target-level acceptance records. Seal checksums after final review.

Focused test targets are `test_advanced_safe_planner.py`, `test_offline_adp_superiority_study.py`, `test_verification_evaluator_node.py`, and `test_ros_verification_campaign.py`, plus an exporter round-trip check. Include high background with one key missing, all keys complete below 80% background, overlapping/duplicate observations, invalid or empty requirements, mask serialization, necessary zero-gain transit, greedy failure despite exact feasibility, budget exhaustion, and rejected-observation accounting. Run relevant Python tests, `colcon build --symlink-install`, and package discovery on Ubuntu 24.04 with ROS 2 Jazzy after implementation; these have not been run for this planning-only task.

The new primary claim is ready only when target selection has a documented rationale, the required denominator stays fixed, every success record is independently reconstructible, observation acceptance matches the written model, all baseline tasks match, feasibility is classified honestly, new comparisons support the stated effects, and the rendered figures preserve the agreed style. If the new data do not show lower cost, the paper can still report a valid required-target planning framework, but its superiority claim must be narrowed to the evidence.

## 10. Current boundaries and unresolved inputs

The physical ROI annotations, their mission significance, required image quality/dwell, final scenario count, and new performance results remain to be established during implementation. This plan does not assume NASA endorsement of an ISS criticality map, actual damage-detection capability from the visualization mesh, success of every scenario, or retention of the previous velocity-increment advantage.

This planning task adds the revision plan only. Manuscript source, algorithm code, the verified September 5 PDF, and the existing figure assets have not been changed.
