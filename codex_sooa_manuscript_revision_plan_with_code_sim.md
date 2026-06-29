# Codex Target/Plan Prompt: Revise Orbital Inspection Manuscript Around SOOA Novelty

## Context

You are modifying an existing LaTeX manuscript currently titled:

**Dynamics-Aware Coverage Planning for Autonomous Inspection of Orbital Structures**

The current manuscript already contains the following material:

- CW/HCW relative orbital dynamics.
- Camera visibility with range, field of view, incidence angle, and line-of-sight checks.
- Candidate-view graph planning.
- Reduced-graph exact dynamic programming certificate.
- Scalable ISS-mesh benchmark with baselines.
- ROS 2 / RViz / Gazebo replay and FOV verification.
- Discussion that Gazebo is only a visualization/replay layer, not the source of orbital dynamics.

The required revision is to reframe the paper so that it is not perceived as a loose combination of existing modules such as NBV + HCW transfer + set cover + ROS replay. The revised manuscript must present a clear algorithmic primitive and problem abstraction:

**Safe Observable Orbital Arc (SOOA)**

The new main contribution should be:

> The paper introduces safe observable orbital arcs as inspection motion primitives that jointly encode relative-orbit reachability, FOV-valid visibility, surface coverage, transfer cost, input feasibility, clearance, and passive-safety margin. Full-coverage orbital inspection is then formulated as constrained SOOA selection, rather than geometric viewpoint selection followed by dynamic repair.

Do not add ADP. The current paper should remain a deterministic planning paper, not a learning-based optimal-control paper.

---

## Target Mode

### Primary target

Revise the manuscript so that its scientific object is:

```text
Safe Observable Orbital Arc planning for full-coverage autonomous orbital inspection.
```

The paper should read as a new planning abstraction and planner, not as a pipeline of existing algorithms.

### Required high-level claims

The revised paper should claim:

1. A new **Safe Observable Orbital Arc (SOOA)** representation.
2. A constrained **SOOA graph** for orbital inspection.
3. FOV-valid, range-valid, incidence-valid, LOS-valid surface coverage.
4. HCW-feasible transfer and/or dwell arc feasibility.
5. Planning-level safety through input, speed, clearance, and passive-drift audit.
6. Reduced finite-graph optimality certificate only on small exhausted graphs.
7. Scalable deterministic solver for the ISS benchmark.
8. ROS 2 / RViz / Gazebo verification of trajectory, attitude, frustum, coverage logs, and visual geometry.

### Required careful wording

Use these claim boundaries throughout the manuscript:

- Do **not** claim global optimality in continuous viewpoint space.
- Do **not** claim flight-certified safety.
- Do **not** claim Gazebo validates orbital mechanics.
- Do **not** claim passive safety unless the passive-drift audit is actually implemented and logged.
- Do **not** claim the scalable full ISS result is globally optimal.
- Do **not** describe the contribution as merely a candidate-view graph unless explicitly explaining the previous baseline abstraction.

Preferred wording:

```text
planning-level safety under the sampled HCW model
```

```text
finite-graph optimality on an exhausted reduced SOOA graph
```

```text
ROS 2/RViz/Gazebo verification of replay geometry and FOV consistency
```

```text
Gazebo is a visual replay and sensor-geometry layer, not the source of orbital dynamics
```

---

## Plan Mode

Follow this plan exactly. Make one coherent revision across the manuscript, then compile and verify.

---

# Phase 0: Project inspection and backup

1. Identify the main LaTeX source file, likely `main.tex`.
2. Identify all included `.tex` files, bibliography files, figures, tables, and scripts.
3. Create a backup copy before editing:

```bash
cp main.tex main_before_sooa_revision.tex
```

4. Compile the current project once to establish the baseline:

```bash
latexmk -pdf -interaction=nonstopmode main.tex
```

If the build command differs, infer the correct command from project files.

5. Do not edit the PDF directly. Edit only LaTeX/source files and any necessary figure-generation scripts.

---

# Phase 1: Rename and reframe the manuscript

## 1.1 Title

Replace the title with one of the following. Prefer Option A.

Option A:

```text
Safe Observable Orbital Arc Planning for Full-Coverage Autonomous Inspection of Orbital Structures
```

Option B:

```text
Passive-Safety-Aware Observable Arc Planning for FOV-Constrained Orbital Structure Inspection
```

Use Option A unless the title becomes too long for the template.

## 1.2 Short running title

If the manuscript has a running title or footer title, replace it with:

```text
SOOA Planning for Orbital Inspection
```

or:

```text
Safe Observable Orbital Arc Planning
```

## 1.3 Keywords

Update keywords to include:

```text
spacecraft inspection, relative orbital dynamics, safe observable orbital arc, field-of-view constraints, coverage planning, passive safety, ROS verification, Clohessy-Wiltshire equations
```

Remove or de-emphasize `next-best-view planning` if it makes the work sound like a standard NBV pipeline.

---

# Phase 2: Rewrite the abstract

Replace the current abstract with a version centered on SOOA. Keep the current numerical results, but do not overclaim.

Use this draft as the base text and adapt to the template length:

