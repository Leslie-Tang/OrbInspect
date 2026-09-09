# Figure 8 source frame

`20260909_113140_hybrid12_rviz_video/` contains the selected video frame and
unaltered audit snapshots from the separately recorded repeat execution
`20260909_113140_hybrid12_rviz_video_execution`.

The selected frame is at 1375.0 s in the 15 fps recording (frame index 20625),
during transfer from observation 9 to 10. Its central-module close view avoids
repeating the last camera panel in Figure 7. Both Figure 8 panels come from this
one 1920 by 1080 frame, saved as `video_transfer_09_to_10.png`.
`source_manifest.json` records exact crop rectangles and all source-file hashes.
Only rectangular cropping is applied; the original pixel values and image
aspect ratios are retained. No brightness, contrast or color edits are applied.

The global crop retains the station, complete planned route, executed track
up to this frame and camera field
of view. The camera crop retains the entire displayed camera image. Interface
controls and empty surrounding space are excluded. Progress counts and weighted
coverage come from the last accepted event before this frame in
`video_events.jsonl`: 9/12 observations, 7/9 required targets and 76.27% coverage.
The recorded video/event offset is used to locate the frame within the transfer;
the estimated mission time is 1374.01 s. These are progress values, not the final
run totals. The original completion frame remains as `video_completion.png`
for provenance; it is no longer used in the active figure.

This source frame illustrates a different execution from Figure 7, whose
separately dated evidence remains under `data/required_target_ros/`.
It is a single illustrative run, not an aggregate or a new performance study.
The full recording is supplied separately as Supplementary Video 1; see
`../../docs/FIGURE_8_RVIZ_OVERVIEW_20260909.md` for the video checksum and location.

The snapshots' original absolute paths are provenance, not LaTeX dependencies.
The generator uses only files included in this manuscript directory.
