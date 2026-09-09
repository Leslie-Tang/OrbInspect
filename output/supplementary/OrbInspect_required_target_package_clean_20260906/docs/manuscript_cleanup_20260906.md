# Manuscript cleanup and editable Figure 1 — 2026-09-06

## Requested scope

1. Cite every figure in the paper body.
2. Redraw Figure 1 in PPT or draw.io using the attached pastel-stage reference style.
3. Remove repeated narration and unnecessarily cautious prose while retaining IEEE TAES presentation and ADP as the main contribution.

The reference image supplied visual direction only. Its Docs2KG content was not incorporated into the orbital-inspection method.

## Changes

- Replaced Figure 1 with an editable draw.io diagram: five pastel stages, outlined station/camera/graph/route schematics, native labels and connectors, and a visible rollout replanning loop. All 138 XML cells are native structure, not an embedded screenshot. Supplied matching SVG, PDF and PNG exports. Placed the vector figure across both columns for readable labels. Other figure assets, styles, and panel layouts are unchanged.
- Added body references for the depth diagnostic, paired performance, component/safety comparison, and representative route. Existing workflow, ADP architecture, and historical ROS references remain.
- Shortened the abstract, introduction, related work, algorithm narration, protocol, results, discussion, conclusion and captions. Consolidated repeated statements about target versus background coverage, finite-model guarantees, desktop timing, and historical versus current execution evidence.
- Kept assumptions near the model, campaign chronology in the protocol, and remaining generalization limits in one scope-and-limitations subsection. Removed one redundant scope remark; all formal propositions, theorem, equations and proof blocks are unchanged.
- Clarified that the seeded local-search baseline reverses the order of its existing observations and does not introduce new viewpoints.

## Figure-reference audit

| Figure | Body location | Reference count outside figure environments |
| --- | --- | ---: |
| 1 — OrbInspect workflow | Introduction | 1 |
| 2 — Rollout architecture | Adaptive base policy and rollout value | 1 |
| 3 — Depth-one-to-six diagnostic | Complexity and experimental protocol | 2 |
| 4 — Paired performance | ADP policy improvement at matched completion | 1 |
| 5 — Component and safety comparison | Objective ablation and safety | 1 |
| 6 — Representative required-target route | Representative route | 1 |
| 7 — Historical camera-linked execution | Historical corrected ROS 2 survey execution | 1 |

## Preserved scientific boundaries

- The method is model-based rollout ADP, not a newly trained DRL actor or critic.
- Completion concerns fixed prescribed samples under the stated camera model, not full ISS surface imagery or demonstrated defect detection.
- Completion preservation and base-cost no-degradation retain their finite deterministic graph and base-policy assumptions; exact optimality requires exhausted search.
- All required-target results remain offline, with the historical corrected ROS survey reported separately.
- The nine-target confirmation, retained failures, shifted scenarios, six-depth diagnostic and test-depth separation are unchanged.
- The timing procedure, single-graph scope, uncertainty assumptions, and disabled passive-drift audit remain disclosed.
- No experiments, source implementation, archived result data, or earlier deliverables were changed for this editorial revision.

## Verification

- Rebuilt successfully using the existing IEEE TAES class with pdfLaTeX/BibTeX through latexmk.
- No undefined references/citations, duplicate labels, overfull boxes, or LaTeX errors in the final build log. Nonblocking underfull-box warnings remain from two-column justification.
- All seven figures have explicit body references; their order and labels resolve in the compiled article.
- Compared with the depth-one-to-six baseline: all 29 formal mathematical/proof blocks are identical; eight generated data-table/macro files and 16 existing figure inputs are byte-identical.
- Page count: 14 to 12. PDF text extraction: 10,959 to 8,838 whitespace-separated words, approximately 19.4% shorter (including captions, labels, tables and references; not an editorial prose-only count).
- Rendered all 12 pages for visual inspection, including enlarged checks of Figure 1, the depth diagnostic, results panels, representative route and historical ROS figure.
- Imported the .drawio file into the actual draw.io editor and confirmed native shape/label rendering and editability.

## Deliverables and source

- `output/pdf/OrbInspect_IEEE_TAES_required_targets_clean_20260906.pdf`
- `OrbInspect_Overleaf_required_targets_clean_20260906.zip`
- `output/supplementary/OrbInspect_required_target_package_clean_20260906.zip`
- `OrbInspectLatex/figures/required_target/orbinspect_framework.drawio`
- `OrbInspectLatex/scripts/generate_editable_framework.py`

Earlier depth-one-to-six, required-target and survey versions remain preserved. The new source and evidence archives include file checksums and the editable diagram source. Future manual draw.io changes should be exported from the editor; regenerating from the shared-geometry script restores this authored version.
