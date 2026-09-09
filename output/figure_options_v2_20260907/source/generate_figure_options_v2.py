#!/usr/bin/env python3
"""Revise the editable figure alternatives: LOS, HCW geometry and ADP tails."""
from __future__ import annotations

import copy
import csv
import json
import math
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
import pymupdf

import generate_figure_options as v1
from generate_figure_options import (
    Draft, INK, BLUE, RED, GREY, PALE_BLUE, PEACH, YELLOW, GREEN, GOLD,
    MUTED, BORDER, WHITE, SUCCESS,
)

ROOT = v1.ROOT
OUT = ROOT/'output/figure_options_v2_20260907'
PDF = ROOT/'output/pdf/OrbInspect_figure_options_v2_20260907.pdf'
MINT, ROSE, LAVENDER = '#CBE3D8', '#E9C6C7', '#D7D4E7'


def polygon(d, points, fill, stroke=BORDER, width=1.2, name='Editable geometry'):
    xy=np.array(points,dtype=float); lo=xy.min(axis=0); hi=xy.max(axis=0)
    d.native_paths(*lo,*(hi-lo),[(list(map(tuple,xy-lo)),fill,stroke,width)],name)


def arc(d, center, radius, start, end, color=INK, width=1.4):
    points=[(center[0]+radius*math.cos(t),center[1]+radius*math.sin(t))
            for t in np.linspace(start,end,20)]
    d.line(points,color,width)


def visibility(d,x,y,w,h):
    """Cross-sectional ray geometry, matching the manuscript's visibility tests."""
    gh=h-80
    c=np.array([x+.20*w,y+.48*gh])
    p=np.array([x+.83*w,y+.21*gh])
    blocked=np.array([x+.92*w,y+.83*gh])
    top=(x+.97*w,y+.04*gh); bottom=(x+.97*w,y+.96*gh)
    polygon(d,[tuple(c),top,bottom],'#F2F7FB','#B5C9D7',1.1,'Camera FOV cross-section')
    d.line([tuple(c),(x+.98*w,c[1])],BLUE,1.5,True,True)
    d.photo(x+3,c[1]-43,.20*w-14,86,v1.ASSETS/'camera_alexander_lucke.jpg',
            'Original camera photograph, Alexander Lucke CC BY-SA 3.0; illustrative hardware.',
            'https://commons.wikimedia.org/wiki/File:SVCam-ECO_Series_black_with_Tubus.JPG')
    d.circle(*c,3.8,INK,INK,1)
    d.text(x+3,c[1]+46,.26*w,30,'Camera rⱼ',23,align='left')
    # The target is on a front-facing surface; n_i points towards free space.
    polygon(d,[(p[0],p[1]-31),(p[0]+28,p[1]-18),(p[0]+28,p[1]+45),(p[0],p[1]+31)],
            '#DDE4E9','#8193A0',1.2,'Visible target surface')
    d.line([tuple(c),tuple(p)],SUCCESS,2.6,True)
    d.line([tuple(p),(p[0]-63,p[1])],INK,1.6,True)
    d.circle(*p,5.6,WHITE,GOLD,2.1)
    d.text(p[0]+7,p[1]-64,64,31,'pᵢ',25,align='left')
    d.text(p[0]-73,p[1]-33,47,28,'nᵢ',24)
    d.check(p[0]+52,p[1]+14,SUCCESS,.8)
    angle=math.atan2(c[1]-p[1],c[0]-p[0])
    arc(d,p,36,angle,math.pi)
    d.text(p[0]-59,p[1]+13,35,28,'θ',24)
    d.text(x+.35*w,y+.19*gh,127,30,'Clear LOS',24,True,SUCCESS)
    d.text(x+.47*w,y+.34*gh,46,29,'ρ',25)
    fov_angle=math.atan2(top[1]-c[1],top[0]-c[0])
    arc(d,c,65,fov_angle,0,BLUE)
    d.text(x+.065*w,y+.12*gh,92,31,'αₘₐₓ',24,color=BLUE)
    d.line([(x+.23*w,y+.24*gh),
            (c[0]+65*math.cos(fov_angle/2),c[1]+65*math.sin(fov_angle/2))],BLUE,1)
    d.text(x+.83*w,c[1]+8,.15*w,28,'b(qⱼ)',23,color=BLUE)
    # Explicitly distinguish the ray in free space from the hidden segment.
    obstruction=c+.57*(blocked-c)
    corners=np.array([(obstruction[0]-25,obstruction[1]-25),
        (obstruction[0]+5,obstruction[1]-36),(obstruction[0]+33,obstruction[1]-12),
        (obstruction[0]+25,obstruction[1]+30),(obstruction[0]-25,obstruction[1]+23)])
    cross2=lambda a,b:a[0]*b[1]-a[1]*b[0]
    ray=blocked-c; intersections=[]
    for a,b in zip(corners,np.roll(corners,-1,axis=0)):
        edge=b-a; denom=cross2(ray,edge)
        t=cross2(a-c,edge)/denom; u=cross2(a-c,ray)/denom
        if 0<=t<=1 and 0<=u<=1:intersections.append(t)
    assert len(intersections)==2
    entry=c+min(intersections)*ray
    d.line([tuple(c),tuple(entry)],RED,2,False,True)
    d.line([tuple(entry),tuple(blocked)],MUTED,1.5,False,True)
    ox,oy=obstruction
    polygon(d,corners,
            '#CCD3DA','#798A99',1.3,'Occluding mesh cross-section')
    d.line([(ox-25,oy-25),(ox+25,oy+30),(ox+5,oy-36),(ox-25,oy+23)],'#96A3AE',.9)
    d.cross(*entry,.9)
    d.circle(*blocked,5.4,WHITE,RED,1.7)
    d.text(ox-53,oy+37,111,28,'Mesh',23)
    d.text(blocked[0]-107,blocked[1]+15,126,28,'Occluded',23,color=RED)
    d.text(x+7,y+gh+8,w-14,29,'Range · FOV · incidence · clear LOS',23)
    d.box(x+.22*w,y+gh+46,.56*w,35,WHITE,BLUE,6,1.2)
    d.text(x+.23*w,y+gh+49,.54*w,29,'Valid targets → Gⱼ',24,True)