```latex
\begin{abstract}
Autonomous inspection of large orbital structures requires inspection actions that are simultaneously informative, dynamically reachable, sensor-valid, and safe under relative orbital motion. This paper introduces a safe observable orbital arc (SOOA) representation for full-coverage orbital inspection. Each SOOA is an inspection motion primitive that jointly encodes HCW-feasible relative motion, camera field-of-view visibility, line-of-sight surface coverage, transfer effort, clearance, input feasibility, and passive-safety margin. The inspection problem is then formulated as a constrained SOOA-selection problem rather than a geometric viewpoint-selection problem followed by dynamic feasibility checking. For reduced SOOA graphs, an exact dynamic program over selected-arc masks and terminal arcs provides a finite-graph optimality certificate. For ISS-scale mesh instances, a scalable deterministic solver uses the same visibility and feasibility semantics to generate high-coverage safe inspection tours. The method is evaluated on an open NASA ISS mesh against coverage-greedy, nearest-view, fuel-focused, CW-NBV, random-safe, and safety-filtered coverage baselines. The proposed planner reaches 98.33\% weighted surface-sample coverage with 21 selected inspection actions, 21.592 m/s cumulative $\Delta v$, 9.91 m minimum clearance, and 5.97 s planning time in the reported base case. Baselines that optimize coverage geometrically can reach similar coverage only with input or clearance violations, whereas feasible safe baselines require substantially higher effort. ROS 2, RViz, and Gazebo replay verify that the logged trajectory, attitude stream, and camera frusta are consistent with the offline SOOA visibility model, while all quantitative dynamics, coverage, and safety claims remain based on the HCW planner logs.
\end{abstract}
```

If passive-safety margin is not yet computed in the code/data, replace `and passive-safety margin` with `and a passive-safety audit interface`, then add an implementation task in Phase 8.

---

# Phase 3: Rewrite the introduction around the reviewer risk

## 3.1 Add the central motivation

In the Introduction, after the paragraph explaining that geometric views can be unsafe or expensive, add the following idea:

```latex
The key difficulty is not only that coverage and dynamics must both be considered, but that the selectable inspection action itself must be physically meaningful. A static viewpoint is an incomplete planning primitive for orbital inspection because a view that is geometrically informative may be unreachable, unsafe during approach, or passively unsafe after thrust loss. Conversely, an orbit segment that is dynamically natural may be uninformative if its camera field of view does not expose new target surface. This motivates an inspection primitive that binds observability and orbital feasibility before planning begins.
```

## 3.2 Introduce SOOA early

Add this paragraph before the contributions:

```latex
This paper addresses the issue by introducing the safe observable orbital arc (SOOA). A SOOA is not merely a candidate viewpoint or a transfer edge. It is a finite-duration inspection action generated under relative orbital dynamics and annotated with the surface targets observed through the camera model, the required control effort, the minimum clearance, the input and speed feasibility status, and a passive-drift safety margin. Planning over SOOAs changes the finite search space: infeasible or sensor-invalid actions are removed before coverage selection, rather than repaired afterward.
```

## 3.3 Replace the contribution list

Replace the current contribution list with this structure:

```latex
The main contributions are:
\begin{enumerate}
    \item We introduce the safe observable orbital arc (SOOA), an inspection motion primitive that jointly encodes HCW relative-motion feasibility, FOV-valid surface visibility, line-of-sight coverage, control effort, clearance, input feasibility, and passive-safety margin.
    \item We formulate full-coverage orbital inspection as a constrained SOOA-selection problem on a finite graph, avoiding the conventional separation between geometric viewpoint selection and subsequent dynamic feasibility checking.
    \item We develop a two-mode solver for the SOOA graph: an exact dynamic-programming oracle that gives finite-graph optimality on reduced exhausted graphs, and a scalable deterministic safe-arc coverage solver for ISS-scale mesh benchmarks.
    \item We provide a reproducible validation protocol with baseline comparisons, sensitivity studies, ablations, and ROS 2/RViz/Gazebo replay that verifies trajectory, attitude, camera-frustum, coverage, and safety-log consistency while preserving HCW propagation as the quantitative source of truth.
\end{enumerate}
```

If passive safety is not implemented, change the first item to:

```text
... and a passive-safety audit interface.
```

Then implement passive safety in Phase 8 before restoring the stronger wording.

---

# Phase 4: Related Work revision

The current Related Work is mostly usable, but reframe the comparison table and narrative around `viewpoint`, `orbit`, and `arc` representations.

## 4.1 Add a paragraph distinguishing SOOA

Add near the end of Related Work:

```latex
The distinction in this paper is the planning primitive. Robotic NBV and inspection planners commonly reason over sensor poses or short geometric motions, while relative-orbit design methods reason over dynamically meaningful paths that are not necessarily coverage-optimal. The proposed SOOA representation merges these two views at the discrete action level: every selectable action is simultaneously an orbital motion segment and a sensor-valid coverage contributor. This makes the finite graph a graph of admissible inspection actions, not merely a graph of geometric views connected by post hoc transfers.
```

## 4.2 Update Table I

Rename `This work` row to:

