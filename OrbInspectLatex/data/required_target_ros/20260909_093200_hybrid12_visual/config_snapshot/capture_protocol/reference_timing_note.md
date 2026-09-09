
## Timing and startup-scene diagnostics

The publisher-reported maximum reference interval was 0.248723052 s, exceeding
the 0.075-s nominal diagnostic. The separate count-completion gate passed with
36,186 published references against a minimum 35,640. The recorded reference
headers have a maximum gap of 0.051313877 s; this does not replace or erase the
publisher diagnostic, which includes publication history beyond the recorded
sample set. Both reports are retained in `reference_timing_diagnostic.json`.

Camera recording began before the chaser was spawned. Scene messages with no
named chaser are retained in the original JSONL and listed separately in the
camera audit; no pose is synthesized. The initial preparation failure is
retained. All selected frames still satisfy the unchanged temporal bracketing,
0.2-s receipt, 0.041-s scene-time, 0.1-m position and 0.5-degree orientation gates.
