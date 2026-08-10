# Legacy result notice

This directory is retained only as an historical development artifact.  It was
generated before the current 26-feature critic schema and before full-mesh BVH
occlusion and mesh-consistent clearance checks were introduced.  In particular,
its ten stored critic weights are dimensionally incompatible with the current
planner.

These files must not be used as evidence for the revised paper.  Current
paper-facing runs write `config_snapshot/result_manifest.json` with the Git
commit, dirty-worktree flag, result schema, critic feature count, configuration
hash, and ISS mesh hash.
