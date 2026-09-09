# Figure 1: compact publication typography

This is the selected five-panel orbital-inspection figure with the repeated
in-image title removed, bold type limited to the panel headings, and vertical
whitespace reduced. The canvas changes from 1680 x 1160 to 1680 x 990, a 14.66%
height reduction at unchanged width. The title remains in the manuscript caption.

Colors, panel ordering, scientific statements, mathematical tokens, and archived
data are unchanged. The ISS illustration, LOS/FOV construction, HCW trajectory,
and equal-aspect route are rigid translations, not vertically stretched images.
The camera photograph is unchanged and embedded independently.

## Files and editability

- `viability_preserving_rollout_adp.drawio`: editable master. Open in draw.io with
  mathematical typesetting enabled; LaTeX expressions and text remain editable.
- Matching `.svg`, `.pdf`, and `.png`: review/publication exports from the same
  native cell geometry. The PDF is 182 mm wide; the manuscript fits it to the
  unchanged two-column text width.
- `NOTATION_NOTES.md`: definitions of compact notation and example identifiers.
- `QA.json`: geometry, palette, image-byte, label, and mathematical-token checks.
- `source/`: the typography revision and shared mathematical-label renderer.

Regular labels are normalized toward one text size and fitted to their boxes;
panel headings form the only bold tier. The Bellman equation remains prominent
through its existing colored box, not an oversized title. No overall shrink
operation is applied. Equations are vector outlines in exports for font fidelity,
with the canonical editable LaTeX retained in draw.io. Ordinary text is selectable
in the PDF. Live draw.io/MathJax rendering was not verified on this host; shared
native/export sources and the final PDF appearance are checked separately.

The source is the preceding notation-aligned integrated alternative. Its B1/B2
alternatives and prior packages are retained unchanged. No simulation was rerun,
and no manuscript prose, results, equations, caption, or page dimensions changed.

## Image credits

ISS geometry: NASA, [International Space Station 3D Model](https://science.nasa.gov/resource/international-space-station-3d-model/),
projected from the repository's transformed GLB mesh. It is a model illustration,
not a photograph or a new inspection result.

Camera photograph: Alexander Lucke, [SVCam-ECO Series black with Tubus](https://commons.wikimedia.org/wiki/File:SVCam-ECO_Series_black_with_Tubus.JPG),
[CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). The photograph is
reproduced unmodified, without cropping or retouching. All diagram annotations
are separate objects. It illustrates sensing hardware, not a selected or
space-qualified camera. The photograph retains its source license.