```text
This work: SOOA graph planning
```

Primary emphasis:

```text
safe observable orbital arcs for FOV-valid weighted surface coverage
```

Difference:

```text
selects finite-duration HCW-feasible inspection actions annotated with visibility, fuel cost, clearance, input feasibility, and passive-safety margin; includes reduced-graph DP certification and ROS/RViz/Gazebo replay verification
```

If passive safety is not implemented, use `passive-safety audit` rather than `passive-safety margin`.

---

# Phase 5: System model and problem formulation

## 5.1 Preserve existing HCW and FOV equations

Keep the current HCW dynamics and visibility equations. They are valuable and already match the target direction.

However, do the following:

1. Replace language that says `candidate viewpoint is the planning object` with `candidate arc` or `SOOA` where scientifically correct.
2. Keep `viewpoint` only when referring to the terminal stabilized camera pose or the viewpoint seed from which an arc is generated.
3. Add a new subsection before the finite graph section.

## 5.2 Add subsection: Safe Observable Orbital Arc

Insert this subsection after the visibility and dynamic feasibility subsections and before the finite graph objective.

Use this LaTeX draft as the base:

```latex
\subsection{Safe Observable Orbital Arc}

A safe observable orbital arc is the finite-duration inspection action used by the planner. For an arc $a_j$ over $t\in[0,T_j]$, define
\begin{equation}
    a_j = \left(x_j(t), u_j(t), q_j(t), \Gamma_j, \Delta v_j, d^{\min}_j, \rho_j\right),
\end{equation}
where $x_j(t)$ is the HCW-propagated relative state, $u_j(t)$ is the commanded acceleration, $q_j(t)$ is the camera attitude profile, $\Gamma_j\subseteq\mathcal{T}$ is the set of targets satisfying the range, FOV, incidence, dwell, and line-of-sight visibility predicates along the arc, $\Delta v_j$ is the accumulated control effort, $d^{\min}_j$ is the minimum clearance, and $\rho_j$ is the passive-safety margin.

The accumulated control effort and clearance are
\begin{equation}
    \Delta v_j = \int_0^{T_j} \|u_j(t)\|_2\,dt,
\end{equation}
\begin{equation}
    d^{\min}_j = \min_{t\in[0,T_j]} d_{\mathcal{S}}(r_j(t)).
\end{equation}
An arc is dynamically admissible if all sampled states satisfy the HCW propagation model, input bound, speed bound, and clearance bound. It is observable if $\Gamma_j\neq\emptyset$ under the camera visibility model.

To encode passive safety, the uncontrolled drift from every sampled state on the arc is propagated as
\begin{equation}
    \dot{x}_{\mathrm{drift}} = f_{\mathrm{HCW}}(x_{\mathrm{drift}},0).
\end{equation}
The passive-safety margin is
\begin{equation}
    \rho_j = \min_{t_k\in a_j}\min_{\tau\in[0,T_{\mathrm{PS}}]}
    d_{\mathcal{S}}\left(r^{\mathrm{drift}}(t_k+\tau)\right)-d_{\mathrm{PS}}.
\end{equation}
The arc is passively safe if $\rho_j\ge 0$. If passive-safety auditing is disabled in a specific benchmark, $\rho_j$ is reported as not evaluated and the safety claim is limited to input, speed, and clearance feasibility.
```

Important: if the project does not currently compute passive safety, implement it in the experiment scripts or retain the final sentence that limits the claim.

## 5.3 Replace finite candidate-view graph with SOOA graph

Change the formulation from:

```latex
V = \{z_j\}_{j=1}^M
```

to:

```latex
\mathcal{A} = \{a_j\}_{j=1}^M
```

Use:

```latex
\Gamma(a_j) \subseteq \mathcal{T}
```

for visible targets.

Define transition cost:

```latex
\ell(a_i,a_j)
```

The arc-selection objective should be written as:

```latex
\begin{equation}
\min_{\sigma}
\sum_{\ell=1}^{L} \ell(a_{\sigma_{\ell-1}},a_{\sigma_\ell})
+ \lambda_v\sum_{\ell=1}^{L}\Delta v(a_{\sigma_\ell})
+ \lambda_L L
+ \lambda_C\sum_{i=1}^{N}w_i(1-c_i),
\end{equation}
```

with:

```latex
\begin{equation}
    c_i = \mathbf{1}\left[i\in \bigcup_{\ell=1}^{L}\Gamma(a_{\sigma_\ell})\right].
\end{equation}
```

and:

```latex
\begin{equation}
    \sum_{i=1}^{N}w_i c_i \ge C_{\mathrm{req}}\sum_{i=1}^{N}w_i.
\end{equation}
```

---

# Phase 6: Algorithm revision

## 6.1 Rename Algorithm 1

Rename:

```text
Dynamics-aware finite-graph inspection planner
```

to:

```text
SOOA-based orbital coverage planner
```

## 6.2 Replace Algorithm 1 pseudocode

Use the following algorithmic sequence. Adapt variable names to match the manuscript.

