# IEEE TAES initial-submission cover letter

Adapted from the author-provided `coverletter.tex` and `Polyu-cover.pdf` in
`/home/rugang/Github/6_RADGSEMP/Latex_TASE/forSubmit/`.
The supplied logo is copied unchanged. Scientific claims and the title match
`../main.tex`, reviewed on 9 October 2026. The current manuscript identifies
Zheng Tan as the corresponding author, so the letter is signed in his name.
The author supplied his contact email, `zheng-uav.tan@connect.polyu.hk`, on
9 October 2026; it is now included in the letter.

## Files

- `coverletter.tex`: editable English cover letter.
- `Polyu-cover.pdf`: original PolyU letterhead asset, required for compilation.
- Final rendered PDF: `../../output/pdf/OrbInspect_TAES_coverletter.pdf`.

## Final letter

Finalized on 9 October 2026 for consideration as a Regular Paper. The PDF is
one page, contains the confirmed contact email, and has no drafting placeholders
or conditional declaration text. Its title and quantitative claims were checked
against the current manuscript.

The [published TAES author instructions](https://ieee-aess.org/publications/transactions-aes/author-information)
were checked on 9 October 2026. They do not specify a cover-letter declaration
block. The letter therefore does not assert unconfirmed publication-history,
concurrent-submission, or all-author-approval facts. The corresponding author's
submission obligations still apply; this document is the cover letter, not a
certification of the entire submission package.

The supplied PolyU logo, Charter font, one-inch margins, and header/footer rules
are retained. Update `\SubmissionDate` if submitting on a later date.

## Build

From this folder:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error -outdir=build coverletter.tex
```

## Claim-evidence checks

| Letter statement | Manuscript support | Scope |
| --- | --- | --- |
| Completion preservation and base-policy graph-cost bound | Theorem 1 | Deterministic finite graph, exhaustive prefix evaluation |
| 59/59, 57/59, 33/59 completion | All-solvable benchmark results | Development benchmark with independent feasible certificates |
| Mean 0.96% graph-cost gap | 27 proven MILP optima | Mean over proven-optimal cases, not a universal bound |
| Mean 11.05% maneuver saving | Fixed-library confirmation | 43 jointly completed test missions versus ADP-seeded local search |
| Nine required targets, twelve observations | ROS execution subsection | ROS-native dynamics and Gazebo visualization; simulation evidence |

Canonical terminology: rollout approximate dynamic programming (ADP),
base-policy continuation, graph cost, all-solvable development benchmark,
fixed-library confirmation, ROS 2/Gazebo simulation execution.
No manuscript text or figure artwork is modified by this letter.