def hcw(d,data,x,y,w,h):
    """Actual bounded thrust history driving a source-dependent HCW transfer."""
    records=data['hcw_transfer']
    positions=np.array(records['positions_xyz'])[:,[0,2]]
    all_controls=np.array(records['controls_xyz'])
    controls=all_controls[:,[0,2]]
    # The profile shows the full control norm, not a single component bound.
    d.text(x+7,y+1,w*.35,32,'‖u‖ (m/s²)',25,True)
    tx,ty,tw,th=x+47,y+51,w*.27,93
    limit=records['audit_record']['input_limit']
    norm=np.linalg.norm(all_controls,axis=1)
    d.line([(tx,ty),(tx,ty+th),(tx+tw,ty+th)],'#85939E',1.2)
    d.line([(tx,ty),(tx+tw,ty)],RED,1.2,False,True)
    d.text(tx-53,ty-15,48,29,'0.06',22,align='right')
    d.text(tx-35,ty+th-15,27,29,'0',22,align='right')
    d.text(tx+tw-4,ty+th+7,39,29,'t',23)
    profile=[]
    for i,u in enumerate(norm):
        profile.extend([(tx+i/30*tw,ty+th*(1-u/limit)),
                        (tx+(i+1)/30*tw,ty+th*(1-u/limit))])
    d.line(profile,BLUE,2.3)
    d.line([(x+w*.39,y+98),(x+w*.46,y+98)],INK,1.9,True)
    # Equal spatial scale; no 2-D clearance is inferred from this illustration.
    lo,hi=positions.min(axis=0),positions.max(axis=0)
    extent=hi-lo
    ph=134; pw=w*.43
    scale=min(pw/(extent[0]+15),ph/(extent[1]+16))
    center=(lo+hi)/2
    xy=lambda point: (x+w*.715+(point[0]-center[0])*scale,
                       y+ph/2+37-(point[1]-center[1])*scale)
    points=[xy(p) for p in positions]
    d.line(points,BLUE,3)
    d.line(points[15:19],BLUE,3,True)
    tangent=np.array(points[-1])-points[0]; tangent/=np.linalg.norm(tangent)
    perpendicular=np.array([-tangent[1],tangent[0]])
    for i,sign in [(7,1),(22,-1)]:
        vector=controls[i]; vector=vector/np.linalg.norm(vector)*33
        start=np.array(points[i])+sign*perpendicular*18
        target=(start[0]+vector[0],start[1]-vector[1])
        d.line([points[i],tuple(start)],MUTED,1,False,True)
        d.line([tuple(start),target],INK,1.5,True)
    d.circle(*points[0],8,WHITE,BLUE,2)
    d.circle(*points[-1],8,MINT,SUCCESS,2)
    d.text(points[0][0]-35,points[0][1]-35,70,29,'C70',24,True)
    d.text(points[-1][0]+10,points[-1][1]-14,70,29,'C68',24,True)
    d.text(x+.56*w,y+3,w*.40,32,'HCW motion x(t)',25,True)
    # Small coordinate triad indicates projection without decorative grid lines.
    ax=x+w*.47; ay=y+165
    d.line([(ax,ay),(ax+39,ay)],'#82919D',1.3,True)
    d.line([(ax,ay),(ax,ay-38)],'#82919D',1.3,True)
    d.text(ax+39,ay-13,30,26,'x',22)
    d.text(ax-15,ay-66,30,27,'z',22)
    d.text(x+4,y+h-92,w-8,29,'Rest-to-rest · 90 s',24)
    badge_width=(w-16)/3
    for i,label in enumerate(['Input','Mesh','Terminal']):
        bx=x+i*(badge_width+8)
        d.box(bx,y+h-52,badge_width,38,WHITE,BORDER,5,1.1)
        d.text(bx+3,y+h-47,badge_width-28,27,label,23)
        d.check(bx+badge_width-18,y+h-32,SUCCESS,.65)
    return points