```latex
\begin{algorithm}[t]
\caption{SOOA-based orbital coverage planner}
\begin{algorithmic}[1]
\REQUIRE Structure geometry $\mathcal{S}$, initial state $x_0$, camera model, HCW model, safety limits, $C_{\mathrm{req}}$, $C_{\mathrm{stop}}$
\ENSURE Planned trajectory $P$, attitude stream, SOOA sequence, and inspection metrics
\STATE Sample area-weighted surface targets $\mathcal{T}=\{(p_i,n_i,w_i)\}_{i=1}^{N}$
\STATE Generate viewpoint/attitude seeds around the structure
\STATE For each seed, generate a finite-duration candidate orbital arc under the HCW model
\STATE Reject arcs violating input, speed, clearance, terminal-error, or passive-safety constraints
\STATE Evaluate range, FOV, incidence, dwell, and LOS visibility along each accepted arc
\STATE Construct the SOOA library $\mathcal{A}$ with visibility sets $\Gamma(a_j)$, costs $\Delta v_j$, clearances $d^{\min}_j$, and margins $\rho_j$
\STATE Construct transition costs and feasibility flags between admissible arcs
\STATE Initialize covered set $\mathcal{C}\leftarrow\emptyset$, selected sequence $\sigma\leftarrow\emptyset$, and current arc/state from $x_0$
\WHILE{$C(\mathcal{C})<C_{\mathrm{stop}}$ and the arc budget is not exhausted}
    \STATE Compute new weighted coverage gain $\Delta C_j$ for feasible outgoing arcs
    \STATE Score each arc using coverage gain, transfer cost, control effort, and safety margin
    \STATE Select $a^\star = \arg\max_j s_j$
    \STATE Append $a^\star$ to $\sigma$ and update the predicted terminal state
    \STATE Update $\mathcal{C}$ using $\Gamma(a^\star)$
\ENDWHILE
\STATE Roll out/audit the selected SOOA sequence under HCW dynamics
\STATE Export trajectory, control, attitude, FOV, coverage, safety, and planner logs
\RETURN $P$, attitude stream, SOOA sequence, and metrics
\end{algorithmic}
\end{algorithm}
```

## 6.3 Rename Algorithm 2

Rename:

```text
Certified reduced-graph dynamic program
```

to:

```text
Certified reduced-SOOA-graph dynamic program
```

Replace `candidate node`, `view`, or `viewpoint` with `arc` where appropriate.

The DP state can remain `(B,j)`, but explain that `B` is the set of selected SOOA indices and `j` is the terminal arc.

---

# Phase 7: Theorem revision

The current theorem on reduced finite-graph global optimality is useful. Keep it, but place it after two simpler SOOA theorems. Use clear claim boundaries.

## 7.1 Add Theorem: SOOA planning-level safety

Add:

```latex
\begin{theorem}[Planning-level safety of SOOA sequences]
Consider a selected SOOA sequence $\sigma=(a_{\sigma_1},\ldots,a_{\sigma_L})$. If every selected arc and every transition rollout satisfies the sampled HCW dynamics, input bound, speed bound, clearance bound, and passive-safety condition $\rho_j\ge 0$, then the concatenated trajectory is planning-level safe over the sampled inspection horizon and remains collision-free under uncontrolled HCW drift for the audited passive-safety horizon.
\end{theorem}
```

Proof sketch:

```latex
\begin{proof}
Each SOOA is accepted only after all sampled states satisfy the input, speed, and clearance inequalities. Transition rollouts are accepted under the same feasibility audit. Concatenating feasible arcs and feasible transitions therefore preserves the sampled clearance bound over the planned trajectory. For passive safety, $\rho_j\ge 0$ is defined as the minimum clearance margin of the uncontrolled HCW drift from every sampled state over $[0,T_{\mathrm{PS}}]$. Hence any thrust-loss event at an audited sample remains outside the passive-safety boundary over the audited horizon. The statement is limited to the sampled HCW model and the selected audit horizon.
\end{proof}
```

If passive safety is not implemented, write this theorem as a proposed extension or remove the theorem and keep only a definition. Do not claim uncomputed safety.

## 7.2 Add Theorem: conditional coverage completeness

Add:

```latex
\begin{theorem}[Conditional discrete coverage completeness]
Let $\mathcal{A}_{\mathrm{safe}}$ be the accepted SOOA library. If
\begin{equation}
    \bigcup_{a_j\in\mathcal{A}_{\mathrm{safe}}}\Gamma(a_j)=\mathcal{T},
\end{equation}
then there exists a safe SOOA subset that achieves full discrete coverage of the target set. More generally, if the union covers a target subset $\mathcal{T}'\subseteq\mathcal{T}$, then full coverage is achievable only on $\mathcal{T}'$ under the given library.
\end{theorem}
```

Proof sketch:

```latex
\begin{proof}
The condition states that every target appears in at least one accepted SOOA visibility set. Selecting the union of all accepted SOOAs therefore covers every target. Since every selected element belongs to $\mathcal{A}_{\mathrm{safe}}$, the resulting sequence is composed of safe arcs, subject to feasible transition ordering. If transition feasibility is also required, the statement applies to the largest connected feasible component reachable from the initial state.
\end{proof}
```

