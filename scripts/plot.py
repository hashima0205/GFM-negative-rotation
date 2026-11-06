"""Plot saved, unwrapped individual-machine observations without temporal smoothing."""
from pathlib import Path
import argparse,tomllib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, FormatStrFormatter
ROOT=Path(__file__).resolve().parents[1]
BUS=[1,2,3,7];COLORS=['#202020','#0072B2','#D55E00','#009E73'];STYLES=['-','--',':','-.']
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
def save(fig,path):
 path.parent.mkdir(parents=True,exist_ok=True)
 for ext in ['png','pdf']:fig.savefig(path.with_suffix('.'+ext),dpi=240,bbox_inches='tight',facecolor='white')
 plt.close(fig)
def obs(case):return pd.read_csv(ROOT/'results'/case/'observations.csv.gz')
def main_time():
 data={c:obs(c) for c in ['A','B','C']}
 for long in [False,True]:
  fig,axes=plt.subplots(1,3,figsize=(7.2,2.6),sharex=True,sharey=True)
  limits=(-.2,1000 if long else 8)
  for ax,(case,d) in zip(axes,data.items()):
   v=d[(d.t_post_s>=limits[0])&(d.t_post_s<=limits[1])]
   for b,color,style in zip(BUS,COLORS,STYLES):
    ax.plot(v.t_post_s,v[f'b{b}_delta_rad']-d[f'b{b}_delta_rad'].iloc[0],color=color,ls=style,lw=1.25,label=f'Bus {b}')
   for t in [-.15,0]:ax.axvline(t,color='.65',ls=':',lw=.7)
   ax.set_title({'A':'(a) Droop, '+r'$\tau_p=0.02$ s','B':'(b) Droop, '+r'$\tau_p=1.00$ s','C':'(c) VSM, $H=2.5$ s'}[case],fontsize=9)
   ax.set_xlabel('Time from clearing [s]');ax.set_xlim(limits);ax.grid(alpha=.18)
   ax.text(.04,.06,'Recovery' if case=='A' else 'Negative rotation',transform=ax.transAxes,fontsize=8)
  axes[0].set_ylabel(r'$\delta_i(t)-\delta_i^{\mathrm{pre}}$ [rad]')
  fig.legend(*axes[0].get_legend_handles_labels(),loc='upper center',ncol=4,bbox_to_anchor=(.5,1.06),frameon=False)
  fig.subplots_adjust(wspace=.12,bottom=.22,top=.82)
  save(fig,ROOT/('figures/details/time_response_ABC_long' if long else 'figures/paper/time_response_ABC'))
 for case in ['A','B','C','C_D1_10']:
  d=obs(case);v=d[(d.t_post_s>=-.2)&(d.t_post_s<=12)]
  fig,axes=plt.subplots(4,2,figsize=(8.2,9),sharex=True)
  fields=[('delta_rad','Internal angle change [rad]'),('df_Hz','Internal frequency deviation [Hz]'),('U_pu','Terminal voltage [pu]'),('Ig_pu','Grid-side current [pu]'),('Pcap_pu','Measured active power [pu]'),('Qcap_pu','Measured reactive power [pu]'),('If_pu','Inverter-side current [pu]'),('limit_factor','Current-command scale factor')]
  for ax,(key,label) in zip(axes.flat,fields):
   for b,color,style in zip(BUS,COLORS,STYLES):
    value=v[f'b{b}_{key}']-(d[f'b{b}_{key}'].iloc[0] if key=='delta_rad' else 0)
    ax.plot(v.t_post_s,value,color=color,ls=style,lw=1,label=f'Bus {b}')
   ax.set_ylabel(label);ax.grid(alpha=.18);ax.axvline(0,color='.5',lw=.7,ls=':')
  for ax in axes[-1]:ax.set_xlabel('Time from clearing [s]')
  fig.legend(*axes[0,0].get_legend_handles_labels(),loc='upper center',ncol=4,frameon=False)
  fig.suptitle(case+' — individual-machine responses',y=1.02);fig.tight_layout(rect=[0,0,1,.97]);save(fig,ROOT/'figures/details'/f'{case}_responses')
 fig,axes=plt.subplots(2,1,figsize=(6.9,4.2),sharex=True)
 for case,basecolor in [('C','#B2182B'),('C_D1_10','#2166AC')]:
  d=obs(case);v=d[(d.t_post_s>=-.2)&(d.t_post_s<=10)]
  for b,style in zip(BUS,STYLES):
   axes[0].plot(v.t_post_s,v[f'b{b}_delta_rad']-d[f'b{b}_delta_rad'].iloc[0],color=basecolor,ls=style,lw=1,label=case+f', Bus {b}')
   axes[1].plot(v.t_post_s,v[f'b{b}_df_Hz'],color=basecolor,ls=style,lw=1)
 axes[0].set_ylabel('Internal angle change [rad]');axes[1].set_ylabel('Frequency deviation [Hz]');axes[1].set_xlabel('Time from clearing [s]')
 for ax in axes:ax.grid(alpha=.2);ax.axvline(0,color='.5',ls=':',lw=.7)
 fig.legend(*axes[0].get_legend_handles_labels(),loc='upper center',ncol=4,fontsize=7,frameon=False,bbox_to_anchor=(.5,1.04));fig.tight_layout(rect=[0,0,1,.9]);save(fig,ROOT/'figures/details/C_D1_comparison')
