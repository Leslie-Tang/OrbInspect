# Notation notes for the figure alternatives

These notes supplement the diagrams without enlarging their text or changing
the manuscript. Figure A is the integrated alternative; B1 and B2 form the
complementary overview and ADP-mechanism pair.

## Shared definitions

- $\mathcal K$ is the fixed required-target set; $K$ in the manuscript's HCW
  edge record is a different quantity, the number of transfer steps.
- $s=(j,m,b,h)$ is the generic decision state. Here $j$ is the current node,
  $m$ the covered-target mask, $b$ the selected-view mask, and $h$ the remaining
  action budget. $H$ is the initial budget. Omitting the time subscript $k$ is
  consistent with the manuscript's Bellman equations.
- $a\in\mathcal U_s(s)$ is an audited, unvisited destination choice. An edge
  $a_{ij}$ joins source $i$ to destination $j$; $\ell_{ij}$ and $\chi_{ij}$ are
  its stage cost and audit indicator. At decision state $s$, the corresponding
  indices are $\ell_{ja}$ and $\chi_{ja}$.

## Camera and example identifiers (A and B1)

The camera center and boresight at observation node $j$ are
$\bar{\mathbf r}_j$ and $b(\bar q_j)$. Target position $p_i$ and surface normal
$n_i$ use the manuscript's notation. The displayed range is
$\|p_i-\bar{\mathbf r}_j\|$. The illustrated incidence angle is

$$\theta=\arccos\frac{(\bar{\mathbf r}_j-p_i)^{\mathsf T}n_i}
{\|\bar{\mathbf r}_j-p_i\|\|n_i\|},\qquad\theta\leq\theta_{\max}.$$

The FOV half-angle is $\alpha_{\max}$, and $G_j$ contains camera-valid targets.
The letters $x,z$ on spatial axes name the LVLH directions, corresponding to
position components $r_x,r_z$; bold $\mathbf x$ denotes the six-dimensional state.

C5, C0, C70, C68 and C21 are archived candidate-library identifiers used in the
illustrative graph/transfer, not a replacement for the abstract graph-node
notation $v_j$. In particular, C0 is candidate ID zero, not the distinguished
initial node $v_0$. The initial node is not included in that five-candidate excerpt.

## Base-policy evaluation and backup (A and B2)

At each prefix leaf, $s$ denotes that leaf's state and $\mu$ is the same
deterministic task-aware base policy. The compact finite-tail sum in A means

$$\widehat V_0(s)=\sum_{k=0}^{L-1}\ell_{j_k\mu(s_k)}$$

when the policy reaches $\Gamma_{\mathcal K}(m)=1$ within the leaf's remaining
budget; otherwise $\widehat V_0(s)=+\infty$. Thus the sum includes every stage
cost of the full tail, not merely its first step. Each leaf has its own value.
The displayed branches are schematic, not a branch cap or a fixed depth of two.

The backup is $\widehat Q_d(s,a)=\ell_{ja}+\widehat V_{d-1}(f(s,a))$.
Finite-valued actions compete in the minimization defining $a^\star$;
$s'=f(s,a^\star)$ is the updated planning state. If all admissible actions have
$\widehat Q_d(s,a)=+\infty$, the outcome is no certified completion, not a proof
of physical infeasibility. The words 'required goal reached' denote
$\Gamma_{\mathcal K}(m)=1$. A complete inspection plan is distinct from a
closed-loop flight-execution claim.