## 7.3 Add Theorem: monotone submodular coverage

Add:

```latex
\begin{theorem}[Submodularity of SOOA coverage]
For a SOOA subset $\mathcal{B}\subseteq\mathcal{A}$, define
\begin{equation}
    F(\mathcal{B})=\sum_{i=1}^{N} w_i\mathbf{1}\left[i\in\bigcup_{a_j\in\mathcal{B}}\Gamma(a_j)\right].
\end{equation}
Then $F$ is nonnegative, monotone, and submodular. Therefore, under a cardinality-constrained selection model, the standard greedy coverage rule obtains the classical $(1-1/e)$ approximation bound relative to the best subset of the same size.
\end{theorem}
```

Proof sketch:

```latex
\begin{proof}
Nonnegativity follows from $w_i\ge0$. Monotonicity follows because adding a SOOA cannot remove previously covered targets. For any $\mathcal{B}\subseteq\mathcal{C}\subseteq\mathcal{A}$ and any arc $a\notin\mathcal{C}$, the targets newly covered by adding $a$ to $\mathcal{C}$ are a subset of those newly covered by adding $a$ to $\mathcal{B}$. Thus the marginal gain has diminishing returns, which proves submodularity. The approximation ratio follows from the classical greedy result for monotone submodular maximization under a cardinality constraint. This bound applies to the discrete coverage-selection stage, not to the full continuous orbital inspection problem.
\end{proof}
```

## 7.4 Keep current finite-graph optimality theorem, but rename it

Rename the current theorem to:

```text
Global optimality on an exhausted reduced SOOA graph
```

Update the text so it explicitly says:

```text
This theorem is deliberately discrete and reduced-graph only. It does not claim continuous-space optimality or global optimality for the scalable full ISS solver.
```

---

# Phase 8: Passive-safety audit implementation or claim limitation

Inspect the repository scripts/data. Determine whether passive drift margins are already computed.

---

# Phase 8A: Code-level SOOA refactor and simulation implementation

This phase is mandatory if the repository contains the planner/simulation code. The manuscript revision must not only rename concepts in text; the code and experiment outputs should support the SOOA abstraction as far as the current repository allows.

## 8A.1 Locate code entry points

Find the scripts/modules responsible for:

```text
target sampling
candidate viewpoint generation
visibility matrix construction
HCW transfer generation
planner selection loop
baseline planners
experiment runner
CSV/JSON metrics export
figure generation
ROS/RViz/Gazebo replay export
```

Create a short map in `SOOA_REVISION_REPORT.md`:

```text
planner entry point:
visibility code:
HCW transfer code:
experiment runner:
figure scripts:
ROS/replay scripts:
```

Do not rewrite unrelated infrastructure.

## 8A.2 Introduce a SOOA data structure

Add a dedicated data structure, class, dataclass, or dictionary schema representing one Safe Observable Orbital Arc.

Minimum fields:

```text
arc_id
seed_view_id
x_samples              # sampled HCW states
u_samples              # sampled accelerations
q_samples              # camera attitudes / boresight vectors
visible_target_ids     # Gamma(a_j)
delta_v
min_clearance
peak_input
max_speed
terminal_error
passive_margin         # rho_j, if implemented
passive_safe           # true/false/None
feasible               # full arc feasibility flag
rejection_reason
```

Suggested Python dataclass:

```python
@dataclass
class SafeObservableOrbitalArc:
    arc_id: int
    seed_view_id: int
    t: np.ndarray
    x: np.ndarray
    u: np.ndarray
    q: np.ndarray
    visible_target_ids: np.ndarray
    delta_v: float
    min_clearance: float
    peak_input: float
    max_speed: float
    terminal_error: float
    passive_margin: Optional[float]
    passive_safe: Optional[bool]
    feasible: bool
    rejection_reason: str = ""
```

If the codebase is not Python, implement the equivalent structure in the existing language.

## 8A.3 Refactor candidate generation into candidate arc generation

Current likely structure:

```text
generate candidate viewpoints
compute visibility
compute HCW transfers during planning
```

Target structure:

```text
generate viewpoint/attitude seeds
generate HCW candidate arcs or transfer-to-dwell arcs
evaluate arc feasibility
evaluate visibility along each arc
store accepted SOOAs
construct SOOA graph
```

Implementation rule:

- A geometric viewpoint may remain as a seed.
- The selectable planning object must become an accepted SOOA.
- The planner may still use terminal camera poses internally, but exported logs and manuscript terminology should report selected SOOAs / selected inspection actions.

## 8A.4 Implement SOOA visibility evaluation

For each arc sample and each target, evaluate the same predicates already used in the manuscript:

```text
range
FOV
incidence angle
LOS / ray casting
dwell accumulation
```

Store:

```text
visible_target_ids for each arc
incremental coverage gain during selection
per-view/per-arc coverage contribution
```

If the existing code only evaluates visibility at terminal viewpoints, either:

1. upgrade it to evaluate along arc samples; or
2. explicitly define the SOOA as a transfer-to-stabilized-dwell arc and evaluate visibility during dwell samples.

Do not silently claim along-arc visibility if only terminal dwell visibility is computed.