def local_basins():
 palette={'recovery':'#56B4E9','negative_running':'#D55E00','positive_running':'#CC79A7','unresolved':'#BBBBBB','numerical_failure':'#333333'}
 for case in ['A','B','C']:
  folder=ROOT/'results/basins'/case;files=sorted((folder/'points').glob('*.toml'))
  if len(files)!=49:raise RuntimeError(f'{case}: expected 49 classified points, found {len(files)}')
  points=[tomllib.loads(p.read_text()) for p in files];roots=pd.read_csv(folder/'roots.csv')
  fig,ax=plt.subplots(figsize=(3.5,2.8))
  for label,color in palette.items():
   pts=[p for p in points if p['classification']==label]
   if pts:ax.scatter([p['theta_actual'] for p in pts],[p['df_actual'] for p in pts],s=22,c=color,label=label.replace('_',' '),edgecolors='none',zorder=4)
  for r in roots.itertuples():
   if r.kind in ['stable','saddle']:
    ax.scatter(r.remote_angle_rad,r.remote_df_Hz,c='black',s=54,marker='*' if r.kind=='stable' else 'X',label='stable equilibrium' if r.kind=='stable' else 'saddle projection',zorder=6)
  # Representative trajectories start on the defined section. They may leave that section afterwards.
  for label,color in [('recovery','#005C84'),('negative_running','#9D2400')]:
   candidates=[p for p in points if p['classification']==label and (folder/'points'/f"{p['point']:03d}_trajectory.csv.gz").exists()]
   if candidates:
    candidates=[p for p in candidates if abs(p['theta_actual']-roots.remote_angle_rad.iloc[0])+abs(p['df_actual'])>1e-6] or candidates
    p=min(candidates,key=lambda p:abs(p['theta_actual']-roots.remote_angle_rad.iloc[0])+abs(p['df_actual']))
    d=pd.read_csv(folder/'points'/f"{p['point']:03d}_trajectory.csv.gz")
    theta=d[['x26','x39','x52']].mean(axis=1)
    df=d[['x25','x38','x51']].mean(axis=1)*60 if case=='C' else np.mean([60*.05*(.4-d[f'x{i}']) for i in [25,38,51]],axis=0)
    ax.plot(theta,df,color=color,lw=.9,alpha=.9,label=label.replace('_',' ')+' trajectory (projection)',zorder=3)
  ax.set(xlabel='Mean internal angle to Bus6 [rad]',ylabel='Mean internal frequency deviation [Hz]',xlim=(roots.remote_angle_rad.iloc[0]-.087,roots.remote_angle_rad.iloc[0]+.087),ylim=(-.045,.045))
  ax.xaxis.set_major_locator(MaxNLocator(4));ax.xaxis.set_major_formatter(FormatStrFormatter('%.2f'))
  ax.set_title(case+' — conditional classification at 1000 s',fontsize=9);ax.grid(alpha=.15)
  ax.legend(loc='upper left',bbox_to_anchor=(1.02,1),fontsize=6,frameon=False)
  save(fig,ROOT/'figures/details'/f'basin_local_{case}')
  pd.DataFrame([{k:v for k,v in p.items() if k not in ['initial_native','final_native','initial_bus_voltage_ri','final_bus_voltage_ri','machine_metrics']} for p in points]).to_csv(folder/'classification.csv',index=False)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--only',choices=['time','basins','local-basins','all'],default='all');a=parser.parse_args()
 if a.only in ['time','all']:main_time()
 if a.only in ['local-basins','all']:local_basins()
 if a.only in ['basins','all']:
  from plot_fault_basins import plot_all
  plot_all()
