"""Historical-style conditional sections and the actual fault path from the pre-fault state.

Colored triangles summarize only their vertices. The physical path is a projection,
and its hidden states generally differ from the background's initial-state section.
"""
from pathlib import Path
import json,tomllib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from postprocess import ROOT,RESULTS,verify,case_info,study,main_cases,section_settings,native_coordinates,base_frequency,control_label,save_figure,write_check,option,safe_output
REMOTE=study()["network"]["remote_buses"]
COLORS={'recovery':'#9ecae1','negative_running':'#fdae6b','positive_running':'#bc80bd','unresolved':'#d9d9d9','numerical_failure':'#555555'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})

save=save_figure

def coordinates(d):
    return d[[f'b{b}_delta_rad' for b in REMOTE]].mean(axis=1),d[[f'b{b}_df_Hz' for b in REMOTE]].mean(axis=1)

def load_case(case,settings):
    folder=verify(option('--section-results',RESULTS/'fault_basins')/case)
    points=[tomllib.loads(p.read_text()) for p in sorted((folder/'points').glob('*.toml'))]
    table=pd.read_csv(folder/'classification.csv')
    triangles=pd.read_csv(folder/'triangles.csv').to_numpy(dtype=int)
    d=pd.read_csv(folder/'physical_fault_projection.csv')
    roots=pd.read_csv(folder/'roots.csv') if (folder/'roots.csv').exists() else pd.read_csv(verify(RESULTS/'basins'/case)/'roots.csv')
    return folder,points,table,triangles,d,roots

def background(ax,table,triangles):
    xy=table[['theta_actual','df_actual']].to_numpy();labels=table.classification.to_numpy()
    same=[];colors=[];mixed=[]
    for face in triangles:
        categories=set(labels[face])
        if len(categories)==1 and next(iter(categories)) in ['recovery','negative_running','positive_running']:
            same.append(xy[face]);colors.append(COLORS[next(iter(categories))])
        else:mixed.append(xy[face])
    if same:ax.add_collection(PolyCollection(same,facecolors=colors,edgecolors='none',alpha=.65,zorder=0))
    if mixed:ax.add_collection(PolyCollection(mixed,facecolors='#eee',edgecolors='#aaa',linewidths=.3,hatch='////',alpha=.6,zorder=1))
    ax.scatter(*xy.T,s=15,c=[COLORS[v] for v in labels],edgecolors='#555',linewidths=.35,zorder=3)

def fault_path(ax,d,roots,settings,wide):
    for stage,color in [('pre','#2166ac'),('fault','#762a83'),('post','#202020')]:
        g=d[d.stage==stage]
        ax.plot(g.theta_rad,g.df_Hz,color=color,lw=1.15,zorder=5)
        times=g.t_absolute_s.to_numpy() if stage=='fault' else g.t_post_s.to_numpy()
        for at in ([float(d[d.stage=='fault'].t_absolute_s.iloc[0])+v for v in study()['figures']['fault_arrow_offsets_s']] if stage=='fault' else study()['figures']['post_arrow_times_s'] if stage=='post' else []):
            i=np.searchsorted(times,at);j=i+(8 if stage=='fault' else 3)
            if j>=len(g):continue
            a,b=g.iloc[i],g.iloc[j];xlim=settings['wide_xlim_rad'] if wide else settings['plot_xlim_rad'];ylim=settings['plot_ylim_Hz']
            if all(xlim[0]<r.theta_rad<xlim[1] and ylim[0]<r.df_Hz<ylim[1] for r in [a,b]):
                ax.annotate('',xy=(b.theta_rad,b.df_Hz),xytext=(a.theta_rad,a.df_Hz),arrowprops=dict(arrowstyle='-|>',color=color,lw=.8,mutation_scale=8),zorder=6)
    a=d.iloc[0];b=d[d.stage=='post'].iloc[0]
    ax.scatter(a.theta_rad,a.df_Hz,marker='^',s=58,c='#2166ac',edgecolors='white',zorder=9)
    ax.scatter(b.theta_rad,b.df_Hz,marker='o',s=42,facecolors='white',edgecolors='#111',zorder=8)
    for r in roots.itertuples():
        if r.kind=='stable':ax.scatter(r.remote_angle_rad,r.remote_df_Hz,marker='*',s=125,c='#ffe259',edgecolors='#111',zorder=8)
        elif r.kind=='saddle':ax.scatter(r.remote_angle_rad,r.remote_df_Hz,marker='X',s=45,c='#333',edgecolors='white',linewidths=.4,zorder=7)