## 8A.5 Implement passive-drift audit

If possible, implement the passive-safety margin used by the manuscript.

Algorithm:

```text
for each accepted SOOA a_j:
    rho_j = +inf
    for each sampled state x_k on the arc:
        x_drift = x_k
        propagate HCW with u = 0 for tau in [0, T_PS]
        compute min signed distance to station safety envelope
        update rho_j = min(rho_j, d_S(r_drift) - d_PS)
    passive_safe = rho_j >= 0
```

Suggested defaults:

```text
T_PS = 300 s or one transfer duration
drift integration step = planner integration step
d_PS = d_safe unless a separate passive-safety distance is configured
```

Export these metrics:

```text
rho_min
passive_safety_horizon
passive_safety_distance
passive_safe
```

If implementation is not feasible, set:

```text
passive_margin = None
passive_safe = None
```

and force the manuscript to use limited wording:

```text
passive-safety audit interface
```

not:

```text
passive-safety guarantee
```

## 8A.6 Modify planner scoring to use SOOA semantics

Replace viewpoint score language and variables with arc score logic.

Target score form:

```text
s_j =
new_weighted_coverage_gain(a_j)
/
(1 + transition_cost(current, a_j) + lambda_v * delta_v_j)
+
w_s * normalized_safety_margin(a_j)
```

The exact formula may preserve existing behavior, but it should use SOOA fields:

```text
Gamma(a_j)
Delta v(a_j)
d_min(a_j)
rho_j, if available
transition feasibility eta(current, a_j)
```

Do not change numerical behavior unnecessarily. If the existing score is retained for reproducibility, wrap it as the SOOA score and document this in code comments and the report.

## 8A.7 Update exact DP solver to operate on SOOA indices

The DP may remain mathematically identical, but variable names and exported logs should use:

```text
arc index
SOOA set
Gamma(a_j)
ell(a_i, a_j)
eta(a_i, a_j)
selected SOOA sequence
```

The report should state whether the DP logic changed or was only refactored in terminology.

## 8A.8 Add SOOA experiment outputs

Update CSV/JSON outputs to include, where available:

```text
selected_sooa_count
selected_sooa_ids
coverage
delta_v
delta_v_per_coverage
min_clearance
peak_input
max_speed
terminal_error_rms
rho_min
passive_safe
input_feasible
clearance_feasible
trajectory_feasible
planning_time
```

Preserve old column names only if needed for backward compatibility, but add new aliases rather than breaking existing figure scripts.

## 8A.9 Add or update ablation experiments

Add a SOOA-specific ablation if code structure permits:

```text
geometric_viewpoint_graph
dynamics_aware_viewpoint_graph
sooa_without_passive_safety
full_sooa
```

Required metrics:

```text
coverage
delta_v
min_clearance
rho_min, if implemented
peak_input
input_violation
clearance_violation
passive_safety_violation
runtime
```

If these variants are too expensive to implement, map existing ablations to SOOA components:

```text
no transfer cost
no clearance filtering
no input checking
unweighted coverage
```

and explicitly report that these are component ablations, not full representation ablations.

## 8A.10 Update figure generation scripts

Modify labels and captions in generated figures:

```text
selected views -> selected SOOAs / selected inspection actions
candidate views -> candidate SOOAs, unless referring to seed viewpoints
dynamics-aware tour -> SOOA-based tour
view index -> selected SOOA index
```

If passive safety is implemented, add at least one plot or table entry for:

```text
rho_min or passive-safety margin over selected arc index
```

## 8A.11 Update ROS/RViz/Gazebo replay export

Ensure replay topics or marker names reflect SOOA outputs where appropriate.

Recommended outputs:

```text
/sooa_planner/trajectory_reference
/sooa_planner/attitude_reference
/sooa_planner/camera_frustum
/sooa_planner/covered_patches
/sooa_planner/visible_patches
/sooa_planner/safety_margin
/sooa_planner/passive_drift_preview, if implemented
```

RViz should display:

```text
target mesh
chaser pose
SOOA trajectory/path
selected SOOA terminal/dwell poses
camera frustum
covered/uncovered/visible patches
keep-out zone
passive drift preview, if implemented
```

Gazebo remains visual replay only. Do not use Gazebo physics to compute orbital dynamics.

## 8A.12 Add tests/sanity checks

Add lightweight tests or scripts that verify:

```text
SOOA object fields are populated
visibility sets are nonempty for accepted arcs
rejected arcs include rejection reasons
input and clearance audits match exported feasibility flags
rho_min is finite if passive safety is enabled
coverage computed from selected SOOAs matches reported final coverage
old benchmark still runs
figure scripts still run
```

Suggested commands:

```bash
python -m pytest
python scripts/run_high_coverage_benchmark.py
python scripts/generate_figures.py
```

Infer actual commands from the repository.

## 8A.13 Regenerate outputs only when necessary

If the code changes only rename variables and export aliases, preserve existing numerical results.

If passive safety, SOOA along-arc visibility, or planner scoring changes numerical behavior, rerun the benchmark and regenerate:

```text
tables
figures
CSV/JSON logs
ROS replay logs, if required
```