def route_thumbnail(d,data,x,y,w,h):
    """Legible x-z route thumbnail with equal scale and no redundant ticks."""
    scale=min((w-24)/120,(h-16)/140)
    px=x+(w-120*scale)/2; py=y+4
    xy=lambda xx,zz:(px+(xx+60)*scale,py+(60-zz)*scale)
    for target in data['targets']:
        d.circle(*xy(*target['xz']),1.3,'#BEC5CA','none',0)
    points=[xy(*p) for p in data['trajectory_xz_m']]
    d.line(points,BLUE,2.4)
    for i in [59,149,238]:d.line(points[i:i+3],BLUE,2.4,True)
    for target in data['targets']:
        if target['required']:d.circle(*xy(*target['xz']),4.1,'none',GOLD,1.7)
    d.circle(*points[0],3.5,INK,INK,1)
    d.circle(*points[-1],4,BLUE,BLUE,1)
    ax=x+16; ay=y+h-20
    d.line([(ax,ay),(ax+28,ay)],'#83909A',1.1,True)
    d.line([(ax,ay),(ax,ay-28)],'#83909A',1.1,True)
    d.text(ax+28,ay-12,28,27,'x',22)
    d.text(ax-13,ay-53,28,27,'z',22)


def adp(d,x,y,w,h,compact=False):
    """Reference-inspired prefix/tail composition with the manuscript's logic."""
    if compact:
        d.text(x,y,w*.44,48,'Lookahead d',25,True)
        d.text(x+w*.46,y,w*.54,48,'Greedy policy tails',25,True)
        root=(x+22,y+109)
        branches=[(x+w*.27,y+71),(x+w*.27,y+151)]
        end=x+w*.53
        for i,mid in enumerate(branches):
            color=BLUE if i==0 else INK
            d.line([root,mid,(end,mid[1])],color,2.1,True)
            d.circle(*mid,10,MINT if i==0 else ROSE,INK,1.4)
            d.line([(end+10,mid[1]),(x+w*.75,mid[1])],color,1.8,True)
            for f in [.59,.66]:d.circle(x+w*f,mid[1],4,WHITE,color,1.2)
            if i==0:
                d.check(x+w*.79,mid[1],SUCCESS,.85)
                d.text(x+w*.83,mid[1]-17,w*.16,34,'Goal',24,True)
            else:d.text(x+w*.79,mid[1]-18,w*.20,36,'+∞',29,True,RED)
        d.circle(*root,12,LAVENDER,INK,1.6)
        d.text(root[0]-20,root[1]-45,40,28,'s',25)
        d.box(x+8,y+h-45,w-16,40,'#F1D8A7',GOLD,6,1)
        d.text(x+18,y+h-41,w-36,31,'Bellman backup → first action',25,True)
        return root,(x+w-8,y+h-25)
    split=x+w*.49
    d.text(x+8,y,w*.45,36,'Finite Bellman prefix',28,True)
    d.text(x+8,y+36,w*.45,31,'Lookahead depth d',25)
    d.text(split+8,y,w*.50-16,36,'Task-aware policy tails',28,True)
    d.text(split+8,y+36,w*.50-16,31,'Deterministic greedy μ',25)
    top=y+116; th=h-260
    levels=[top,top+th*.30,top+th*.68,top+th]
    root=(x+32,top+th*.5)
    mids=[(x+w*.23,top+th*.15),(x+w*.23,top+th*.84)]
    leaves=[(x+w*.43,yy) for yy in levels]
    d.line([(split,y+86),(split,y+h-128)],BORDER,1.4,False,True)
    def edge(a,b,color=INK,width=1.9):
        a,b=np.array(a),np.array(b); unit=(b-a)/np.linalg.norm(b-a)
        d.line([tuple(a+unit*19),tuple(b-unit*18)],color,width,True)
    for i,point in enumerate(mids):
        edge(root,point,BLUE if i==0 else INK,2.5)
        d.circle(*point,17,MINT if i==0 else '#E9D4C7',INK,1.7)
    for i,point in enumerate(leaves):
        edge(mids[i//2],point)
        d.circle(*point,17,MINT if i<2 else ROSE,INK,1.6)
    d.circle(*root,18,LAVENDER,INK,1.8)
    d.text(root[0]-25,root[1]-58,50,32,'s',28)
    d.text(x+w*.07,top+th*.20,w*.13,29,'a₁',26)
    d.text(x+w*.07,top+th*.71,w*.13,29,'a₂',26)
    d.text(x+6,y+h-125,w*.43,35,'a ∈ Uₛ(s)',25)
    # Every prefix leaf is evaluated by a complete tail, not by one further step.
    tail_end=x+w*.72
    for i,(lx,ly) in enumerate(leaves):
        color=BLUE if i<2 else RED
        d.line([(lx+18,ly),(tail_end,ly)],color,2,True,i>=2)
        for f in [.535,.60,.665]:d.circle(x+w*f,ly,4.5,WHITE,color,1.3)
    bx=x+w*.75; bw=w*.245
    d.box(bx,levels[0]-30,bw,levels[1]-levels[0]+60,MINT,SUCCESS,8,1.2)
    d.text(bx+7,levels[0]-16,bw-14,levels[1]-levels[0]+29,'Goal reached\nFinite cost',24,True)
    d.box(bx,levels[2]-28,bw,levels[3]-levels[2]+56,ROSE,RED,8,1.2)
    d.text(bx+7,levels[2]-18,bw-14,levels[3]-levels[2]+32,'Noncompletion\n+∞',24,True,RED)
    qx=x+45; qy=y+h-70; qw=w-88
    d.text(x+w*.43,y+h-107,w*.43,28,'Bellman backup',25,True)
    collector=bx+bw+7
    d.line([(bx+bw,(levels[0]+levels[1])/2),(collector,(levels[0]+levels[1])/2),
            (collector,qy-10),(qx+qw-19,qy-10),(qx+qw-19,qy-1)],INK,1.4,True)
    d.line([(bx+bw,(levels[2]+levels[3])/2),(collector,(levels[2]+levels[3])/2)],INK,1.4)
    d.box(qx,qy,qw,59,'#F1D8A7',GOLD,7,1.3)
    d.equation(qx+10,qy+8,qw-20,42,'q',29)
    return root,(qx+qw,qy+30)


def integrated(data):
    d=Draft('A - Integrated revision','A_integrated',1160)
    d.text(18,14,1644,44,'Viability-preserving rollout ADP for orbital inspection',35,True)
    d.panel(16,80,434,475,'a  Mission inputs',GREY)
    v1.mesh_illustration(d,data,34,145,396,322)
    d.circle(49,502,5.7,'none',GOLD,2)
    d.text(65,480,357,42,'Required targets K',28,True,align='left')
    d.panel(16,583,434,535,'b  Camera and LOS',PALE_BLUE)
    visibility(d,30,673,406,350)
    d.box(36,1046,394,53,WHITE,BORDER,8,1.1)
    d.equation(45,1055,375,34,'state',28)
    d.panel(480,80,828,390,'c  HCW transfer → SOOA graph',PALE_BLUE)
    hcw(d,data,496,149,553,282)
    # A smaller three-node excerpt leaves space for the transfer construction.
    excerpt={**data,'graph_nodes':['cand_0070','cand_0068','cand_0021'],
        'graph_edges':[e for e in data['graph_edges'] if all(n in ['cand_0070','cand_0068','cand_0021'] for n in e)]}
    v1.graph(d,excerpt,1116,201,132,152)
    d.line([(1059,279),(1088,279)],INK,2,True)
    d.text(1080,381,213,31,'ℓᵢⱼ; χᵢⱼ',25)
    d.line([(450,276),(480,276)],INK,2.1,True)
    # Visibility masks feed the graph separately from transfer-audit records.
    d.line([(347,1006),(463,1006),(463,448),(1190,448),(1190,414)],BLUE,1.5,True)
    d.panel(480,502,828,616,'d  Rollout ADP',PEACH)
    root,qout=adp(d,500,576,788,520)
    d.line([(913,470),(913,502)],INK,2,True)
    d.line([(450,1072),(476,1072),(476,root[1]),(root[0]-19,root[1])],INK,1.7,True)
    d.panel(1338,80,326,1038,'e  Replanning',YELLOW)
    d.box(1356,186,290,97,WHITE,BLUE,9,1.3)
    d.text(1366,196,270,38,'First action a*',28,True)
    d.text(1366,239,270,30,'Minimum finite Q',24)
    d.line([qout,(1324,qout[1]),(1324,234),(1356,234)],INK,1.9,True)
    d.line([(1501,283),(1501,324)],INK,2,True)
    d.box(1356,324,290,105,WHITE,BORDER,9,1.3)
    d.text(1366,334,270,34,'Append arc + update',25,True)
    d.equation(1366,375,270,37,'update',27)
    d.line([(1501,429),(1501,477)],INK,2,True)
    d.box(1375,477,250,80,WHITE,GOLD,24,1.5)
    d.text(1385,488,230,59,'Required goal\nreached?',25,True)
    d.line([(1501,557),(1501,613)],SUCCESS,2,True)
    d.text(1514,565,70,32,'Yes',23,color=SUCCESS)
    d.text(1354,621,296,34,'Planned route',28,True)
    v1.route(d,data,1348,688,302,328)
    d.text(1350,1045,301,35,'Required targets: 9/9',25,True)
    d.line([(1625,517),(1650,517),(1650,1140),(490,1140),(490,root[1]+36),
            (root[0],root[1]+36),(root[0],root[1]+19)],RED,1.7,True,True)
    d.text(1608,572,43,28,'No',23,color=RED)
    d.box(739,1127,325,28,WHITE,'none',0,0)
    d.text(744,1127,315,27,'State update and replan',23,color=RED)
    return d


def overview(data):
    d=Draft('B1 - Sensing and planning overview','B1_overview',848)
    d.text(18,14,1644,44,'Orbital inspection: sensing, audited transfers and rollout ADP',35,True)
    d.panel(16,80,324,742,'a  Mission',GREY)
    v1.mesh_illustration(d,data,32,185,292,396)
    d.circle(48,632,5.7,'none',GOLD,2)
    d.text(65,612,252,41,'Required targets K',25,True,align='left')
    d.text(34,687,286,38,'Initial state; budget H',25)
    d.panel(372,80,616,405,'b  Camera and LOS',PALE_BLUE)
    visibility(d,387,145,586,316)
    d.panel(1020,80,644,405,'c  Controlled HCW transfer',PALE_BLUE)
    hcw(d,data,1050,151,584,301)
    d.line([(340,269),(372,269)],INK,2.1,True)
    d.panel(372,531,288,291,'d  SOOA graph',PALE_BLUE)
    v1.graph(d,data,422,617,185,137)
    d.text(389,781,254,29,'Masks · cost · audits',24)
    d.line([(682,485),(682,508),(516,508),(516,531)],BLUE,1.8,True)
    d.line([(1342,485),(1342,508),(516,508)],BLUE,1.8)
    d.panel(692,531,560,291,'e  Rollout ADP',PEACH)
    adp(d,714,591,516,216,True)
    d.panel(1284,531,380,291,'f  Inspection plan',YELLOW)
    route_thumbnail(d,data,1315,589,316,178)
    d.text(1298,775,352,32,'Required targets: 9/9',25,True)
    d.line([(660,694),(692,694)],INK,2.1,True)
    d.line([(1252,694),(1284,694)],INK,2.1,True)
    d.line([(988,283),(1020,283)],INK,1.8,True)
    return d


def mechanism(data):
    d=Draft('B2 - Reference-inspired ADP mechanism','B2_adp_mechanism',940)
    d.text(18,14,1644,44,'Rollout ADP with task-aware base-policy evaluation',36,True)
    d.panel(16,80,294,740,'a  Decision state',GREY)
    d.box(31,184,264,97,WHITE,BORDER,9,1.2)
    d.equation(41,207,244,48,'state',29)
    d.text(39,307,255,162,'j   current viewpoint\nm  covered targets\nb  selected views\nh  remaining budget',24,align='left')
    d.box(32,511,262,119,WHITE,BLUE,9,1.2)
    d.text(42,522,242,33,'Audited + unvisited',24,True)
    d.equation(43,569,240,37,'safe',24)
    d.text(39,656,250,65,'Safe connecting\nactions retained',24)
    d.text(34,749,256,32,'Fixed required set K',24,True)
    d.panel(342,80,984,740,'b  Rollout ADP',PEACH)
    root,qout=adp(d,365,166,938,623)
    d.line([(310,root[1]),(root[0]-19,root[1])],INK,2,True)
    d.panel(1356,80,308,740,'c  Policy update',YELLOW)
    d.box(1373,197,274,120,WHITE,BLUE,9,1.2)
    d.text(1383,209,254,34,'Finite values only',25,True)
    d.equation(1383,260,254,43,'argmin',25)
    d.line([qout,(1342,qout[1]),(1342,254),(1373,254)],INK,1.9,True)
    d.line([(1510,317),(1510,365)],INK,2,True)
    d.box(1373,365,274,130,WHITE,BORDER,9,1.2)
    d.text(1383,377,254,57,'Append first arc\nand update',25,True)
    d.equation(1383,443,254,40,'update',28)
    d.line([(1510,495),(1510,546)],INK,2,True)
    d.box(1387,546,246,82,WHITE,GOLD,24,1.5)
    d.text(1397,556,226,59,'Required goal\nreached?',25,True)
    d.line([(1510,628),(1510,688)],SUCCESS,2,True)
    d.text(1523,642,76,28,'Yes',23,color=SUCCESS)
    d.box(1392,688,236,78,GREEN,SUCCESS,9,1.2)
    d.text(1402,705,216,40,'Complete plan',26,True)
    d.box(501,839,525,66,WHITE,RED,8,1.2)
    d.text(514,848,499,48,'All Q = +∞ → no certified completion',25,color=RED)
    d.line([(977,820),(977,837)],RED,1.6,True,True)
    d.line([(1633,587),(1650,587),(1650,921),(6,921),(6,233),(31,233)],RED,1.7,True,True)
    d.text(1595,638,48,31,'No',23,color=RED)
    d.box(1060,905,304,30,WHITE,'none',0,0)
    d.text(1068,906,288,28,'State update and replan',23,color=RED)
    return d


README = '''# OrbInspect editable figure alternatives - revision 2

The manuscript, current publication figures and first alternatives are unchanged.
Use A as a single integrated figure, or use B1 and B2 as a complementary pair.
All three pages are in `OrbInspect_figure_options.drawio`, and individual native
draw.io files and SVG/PNG previews are included. This is still for author discussion.

## What changed

- Camera/LOS: native field-of-view cross-section, boresight b(q_j), range rho,
  target p_i, outward normal n_i, incidence theta, clear ray and mesh-blocked ray.
  A valid observation requires range, FOV, incidence and unobstructed LOS to pass.
  The cone is a 2-D cross-section, not a claim of a circular physical camera FOV.
  The two target/ray examples are schematic, not a newly measured camera test.
- HCW: actual archived C70-to-C68 controlled transfer in x-z projection, with
  the full control-norm history and its 0.06 m/s² bound, source/arrival positions
  and projected control arrows. Position axes use equal
  scale; control-arrow lengths are normalized for direction visibility. The 90-s
  transfer is rest-to-rest subject to terminal tolerances. Input, full-mesh and
  terminal audits are separate checks; their pass marks come from the archived
  feasible edge. Do not infer 3-D clearance from apparent 2-D separation.
- ADP: the supplied reference's colored prefix nodes, complete task-aware greedy
  tails, finite-cost/noncompletion groups and highlighted Bellman backup are
  redrawn as editable objects. State is s=(j,m,b,h), K is fixed, and safe actions
  include connecting actions without immediate gain. No gradient backpropagation
  or newly trained DRL model is implied. Q is an action value; finite-value
  minimization is a separate policy update. If all values are infinite, no
  certified completion is returned; this is not a physical infeasibility proof.

The ADP tree is schematic, with compressed levels and illustrative completions.
The base policy runs to the required goal or the remaining budget, not for just
one more step. The loop updates the graph-planning state. No new physical/ROS
mission execution is claimed. Passive-drift auditing remains disabled in the
reported study and is not depicted as an active check.

## Sources, credits and editability

ISS geometry: NASA GLB from the repository, full hierarchy/SDF transform and
orthographic vector projection, with archived required-target positions. Subpixel
faces below 0.15 square drawing units are omitted for display only, never audits.
The planned route is the archived representative case with all 9 required targets
covered; other mesh samples are not mandatory. The five-node graph excerpt
(three nodes in the integrated option) has unique candidate IDs and only
archived passed directed arcs.

Camera: Alexander Lucke, CC BY-SA 3.0. The independently embedded original photo
is unchanged: no crop, retouching or AI editing. It is illustrative hardware,
not a selected or space-qualified camera. Source/license links are included in
`assets/IMAGE_CREDITS.md`. All ray/cone/angle annotations are separate objects.

The entire drawing is not flattened. Labels, equations, branches, arrows, targets,
plots and colored containers remain editable in draw.io. ISS and surface geometry
are native vector stencils. Equations use vector outlines in review exports to
avoid font substitution, while native draw.io equations remain editable text.
The included generators run in the original repository environment; the editable
drawings themselves are self-contained.
'''


def main():
    previous=[ROOT/'OrbInspectLatex/main.tex',ROOT/'OrbInspectLatex/main.pdf',
              ROOT/'OrbInspectLatex/figures/required_target/orbinspect_framework.drawio',
              ROOT/'OrbInspectLatex/figures/required_target/orbinspect_framework.pdf',
              ROOT/'output/pdf/OrbInspect_figure_options_20260907.pdf']
    previous += sorted((ROOT/'output/figure_options_20260907').glob('*.drawio'))
    preserved={str(p.relative_to(ROOT)):v1.digest(p) for p in previous}
    data=v1.load_evidence()
    graph=json.loads((v1.STUDY/'raw/hcw_graph.json').read_text())
    source=graph['node_positions'][graph['node_ids'].index('cand_0070')]
    with (v1.STUDY/'raw/representative_case_trajectory.csv').open() as stream:
        rows=[r for r in csv.DictReader(stream) if r['method']=='adaptive_rollout_adp' and r['action']=='4']
    edge=next(e for e in graph['edges'] if e['source_id']=='cand_0070' and e['target_id']=='cand_0068')
    data['hcw_transfer']={'source_id':'cand_0070','target_id':'cand_0068','duration_s':90,
        'positions_xyz':[source]+[[float(r['r'+a]) for a in 'xyz'] for r in rows],
        'controls_xyz':[[float(r['u'+a]) for a in 'xyz'] for r in rows],
        'audit_record':edge,'control_arrows':'Directions from archived controls, length normalized for display.'}
    assert edge['feasible'] and len(rows)==30
    assert np.linalg.norm(np.array(data['hcw_transfer']['positions_xyz'][-1])-
        graph['node_positions'][graph['node_ids'].index('cand_0068')]) < .5
    v1.OUT,v1.PDF=OUT,PDF
    v1.integrated,v1.overview,v1.mechanism=integrated,overview,mechanism
    v1.load_evidence=lambda:data
    v1.README=README
    v1.main()
    shutil.copy2(Path(__file__),OUT/'source'/Path(__file__).name)
    report=json.loads((OUT/'QA.json').read_text())
    report['preserved_sha256']=preserved
    report['manuscript_and_previous_options_unchanged']=all(v1.digest(ROOT/p)==s for p,s in preserved.items())
    assert report['manuscript_and_previous_options_unchanged']
    report['new_checks']={'los':'Schematic FOV/range/incidence/occlusion geometry',
        'hcw':data['hcw_transfer']['audit_record'],
        'adp':'Reference-inspired native prefix, complete tails, finite/infinite costs and Bellman backup.'}
    (OUT/'QA.json').write_text(json.dumps(report,indent=2)+'\n')
    pack()


def pack():
    with zipfile.ZipFile(OUT.with_suffix('.zip'),'w',compression=zipfile.ZIP_DEFLATED) as bundle:
        for p in sorted(OUT.rglob('*')):
            if p.is_file():bundle.write(p,p.relative_to(OUT.parent))
        bundle.write(PDF,OUT.name+'/'+PDF.name)


if __name__=='__main__':
    main()