def plot_all():
    settings=section_settings()
    legend=[Patch(facecolor=COLORS['recovery'],alpha=.65,label='Recovery at all triangle vertices'),Patch(facecolor=COLORS['negative_running'],alpha=.65,label='Negative running at all vertices'),Patch(facecolor='#eee',edgecolor='#aaa',hatch='////',label='Mixed / unresolved vertex outcomes'),Line2D([],[],color='#762a83',label='Fault-on trajectory'),Line2D([],[],color='#202020',label='Post-fault trajectory (first 30 s)'),Line2D([],[],marker='^',ls='',color='#2166ac',label='Pre-fault operating point'),Line2D([],[],marker='o',ls='',mfc='white',mec='black',label='Clearing point'),Line2D([],[],marker='*',ls='',mfc='#ffe259',mec='black',ms=11,label='Post-fault stable equilibrium'),Line2D([],[],marker='X',ls='',color='#333',label='Full-state saddle (projection)')]
    checks=[]
    for case in main_cases():
        folder,points,table,triangles,d,roots=load_case(case,settings)
        for wide in [False,True]:
            fig,ax=plt.subplots(figsize=(5.8,5.4))
            background(ax,table,triangles);fault_path(ax,d,roots,settings,wide)
            running='negative_running' in pd.read_csv(RESULTS/case/'machines.csv').classification.values
            row,cfg=case_info(case)
            title=case+': '+control_label(case,math=True)+(r', $D_1='+f"{float(row['D1']):g}"+'$' if row['control']=='VSM' else '')+(' — negative rotation' if running else ' — fault response recovers')
            ax.set_title(title+'\n'+f"{len(points)} classified states; "+rf"$m_p={100*float(row['mp']):g}\%$, $B_5={cfg['B']:g}$ pu",fontsize=10)
            ax.set(xlim=settings['wide_xlim_rad'] if wide else settings['plot_xlim_rad'],ylim=settings['plot_ylim_Hz'],xlabel=r'Mean internal angle relative to slack Bus6 [rad]',ylabel=r'Mean internal frequency deviation from 60 Hz [Hz]')
            ax.grid(alpha=.18)
            if running and not wide:ax.text(.02,.035,'Negative-rotation trajectory continues left',transform=ax.transAxes,fontsize=8,bbox=dict(facecolor='white',alpha=.85,edgecolor='none'))
            fig.legend(handles=legend,loc='lower center',ncol=2,fontsize=7,frameon=False,bbox_to_anchor=(.51,.01))
            fig.text(.51,.235,'Background: post-fault initial-state section; real fault path: projection.',ha='center',fontsize=7)
            fig.subplots_adjust(left=.14,right=.97,top=.84,bottom=.33)
            save(fig,ROOT/('figures/details' if wide else 'figures/paper')/(f'basin_{case}_wide' if wide else f'basin_{case}'))
        checks.append(dict(case=case,counts=table.classification.value_counts().to_dict(),max_coordinate_error=max(max(abs(p['theta_requested']-p['theta_actual']),abs(p['df_requested']-p['df_actual'])) for p in points),max_frozen_state_error=max(p['max_frozen_state_error'] for p in points),max_initial_algebraic_residual=max(p['initial_algebraic_residual'] for p in points)))

    print(json.dumps(checks,indent=2))

if __name__=='__main__':plot_all()