Do not mix old tables with new code behavior.

## 8A.14 Mandatory code/simulation report

In `SOOA_REVISION_REPORT.md`, add:

```text
Code modifications:
Simulation modifications:
New SOOA data schema:
Passive-safety audit status:
Benchmark rerun status:
Changed numerical results:
Unchanged numerical results:
Tests/sanity checks:
Known code limitations:
```

This section is mandatory even if no code was changed.



## 8.1 If passive safety is implemented

Ensure the manuscript reports:

- minimum passive-safety margin, `rho_min`;
- passive safety horizon, `T_PS`;
- passive safety distance, `d_PS`;
- whether all selected arcs pass the audit.

Add these to the metrics table if available:

```text
Minimum passive-safety margin
Passive-safety horizon
Passive-safety audit passed
```

## 8.2 If passive safety is not implemented

Implement a lightweight HCW drift audit if data and code structure allow it.

Algorithm:

```text
For each selected trajectory sample x_k:
    Set x_drift(0) = x_k
    Propagate HCW with u = 0 for tau in [0, T_PS]
    Compute minimum signed distance to station safety envelope
rho_min = min over all samples and drift times of d_S(r_drift) - d_PS
passive_safe = rho_min >= 0
```

Suggested defaults:

```text
T_PS = 300 s or one transfer duration
integration step = same as planner step
```

Do not invent a result. Regenerate the tables only if the audit runs successfully.

## 8.3 If implementation is not feasible within this revision

Limit all claims by saying:

```text
The present benchmark audits input, speed, and clearance feasibility; passive-drift margin is formulated as part of the SOOA representation and will be activated in future high-fidelity validation.
```

But this is weaker. Prefer implementing the passive-drift audit if possible.

---

# Phase 9: Results and ablation revisions

## 9.1 Preserve existing numerical results

Do not change reported numerical values unless the experiment scripts are rerun and the new outputs are verified.

Current key values to preserve unless regenerated:

```text
coverage = 98.33%
selected views/actions = 21
trajectory samples = 945
mission duration = 1890.0 s
total planned Delta-v = 21.5921 m/s
minimum clearance = 9.9107 m
peak requested input = 0.0388 m/s^2
planning time = 5.9707 s
```

Rename `selected views` to `selected SOOAs` or `selected inspection actions` if the implementation is reframed accordingly.

## 9.2 Add SOOA-specific ablation

Add a new ablation table or paragraph. Compare:

```text
Geometric viewpoint graph
Dynamics-aware viewpoint graph
SOOA without passive safety
Full SOOA
```

Metrics:

```text
coverage
Delta-v
minimum clearance
minimum passive-safety margin, if available
peak input
input violation flag
clearance violation flag
runtime
```

If the repository does not support all variants, add a paragraph explaining that the existing ablation already removes transfer cost, clearance filtering, input checking, and coverage weighting, and label these as partial SOOA-ablation components. Do not fabricate missing comparison data.

## 9.3 Reword baseline interpretation

Replace any wording that says:

```text
proposed dynamics-aware planner
```

with:

```text
proposed SOOA planner
```

or:

```text
SOOA-based planner
```

When discussing baseline failures, emphasize:

```text
The failures occur because those methods select coverage-rich geometric actions before enforcing the full admissible arc semantics.
```

---

# Phase 10: ROS/RViz/Gazebo verification revision

## 10.1 Replace placeholder figure

Find the placeholder on the ROS verification page. It currently says a ROS verification panel will be shown later. Replace this with a real figure if possible.

Required figure content:

Panel A: ROS data flow

```text
offline SOOA planner -> trajectory_reference -> attitude_reference -> HCW replay/tracking node -> RViz markers/Gazebo pose/rosbag logs
```

Panel B: RViz evidence

```text
ISS mesh, chaser pose, path marker, camera frustum, visible patches, covered/uncovered patches, keep-out zone
```

Panel C: FOV consistency

```text
frustum reconstructed from saved attitude and same FOV parameters used by offline visibility matrix
```

Panel D: Safety logs

```text
minimum clearance, input norm, passive-safety margin if implemented, coverage over time
```

## 10.2 If no image can be generated

Replace the placeholder with a non-placeholder schematic figure generated in vector form. A simple TikZ or PDF figure is acceptable.

Caption should say:

```latex
ROS 2/RViz/Gazebo verification workflow. The HCW dynamics node replays the planned SOOA trajectory and attitude stream, RViz reconstructs path, camera frustum, coverage, and safety markers, and Gazebo provides visual context for station and chaser geometry. Gazebo does not propagate orbital dynamics in the reported experiments.
```

## 10.3 Keep the scientific separation

Throughout the ROS/Gazebo section, preserve this distinction:

```text
HCW planner/logs = quantitative dynamics, coverage, and safety evidence.
RViz/Gazebo = replay, visualization, FOV geometry, integration consistency.
```

---

# Phase 11: Discussion and conclusion revision

## 11.1 Discussion

Rewrite the opening of the Discussion to say:

