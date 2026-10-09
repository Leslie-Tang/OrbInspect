# Final submission audit — 9 October 2026

## Verdict and author actions

The manuscript passes the technical, numerical, reference-resolution, and PDF
checks described below. Verified editorial inconsistencies were corrected
locally. The main manuscript is 13 pages, the supplement 2 pages, and the cover
letter 1 page. Approved figure artwork and experimental results were preserved.

**Before submission, the authors still need to verify the scope of the added
AI-use acknowledgment and confirm the submission declarations.** This audit
did not submit or publish the manuscript.

| Priority | Item | Action |
| --- | --- | --- |
| Before submission | An AI-use acknowledgment is now active in `main.tex`; recorded assistance extends beyond grammar correction. | Confirm that its named sections and assistance types accurately reflect actual use. Edit and rebuild if needed. |
| Before submission | Originality, no conflicting concurrent submission, and approval by all authors are not established by the available correspondence. | The submitting author must confirm these facts. The cover letter contains no unsupported assertion about them. |
| At upload | Original video is 111,017,886 bytes, above IEEE's stated 100 MB limit. | Use the 88,930,328-byte derivative in `output/supplementary/submission/`, with its README and supplementary PDF. |
| If submitting later | Cover letter is dated 9 October 2026. | Update `SubmissionDate` and rebuild the letter. |

The AI disclosure is an IEEE publishing requirement, not a new approval rule
imposed by this audit. The active text does not assert that author validation
has already occurred. A public code release/archival DOI remains an author decision;
the commented availability statement was not enabled.

This is a direct technical/editorial audit, not an independent replication or
a guarantee of acceptance. Three planned isolated reviewer sessions failed
at the model service before delivering reports; no independent reviewer
consensus is claimed.

## Corrections made

1. Added the confirmed corresponding-author email and corrected main/supplement
   PDF metadata to include all five named authors.
2. Clarified selection among candidate viewpoints, rather than implying
   continuous optimization of arbitrary camera poses.
3. Replaced residual “uncertified completions” language with action-level
   certificate wording. The discussion now states that failure to obtain a
   finite rollout value does not prove graph infeasibility.
4. Scoped a failure statement to cases not completed by depth-three ADP;
   one-step ADP and seeded local search can also fail solvable cases.
5. Distinguished transfer-only graph durations from ROS durations including
   terminal settling.
6. Defined the positive denominator guard in the method and moved its
   numerical value, 0.05, into the experimental protocol.
7. Added the Table II callout before presentation, corrected the ROS reference
   from Supplementary S4 to S5, and simplified a diagnostic subsection reference.
8. Added implemented camera range (2–54 m) and incidence limit (60 degrees)
   alongside the rectangular 70-by-50-degree planner FOV.
9. Added Gazebo camera/transport details to S5: perspective RGB, 960-by-686,
   15 Hz, clipping 0.1–120 m, 0.45 m offset, and ROS image topic/type. Rendered
   vertical FOV is approximately 53.2 degrees; credit uses the planner's
   50-degree gate. Rendered imagery does not determine target credit.
10. Corrected Wertz, Everett, and Puschell to editors of *Space Mission
    Engineering: The New SMAD*.
11. Restored Alexander Lucke/CC BY-SA 3.0 camera-photo attribution and
    source/license links in Fig. 1. Asset notes now distinguish the historical
    ISS photograph from the current mesh rendering.
12. Updated current figure/table references in project documentation while
    retaining historical asset names and provenance.
13. Removed a redundant phrase from the cover letter's opening sentence.
14. Enabled a factual AI-use acknowledgment naming the system and scope,
    without claiming that author validation is already complete.

## Mathematics and implementation

- HCW dimensions, matrix signs, and identity notation agree with the model.
  The RK4-induced matrices describe the map evaluated by direct RK4 stages.
- The boundary solve uses the terminal influence/Gram system, then propagates
  requested input without clipping before auditing it. The minimum-norm
  formula assumes full row rank. Feasibility comes from subsequent audits,
  not from the unconstrained minimum-energy solution alone.
