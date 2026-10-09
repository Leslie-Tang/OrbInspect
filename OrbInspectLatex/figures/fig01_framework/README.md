# Figure 1: framework overview

`viability_preserving_rollout_adp.drawio` is the current native editable source.
The PDF, SVG and PNG are the approved matching exports; the manuscript uses
the PDF. The 2026-10-09 revision replaces panel II's planar FOV wedge with a
rectangular viewing pyramid and separate horizontal/vertical half-angle
labels. The range, incidence, and LOS gates remain distinct. The other panels,
workflow arrows, palette, typography, and aspect ratio are preserved.

The five panels use Roman labels I--V. The notation follows the manuscript:
$\mathbf p_i$, $\mathbf n_i$, $\mathbf b(\bar{\mathbf q}_j)$, state
$s=(j,\mathbf m,\boldsymbol\beta,h)$, stored edge $\mathsf a_{ij}$, and
candidate nodes $c_i$. The station illustration derives
from the NASA ISS mesh, and the independent camera image is Alexander Lucke's
photograph under CC BY-SA 3.0, as credited in the manuscript caption.
`assets/camera_alexander_lucke.jpg` is included, while images required to
display the diagram are embedded in the draw.io and SVG files.

The asset evidence and notation notes are preserved provenance from the
precursor alternative A. B1/B2 mentioned in those notes are historical
alternatives, not the current Figure 2. The historical photo-credit note also
describes an earlier ISS photograph; that photograph is not used in this
mesh-based version. The camera attribution remains applicable.

Edit and export from this draw.io file; the historical generator chain is not
required to open or compile it. Keep the exported aspect ratio and inspect
the PDF before changing the approved checksums in `figures/manifest.json`.
The scoped revision script is `tools/paper/rectangular_figure1_fov.py`, which
uses the current native cells and SVG objects and verifies unchanged objects
outside the requested revision.