```latex
The main result is that the selectable unit of orbital inspection planning matters. When the planner selects geometric views and only later checks dynamics, high coverage can be achieved by actions that violate input or clearance constraints. The proposed SOOA representation changes this order: an action must be dynamically feasible, sensor-valid, and safety-audited before it can contribute coverage. This is why coverage and orbital feasibility cannot be separated without changing the mission outcome.
```

Keep the current limitations, especially:

- CW/HCW only;
- downsampled LOS;
- dense target sets make visibility expensive;
- no flight-certified safety;
- Gazebo is not dynamics validation;
- scalable solver is empirical, not globally optimal.

## 11.2 Conclusion

Rewrite the first paragraph of the Conclusion:

```latex
This paper introduced safe observable orbital arc planning for autonomous inspection of orbital structures. Instead of selecting geometric viewpoints and subsequently repairing the trajectory, the proposed formulation constructs finite-duration inspection actions that are simultaneously HCW-feasible, FOV-valid, coverage-informative, and safety-audited. Full-coverage inspection is then solved as a constrained SOOA-selection problem on a finite graph.
```

Preserve numerical results.

End with future work:

```text
accelerated mesh visibility
adaptive SOOA generation
larger certified graphs
uncertainty-inflated keep-out volumes
camera slew limits
illumination constraints
plume constraints
actuator saturation
Basilisk or higher-fidelity orbital backend
online replanning
```

Do not add ADP as future work unless explicitly requested by the author.

---

# Phase 12: Consistency pass

Search and revise terminology consistently.

## 12.1 Replace phrases carefully

Replace where appropriate:

```text
candidate-view graph -> SOOA graph
candidate viewpoint -> viewpoint seed / terminal camera pose / SOOA, depending on context
selected views -> selected SOOAs / selected inspection actions
view selection -> SOOA selection / safe-arc selection
finite candidate graph -> finite SOOA graph
```

Do not blindly replace all instances. Some `viewpoint` references are still valid when describing camera pose seeds, baselines, or prior work.

## 12.2 Check symbols

Ensure consistent notation:

```text
T or \mathcal{T}: target set
A or \mathcal{A}: SOOA library
Gamma_j or \Gamma(a_j): target set observed by SOOA j
rho_j: passive safety margin
Delta v_j: accumulated control effort of SOOA j
ell(a_i,a_j): transition cost
```

## 12.3 Check references

After edits, check:

- equation numbering;
- theorem numbering;
- algorithm numbering;
- figure numbering;
- table numbering;
- cross-references;
- bibliography compilation.

---

# Phase 13: Compile, inspect, and report

Run:

```bash
latexmk -pdf -interaction=nonstopmode main.tex
```

If errors occur, fix them. Do not leave undefined references, missing citations, or broken figure paths.

Then run:

```bash
latexmk -pdf -interaction=nonstopmode main.tex
```

again to resolve references.

Generate a final revision report named:

```text
SOOA_REVISION_REPORT.md
```

The report must include:

1. Files modified.
2. Title change.
3. Abstract/contribution changes.
4. New SOOA definition location.
5. New/modified algorithms.
6. New/modified theorems.
7. Passive-safety status:
   - implemented and reported, or
   - formulated but not evaluated, with exact limitation wording.
8. ROS/RViz/Gazebo figure status:
   - real figure added, or
   - schematic replacement added, or
   - still missing with reason.
9. Compilation status.
10. Remaining risks before submission.

---

# Final acceptance criteria

The revised manuscript is acceptable only if all of the following are true:

- The title, abstract, introduction, contribution list, formulation, algorithms, results narrative, discussion, and conclusion all use the SOOA framing.
- The paper no longer reads as a simple combination of NBV + HCW + graph search + ROS replay.
- The finite optimality claim is explicitly limited to the reduced exhausted SOOA graph.
- Safety claims are explicitly limited to the implemented audit level.
- Gazebo is never described as validating orbital dynamics.
- Existing numerical results are preserved unless experiments are rerun.
- No ADP is introduced.
- If planner/simulation code is present, it has been inspected and either refactored to expose SOOA objects or explicitly reported as unchanged with justification.
- If passive safety is claimed, a passive-drift audit is implemented, logged, and reported.
- Experiment tables/figures are consistent with the current code and logs.
- The PDF compiles without fatal errors.
- The final report clearly states what was changed in manuscript, algorithm, code, simulation, and what remains unresolved.

---

# One-shot instruction to Codex

Use the following as the execution prompt:

```text
You are revising a LaTeX manuscript for a top-tier aerospace/robotics journal. The current paper is about dynamics-aware coverage planning for orbital structure inspection. Modify the manuscript according to the target and plan in this markdown file. The main goal is to reframe the method around Safe Observable Orbital Arcs (SOOAs), a new inspection primitive that jointly encodes HCW feasibility, camera FOV visibility, LOS surface coverage, control effort, clearance, input feasibility, and passive-safety margin. Do not introduce ADP. Do not overclaim global optimality, flight safety, or Gazebo dynamics validation. Preserve existing numerical results unless you rerun and verify experiments. Compile the manuscript, fix LaTeX errors, and create SOOA_REVISION_REPORT.md documenting all changes and remaining risks.
```
