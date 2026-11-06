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

ROOT=Path(__file__).resolve().parents[1]
REMOTE=[2,3,7]
COLORS={'recovery':'#9ecae1','negative_running':'#fdae6b','positive_running':'#bc80bd','unresolved':'#d9d9d9','numerical_failure':'#555555'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})

def save(fig,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    for ext in ['pdf','png']:
        fig.savefig(path.with_suffix('.'+ext),dpi=240,bbox_inches='tight',facecolor='white')
    plt.close(fig)

def coordinates(d):
    return d[[f'b{b}_delta_rad' for b in REMOTE]].mean(axis=1),d[[f'b{b}_df_Hz' for b in REMOTE]].mean(axis=1)

def export_case(case,settings):
    folder=ROOT/'results/fault_basins'/case
    points=[tomllib.loads(p.read_text()) for p in sorted((folder/'points').glob('*.toml'))]
    expected=len(settings['angle_rad'])*len(settings['frequency_Hz'])+len(settings['local_angle_rad'])*len(settings['local_frequency_Hz'])
    if len(points)!=expected:raise RuntimeError(f'{case}: {len(points)}/{expected} points')
    excluded=['initial_native','final_native','initial_bus_voltage_ri','final_bus_voltage_ri','machine_metrics']
    table=pd.DataFrame([{k:v for k,v in p.items() if k not in excluded} for p in points])
    table.to_csv(folder/'classification.csv',index=False)
    machines=[]
    for p in points:
        for m in p['machine_metrics']:machines.append([p['point'],*m])
    pd.DataFrame(machines,columns=['point','bus','classification','turns','tail_mean_df_Hz','tail_max_abs_df_Hz','phase_error_rad','phase_width_rad','min_window_turns','max_window_turns']).to_csv(folder/'machines.csv',index=False)
    xy=table[['theta_actual','df_actual']].to_numpy()
    triangles=mtri.Triangulation(*xy.T).triangles
    pd.DataFrame(triangles,columns=['vertex_0','vertex_1','vertex_2']).to_csv(folder/'triangles.csv',index=False)
    d=pd.read_csv(ROOT/'results'/case/'observations.csv.gz',usecols=['t_absolute_s','t_post_s','stage',*[f'b{b}_{key}' for b in [1,2,3,7] for key in ['delta_rad','df_Hz']]])
    d=d[d.t_post_s<=settings['fault_trajectory_post_horizon_s']].copy()
    d['theta_rad'],d['df_Hz']=coordinates(d)
    d.to_csv(folder/'physical_fault_projection.csv',index=False)
    roots=pd.read_csv(ROOT/'results/basins'/case/'roots.csv')
    anchors=[]
    for name,row in [('prefault',d.iloc[0]),('fault_application',d[d.stage=='fault'].iloc[0]),('clearing',d[d.stage=='post'].iloc[0])]:
        anchors.append(dict(anchor=name,theta_rad=row.theta_rad,df_Hz=row.df_Hz,t_absolute_s=row.t_absolute_s,t_post_s=row.t_post_s))
    for r in roots.itertuples():
        if r.kind in ['stable','saddle']:anchors.append(dict(anchor='post_'+r.kind,theta_rad=r.remote_angle_rad,df_Hz=r.remote_df_Hz))
    pd.DataFrame(anchors).to_csv(folder/'anchors.csv',index=False)
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
        for at in ([1.04,1.10] if stage=='fault' else [.1,.5,1.,2.,4.,12.,24.] if stage=='post' else []):
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
    settings=tomllib.loads((ROOT/'inputs/fault_basin.toml').read_text())
    legend=[Patch(facecolor=COLORS['recovery'],alpha=.65,label='Recovery at all triangle vertices'),Patch(facecolor=COLORS['negative_running'],alpha=.65,label='Negative running at all vertices'),Patch(facecolor='#eee',edgecolor='#aaa',hatch='////',label='Mixed / unresolved vertex outcomes'),Line2D([],[],color='#762a83',label='Fault-on trajectory'),Line2D([],[],color='#202020',label='Post-fault trajectory (first 30 s)'),Line2D([],[],marker='^',ls='',color='#2166ac',label='Pre-fault operating point'),Line2D([],[],marker='o',ls='',mfc='white',mec='black',label='Clearing point'),Line2D([],[],marker='*',ls='',mfc='#ffe259',mec='black',ms=11,label='Post-fault stable equilibrium'),Line2D([],[],marker='X',ls='',color='#333',label='Full-state saddle (projection)')]
    checks=[]
    for case in ['A','B','C']:
        folder,points,table,triangles,d,roots=export_case(case,settings)
        for wide in [False,True]:
            fig,ax=plt.subplots(figsize=(5.8,5.4))
            background(ax,table,triangles);fault_path(ax,d,roots,settings,wide)
            title={'A':r'A: Droop, $\tau_p=0.02$ s — fault response recovers','B':r'B: Droop, $\tau_p=1.00$ s — negative rotation','C':r'C: VSM, $H=2.5$ s, $D_1=0$ — negative rotation'}[case]
            ax.set_title(title+'\n'+f'43 freshly classified states; '+r'$m_p=5\%$, $B_5=1$ pu',fontsize=10)
            ax.set(xlim=settings['wide_xlim_rad'] if wide else settings['plot_xlim_rad'],ylim=settings['plot_ylim_Hz'],xlabel=r'Mean internal angle relative to slack Bus6 [rad]',ylabel=r'Mean internal frequency deviation from 60 Hz [Hz]')
            ax.grid(alpha=.18)
            if case!='A' and not wide:ax.text(.02,.035,'Negative-rotation trajectory continues left',transform=ax.transAxes,fontsize=8,bbox=dict(facecolor='white',alpha=.85,edgecolor='none'))
            fig.legend(handles=legend,loc='lower center',ncol=2,fontsize=7,frameon=False,bbox_to_anchor=(.51,.01))
            fig.text(.51,.235,'Background: post-fault initial-state section; real fault path: projection.',ha='center',fontsize=7)
            fig.subplots_adjust(left=.14,right=.97,top=.84,bottom=.33)
            save(fig,ROOT/('figures/details' if wide else 'figures/paper')/(f'basin_{case}_wide' if wide else f'basin_{case}'))
        checks.append(dict(case=case,counts=table.classification.value_counts().to_dict(),max_coordinate_error=max(max(abs(p['theta_requested']-p['theta_actual']),abs(p['df_requested']-p['df_actual'])) for p in points),max_frozen_state_error=max(p['max_frozen_state_error'] for p in points),max_initial_algebraic_residual=max(p['initial_algebraic_residual'] for p in points)))
    (ROOT/'results/validation/fault_basin_plot_checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(json.dumps(checks,indent=2))

if __name__=='__main__':plot_all()
