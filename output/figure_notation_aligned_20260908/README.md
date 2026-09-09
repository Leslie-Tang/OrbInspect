# Manuscript-aligned notation in three editable figure alternatives

All three figures retain their preceding layouts, colors, mesh/camera assets,
archived HCW transfer and inspection route. Only notation and associated label
typesetting have changed. The manuscript has not been modified.

Open OrbInspect_figure_options.drawio for the three-page editable master, or
A_integrated.drawio, B1_overview.drawio and B2_adp_mechanism.drawio individually.
Mathematical typesetting is enabled in each file. Edit the LaTeX between the
inline math delimiters in a text label; ordinary words remain ordinary text.
Draw.io supports this through Extras > Mathematical Typesetting. See the
[official documentation](https://www.drawio.com/docs/manual/text/math-typesetting/).
If a viewer does not load MathJax, open the file in draw.io with typesetting
enabled; the formulas are not flattened screenshots.

Every revised label is stored as one canonical list of text/LaTeX runs. The native
draw.io values and review SVG/PDF math are generated from that same list, with
programmatic equality checks. Review math glyphs are outlined for reliable font
display; their editable LaTeX is retained in draw.io. Ordinary export text remains
selectable. Browser/MathJax and Python renderers may differ slightly in glyph
metrics; no claim of pixel-identical font rasterization is made.

The live MathJax browser check could not complete on this host: its private
headless browser failed to initialize even on a blank page. Shared LaTeX source
equality and Python/PDF rendering were checked; live draw.io rendering is not
reported as a passed test. The supplied notation follows draw.io's documented
mathematical-typesetting interface, with display-style operators enabled.

The corrections include calligraphic sets, barred terminal observation poses,
bold translational vectors, proper action-value hats and depth indices, state
arguments in base-policy values, and superscript action stars. Ambiguous action
labels a_1/a_2 were removed. Camera range is labelled in words to avoid reusing
the passive-clearance symbol. Mathematical meaning is unchanged.

See NOTATION_NOTES.md for compact caption-ready explanations of the incidence
angle, candidate identifiers, complete-tail summation and finite-value selection.
The audit records exact preservation of all unaffected drawing objects and source
file hashes, together with the shared native/export math tokens.
