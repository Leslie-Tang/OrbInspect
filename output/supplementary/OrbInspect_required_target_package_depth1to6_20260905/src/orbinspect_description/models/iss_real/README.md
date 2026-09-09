# iss_real

NASA International Space Station GLB asset shared by planning audits and
Gazebo Harmonic visualization.

The offline planner and post-run execution audit apply the complete glTF scene
hierarchy (matrix or translation--rotation--scale at every ancestor), followed
by the SDF model pose and 1.065 scale, to all target, visibility, distance, and
swept-crossing queries. The online ROS safety filter uses conservative proxy
primitives, including oriented array boxes, while accepted evidence is checked
again against every transformed triangle and a 0.80 m chaser bounding radius.
Gazebo remains visual-only and does not propagate the spacecraft state.
