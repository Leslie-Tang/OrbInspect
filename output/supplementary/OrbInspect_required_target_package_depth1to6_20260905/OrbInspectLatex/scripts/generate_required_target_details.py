#!/usr/bin/env python3
"""Reconstruct required-target route evidence and preserve IEEE panel layouts.

The case is illustrative, selected by the median graph-cost effect among
jointly complete test pairs. Dynamics are repropagated, never drawn as chords.
Each reconstructed cost and velocity increment must match its archived row.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np

import generate_adp_future_figures as legacy
import generate_depth_tradeoff_figure as depth_style
from generate_required_target_figures import read_rows, paired, success
from orbinspect_guidance.offline_adp_superiority_study import load_archived_graph
from orbinspect_guidance.offline_planning_experiment import ExperimentConfig, OfflinePlanningExperiment

ROOT = Path(__file__).resolve().parents[2]
ADP, LOCAL = 'adaptive_rollout_adp', 'seeded_local_search'


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, required=True)
    args = parser.parse_args()
    study = args.study.resolve()
    paper = ROOT / 'OrbInspectLatex/figures/required_target'
    generated = []

    def save(fig, name):
        for suffix in ('pdf', 'png', 'svg'):
            path = study / 'figures' / f'{name}.{suffix}'
            fig.savefig(path)
            shutil.copy2(path, paper / path.name)
            generated.append(str(path.relative_to(ROOT)))
        plt.close(fig)

    depth_style._style()
    plt.rcParams['svg.fonttype'] = 'none'
    rows = read_rows(study / 'raw/validation_depth_results.csv')
    depths = sorted({int(row['adaptive_rollout_depth']) for row in rows})
    groups = {d: [r for r in rows if int(r['adaptive_rollout_depth']) == d] for d in depths}
    common = set.intersection(*[{r['scenario_id'] for r in g if success(r)} for g in groups.values()])
    series = (
        ([np.mean([float(r['graph_cost']) for r in groups[d] if r['scenario_id'] in common]) for d in depths],
         'Mean complete-task graph cost, $J$', 'a', False),
        ([np.median([float(r['online_time_s']) for r in groups[d]]) for d in depths],
         'Median online time (s, log scale)', 'b', True),
        ([np.mean([float(r['safe_action_evaluations']) for r in groups[d]]) for d in depths],
         'Mean safety-screen evaluations (log scale)', 'c', True),
    )
    for values, ylabel, suffix, log in series:
        fig, ax = plt.subplots(figsize=(2.18, 2.45))
        ax.plot(depths, values, color=depth_style.BLUE, marker='o', markersize=4.6,
                markerfacecolor='white', markeredgewidth=1.05, zorder=2)
        ax.scatter([3], [values[depths.index(3)]], color=depth_style.RED, marker='s', s=38,
                   edgecolor=depth_style.BLACK, linewidth=.35, zorder=3)
        if log:
            ax.set_yscale('log')
        ax.set_xticks(depths)
        ax.set(xlabel='Rollout depth, $d$', ylabel=ylabel)
        ax.grid(axis='y', which='both', color='#ECECEC', linewidth=.6)
        note = f'common complete n = {len(common)}' if suffix == 'a' else 'validation diagnostic'
        ax.text(.02, .05, note, transform=ax.transAxes, ha='left', va='bottom', color=depth_style.GREY, fontsize=7)
        fig.tight_layout(pad=.35)
        save(fig, f'adp_depth_tradeoff_{suffix}')

    legacy._style()
    plt.rcParams['svg.fonttype'] = 'none'
    primary = json.loads((study / 'config_snapshot/freeze_manifest.json').read_text())['primary_profile']
    rows = [r for r in read_rows(study / 'raw/scenario_results.csv') if r['profile_id'] == primary]
    comparisons = paired(rows, 'test')
    median = float(np.median([float(a['graph_cost'])-float(b['graph_cost']) for a,b in comparisons]))
    selected = min(comparisons, key=lambda pair: (abs(float(pair[0]['graph_cost'])-float(pair[1]['graph_cost'])-median), pair[0]['scenario_id']))
    archived = {r['method']:r for r in selected}
    scenario_id = selected[0]['scenario_id']
    scenario = next(r for r in json.loads((study/'raw/scenarios.json').read_text()) if r['scenario_id']==scenario_id)
    graph = load_archived_graph(study/'raw/hcw_graph.json')
    values = json.loads((study/'config_snapshot/base_experiment_config.json').read_text())
    values.update(output_root=study, methods=(), initial_state=tuple(values['initial_state']))
    experiment = OfflinePlanningExperiment(ExperimentConfig(**values))
    candidates = {c.candidate_id:c for c in experiment.candidates}
    masks = dict(zip(graph.node_ids,graph.coverage_masks))
    required = int(scenario['required_target_mask'])
    trajectories, progress = [], []
    for method in (ADP,LOCAL):
        state = experiment.config.initial_state
        time, dv, cost, covered = 0.,0.,0.,0
        progress.append(dict(method=method,action=0,candidate_id='initial',required_coverage=0.,weighted_coverage=0.,whole_sample_coverage=0.,cumulative_delta_v=0.,cumulative_graph_cost=0.,covered_target_mask=0))
        for action,node in enumerate(archived[method]['route_node_ids'].split(';'),1):
            transfer = experiment._estimate_transfer_from_state(state,candidates[node])
            if not transfer.feasible:
                raise RuntimeError(f'Reconstructed edge failed: {method} {node}')
            dv += transfer.delta_v
            cost += experiment._dynamic_transfer_cost(transfer)+.05
            covered |= masks[node]
            for sample,(t,x,u) in enumerate(transfer.trajectory):
                trajectories.append(dict(method=method,action=action,sample=sample,time_s=time+t,
                                         rx=x[0],ry=x[1],rz=x[2],vx=x[3],vy=x[4],vz=x[5],ux=u[0],uy=u[1],uz=u[2]))
            weighted = sum(w for i,w in enumerate(scenario['target_weights']) if covered & (1<<i))/sum(scenario['target_weights'])
            progress.append(dict(method=method,action=action,candidate_id=node,required_coverage=(covered&required).bit_count()/required.bit_count(),
                                 weighted_coverage=weighted,whole_sample_coverage=covered.bit_count()/90,cumulative_delta_v=dv,
                                 cumulative_graph_cost=cost,covered_target_mask=covered))
            time += experiment.config.transfer_duration
            state = transfer.next_state
        for measured,field in ((dv,'total_delta_v'),(cost,'graph_cost')):
            if not math.isclose(measured,float(archived[method][field]),rel_tol=1e-10,abs_tol=1e-10):
                raise RuntimeError(f'{method} reconstructed {field}={measured} differs from archive={archived[method][field]}')
        if (covered&required)!=required:
            raise RuntimeError('Illustrative route misses a required target')
    write_csv(study/'raw/representative_case_trajectory.csv',trajectories)
    write_csv(study/'raw/representative_case_progress.csv',progress)
    coords={m:np.array([[r['rx'],r['ry'],r['rz']] for r in trajectories if r['method']==m]) for m in (ADP,LOCAL)}
    styles=((ADP,legacy.PROPOSED_COLOR,'o','-','Rollout ADP'),(LOCAL,legacy.LOCAL_COLOR,'s','--','Seeded local'))
    fig=plt.figure(figsize=(2.28,2.55))
    ax=fig.add_subplot(111,projection='3d')
    mesh=experiment.base_planner.mesh_geometry
    indices=np.linspace(0,len(mesh.triangles)-1,1800,dtype=int)
    ax.add_collection3d(Poly3DCollection([mesh.triangles[int(i)].vertices for i in indices],facecolor=legacy.ROSE,edgecolor='none',alpha=.10))
    for m,color,marker,line,label in styles:
        pts=coords[m]
        ax.plot(*pts.T,color=color,linestyle=line,label=label)
        ends=np.array([graph.node_positions[graph.node_ids.index(n)] for n in archived[m]['route_node_ids'].split(';')])
        ax.scatter(*ends.T,color=color,s=10,depthshade=False)
    targets=np.array([t.position for t in experiment.targets if t.target_id in scenario['required_target_ids']])
    ax.scatter(*targets.T,marker='D',s=9,facecolors='none',edgecolors=legacy.PURPLE,linewidths=.5,depthshade=False,label='Required samples')
    ax.scatter(*experiment.config.initial_state[:3],marker='*',s=48,color=legacy.GREEN,edgecolor=legacy.BLACK,linewidth=.3,label='Initial state')
    legacy._equal_axes(ax,list(coords.values())+[targets])
    ax.set_xlabel('$x$ (m)',labelpad=-3); ax.set_ylabel('$y$ (m)',labelpad=-3); ax.set_zlabel('')
    ax.text2D(1.16,.52,'$z$ (m)',transform=ax.transAxes,rotation=90,ha='center',va='center',clip_on=False)
    ax.tick_params(axis='both',which='major',labelsize=8.2,pad=-1)
    ax.view_init(elev=24,azim=-56)
    ax.legend(frameon=False,loc='upper left',bbox_to_anchor=(-.03,1.01),fontsize=6.9,handlelength=1.6,labelspacing=.25)
    fig.subplots_adjust(left=0.,right=.96,bottom=.01,top=.98)
    save(fig,'adp_representative_trajectory_a')
    for field,ylabel,suffix in (('required_coverage','Required-target completion (%)','b'),('cumulative_delta_v',r'Cumulative $\Delta v$ (m/s)','c')):
        fig,ax=plt.subplots(figsize=(2.25,2.45))
        for m,color,marker,line,label in styles:
            p=[r for r in progress if r['method']==m]
            ax.plot([r['action'] for r in p],[r[field]*(100 if suffix=='b' else 1) for r in p],marker=marker,markersize=3.2,color=color,linestyle=line,label=label)
        if suffix=='b':
            ax.axhline(100,color=legacy.GREY,linestyle=':',linewidth=.9,label='Required goal')
            ax.set_ylim(0,110)
        ax.set(xlabel='Executed SOOA count',ylabel=ylabel)
        ax.grid(color='#ECECEC',linewidth=.6)
        ax.legend(frameon=False,loc='upper left',fontsize=6.9,handlelength=1.6,labelspacing=.25)
        fig.tight_layout(pad=.35)
        save(fig,f'adp_representative_trajectory_{suffix}')
    manifest={'selection_rule':'Jointly successful test pair nearest the median ADP-minus-local graph-cost difference; scenario-ID tie break; illustrative only',
              'scenario_id':scenario_id,'seed':scenario['seed'],'required_target_ids':scenario['required_target_ids'],
              'test_median_cost_difference':median,'methods':archived,'validation_common_success_n':len(common),
              'source_csv_sha256':hashlib.sha256((study/'raw/scenario_results.csv').read_bytes()).hexdigest(),
              'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'generated_files':generated}
    (study/'raw/representative_case_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    text=(f'The illustrative pair is scenario \\texttt{{{scenario_id.replace("_", r"\_")}}}, selected as the jointly complete test pair nearest the median ADP-minus-local graph-cost difference (deterministic ID tie break). '
          f'Both routes complete all {required.bit_count()} prescribed targets. Rollout ADP uses {archived[ADP]["selected_count"]} SOOAs, $J={float(archived[ADP]["graph_cost"]):.3f}$, and $\\Delta v={float(archived[ADP]["total_delta_v"]):.3f}~\\mathrm{{m/s}}$; '
          f'local search uses {archived[LOCAL]["selected_count"]} SOOAs, $J={float(archived[LOCAL]["graph_cost"]):.3f}$, and $\\Delta v={float(archived[LOCAL]["total_delta_v"]):.3f}~\\mathrm{{m/s}}$. '
          f'The respective background inspectable scores are {100*float(archived[ADP]["coverage"]):.2f}\\% and {100*float(archived[LOCAL]["coverage"]):.2f}\\%. Repropagation reproduces both archived costs and velocity increments to numerical tolerance.\n')
    (ROOT/'OrbInspectLatex/data/required_target_case.tex').write_text(text)
    print(json.dumps({'scenario_id':scenario_id,'figures':len(generated)},indent=2))


if __name__=='__main__':
    main()