- Rectangular FOV, positive forward depth, range, incidence, and LOS tests
  agree with the stated visibility model. Set-valued node masks enter logical
  updates through indicator vectors.
- RMS distance uses all post-step samples; terminal position/velocity errors
  use the final sample. Their cost and admissibility roles are distinct.
- The tuple state contains current node, covered targets, selected nodes,
  and remaining budget. The transition updates both masks and decreases the
  budget. Shield-admissible zero-gain connectors remain available.
- The rollout completion/base-policy bound is consistent with a deterministic
  graph, exhaustive prefixes, a fixed deterministic Markov base policy, and
  decreasing budget. It bounds graph cost, not physical maneuver increment
  alone, and does not ensure success whenever an arbitrary feasible route exists.
- Exact recursion and proven MILP optima concern the specified finite graph,
  not omitted viewpoints or continuous-space trajectories.
- Safety is conditional on enabled deterministic sampled-state and swept
  intersection audits. Passive-drift auditing is disabled. Robust navigation
  uncertainty, attitude dynamics, and continuous-time safety are not established.

**67 focused tests passed** across required-route MILP, advanced planner,
required-target study, mesh spatial index, offline CW trajectory, visibility
checker, and HCW dynamics modules. No mathematical or ROS implementation was
modified, so a ROS workspace rebuild was unnecessary for these editorial edits.

## Numerical and experimental consistency

Headline values were recomputed from archived CSV records. See
`output/submission_audit_20261009/recomputed_headline_results.json`.

| Claim | Recomputed result | Scope |
| --- | --- | --- |
| All-solvable completion | Depth-three 59/59; one-step 57/59; greedy 33/59; MILP feasible 59/59 | Three 33-view graphs; four visibility-infeasible stress cases remain separate. |
| Proven-optimum gap | 27 cases; mean 0.9600659% | Largest gap is 9.6248661%; “mean 0.96%” is correct, “within 0.96%” is not. |
| Median nominal/shifted time | ADP 4.17254/2.08529 s; MILP 15.00651/5.37335 s | Archived implementation timings, not controlled cross-host measurements. |
| Fixed-library saving | 43 pairs; mean ADP 14.0333672 m/s, local search 15.7771357 m/s | Reduction of paired means is 11.0525037%, matching 11.05%. |
| Shifted paired result | 8 pairs; mean ADP 14.6807902 m/s, local 15.8882890 m/s | Aggregate ADP mean uses all 9 ADP completions, a different denominator. |
| Fixed-library feasibility | Test: 43 complete/7 visibility-infeasible; shifted: 9/21 | Raw 43/50 and 9/30 are not success rates conditioned on solvability. |
| Independent pilot audit | 252 method–case records, 3,267 numeric edges, 66 base-policy bounds | Archived audit passes; every experiment was not rerun in this review. |

Table IV agrees with the current all-solvable benchmark: 3 base, 30 nominal,
and 26 shifted feasible cases, totaling 59. It is distinct from the original
50-test/30-shifted confirmation campaign.

The depth diagnostic is presented earlier for exposition but explicitly took
place after the frozen confirmation. It supports retaining depth three for
the subsequent pilot, not a retroactive pre-confirmation tuning claim.

## ROS, figures, and PDF inspection

- Selected twelve-view execution: 9/9 targets, 95.86% weighted background
  coverage, 90 s transfers, and 60 s settling. Executed/reference increments
  are 20.477/18.027 m/s. This is simulation evidence without a paired ROS
  maneuver-saving estimate or a physical experiment.
- Current Fig. 6 contains twelve accepted views; Fig. 7 contains the RViz
  overview. Fig. 6 observation 9 and Fig. 7 transfer 9–10 both display 76.3%
  from the same saved coverage ratio. Fig. 7 retains separate LaTeX subfigures
  and does not repeat the final accepted camera view.
- Figure notation, captions, cross-references, and approved exports were
  checked. All **68 figure-file integrity checks pass**; artwork is unchanged.
- All main, supplement, and cover-letter pages were visually reviewed.
  No clipping, overlap, unresolved labels, or overfull boxes were found.
  Underfull spacing warnings remain. References flow naturally across pages
  12–13; the unused final right column is a layout limitation, not missing text.
- After adding the AI-use acknowledgment, the 13-page main PDF was rebuilt and
  pages 12–13 were inspected again. The final minimal source ZIP was rebuilt in
  an isolated temporary directory: both TeX files compile, the acknowledgment
  appears in the compiled main PDF, and the final logs have no undefined or
  overfull diagnostics. See `output/submission_audit_20261009/portable_source_validation.json`.

The submission video is a two-pass H.264 re-encode of the archived normal-speed
recording. It retains 1920-by-1080 resolution, 15 fps, 1816.8 s duration, and
12 observation chapters. Full decode passed, with frames extracted at 0, 750,
1365, and 1805 s for inspection. Compression changes pixels; the original is
preserved unchanged. No new simulation was run.

## Reference audit

The manuscript cites 34 references. All 28 DOI-bearing cited records resolved
and normalized titles matched. Six no-DOI entries were checked against available
publisher, institutional, author, or NASA sources. LaValle's technical report
received a bibliographic check rather than a full-text content review.
Crossref anomalies were not copied blindly: Kimura's author order is supported
by the author's institutional bibliography. Tweddle's 2016 print year is correct.

There are no undefined citations, duplicate labels, or missing graphics.
The unused `kiumarsi2018survey` entry is not printed and is harmless. Metadata
verification does not mean that every cited article was read in full.

## Official policy checks

Checked 9 October 2026:

- [TAES author information](https://ieee-aess.org/publications/transactions-aes/author-information):
  no Regular Paper manuscript page limit; USD 200 per final printed page beyond
  ten. Thirteen final pages would imply approximately USD 600, subject to
  production pagination and the applicable rules. Review is single anonymous.
- [IEEE submission policies](https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/):
  disclose generated content as applicable, identifying system and scope in
  acknowledgments. Grammar-only assistance is treated differently.
- [IEEE supplementary-material instructions](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/prepare-supplementary-materials/):
  submit technical supplements for initial review, include a README, and
  observe the stated 100 MB video limit.

The official linked TAES template was downloaded and compared with the local
class. Core page/column geometry agrees; no class replacement or font reduction
was needed.

## Delivery files

All paths below are relative to the repository root.

| File | Role |
| --- | --- |
| `OrbInspectLatex/main.pdf` | Checked main PDF; authors should verify the active disclosure's scope before actual submission. |
| `OrbInspectLatex/supplement.pdf` | Checked technical supplement. |
| `OrbInspectLatex/submission/coverletter.pdf` | One-page cover letter with confirmed contact. |
| `output/supplementary/submission/Supplementary_Video_1.mp4` | Normal-speed video below 100 MB. |
| `output/supplementary/submission/Supplementary_Material.pdf` | Supplement copy for supplementary uploads. |
| `output/supplementary/submission/README.txt` | Packing list, description, contact, playback guidance, and provenance. |
| `output/submission_audit_20261009/OrbInspect_TAES_manuscript_source.zip` | Minimal portable TeX/figure snapshot including the active disclosure; excludes internal notes and its draft. Regenerate after further author changes. |
| `OrbInspectLatex/build/OrbInspectLatex_source.zip` | Broader author working package with data/internal documentation; not the minimal manuscript upload. |

The minimal source archive is not the full ROS implementation. No public code
release or archival identifier is asserted. Before/after renders, source hashes,
reference metadata, numerical checks, video logs, and the immutable pre-edit
packet are under `output/submission_audit_20261009/`. Pre-existing worktree edits
and historical deletions were preserved.

## Residual scientific limitations

The principal reviewer risks concern scope: dependent development cases on one
station geometry, single-run timing diagnostics, a finite deterministic graph,
and a selected ROS development execution with refined viewpoints. Those limits
remain explicit. A larger frozen multi-geometry evaluation, repeated timings,
and uncertainty/hardware validation would strengthen the evidence, but none
was fabricated or silently added during this final check.
