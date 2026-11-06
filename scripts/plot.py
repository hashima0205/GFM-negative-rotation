"""Plot saved, unwrapped individual-machine observations without temporal smoothing."""
from pathlib import Path
import argparse,tomllib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, FormatStrFormatter
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from postprocess import ROOT,RESULTS,verify,case_info,study,main_cases,section_settings,native_coordinates,base_frequency,control_label,save_figure,write_check,option,safe_output
BUS=study()["network"]["gfm_buses"];COLORS=study()["figures"]["machine_colors"];STYLES=study()["figures"]["machine_styles"]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
save=save_figure
def obs(case):return pd.read_csv(verify(RESULTS/case)/'observations.csv.gz')
def main_time():
 data={c:obs(c) for c in main_cases()}
 for long in [False,True]:
  fig,axes=plt.subplots(1,3,figsize=(7.2,2.6),sharex=True,sharey=True)
  limits=(study()['figures']['short_time_s'][0],float(case_info(main_cases()[0])[0]['horizon']) if long else study()['figures']['short_time_s'][1])
  for ax,(case,d) in zip(axes,data.items()):
   v=d[(d.t_post_s>=limits[0])&(d.t_post_s<=limits[1])]
   for b,color,style in zip(BUS,COLORS,STYLES):
    ax.plot(v.t_post_s,v[f'b{b}_delta_rad']-d[f'b{b}_delta_rad'].iloc[0],color=color,ls=style,lw=1.25,label=f'Bus {b}')
   for t in [case_info(case)[1]['fault_on']-case_info(case)[1]['clearing'],0]:ax.axvline(t,color='.65',ls=':',lw=.7)
   ax.set_title('('+chr(97+main_cases().index(case))+') '+control_label(case,math=True),fontsize=9)
   ax.set_xlabel('Time from clearing [s]');ax.set_xlim(limits);ax.grid(alpha=.18)
   ax.text(.04,.06,'Negative rotation' if 'negative_running' in pd.read_csv(RESULTS/case/'machines.csv').classification.values else 'Recovery',transform=ax.transAxes,fontsize=8)
  axes[0].set_ylabel(r'$\delta_i(t)-\delta_i^{\mathrm{pre}}$ [rad]')
  fig.legend(*axes[0].get_legend_handles_labels(),loc='upper center',ncol=4,bbox_to_anchor=(.5,1.06),frameon=False)
  fig.subplots_adjust(wspace=.12,bottom=.22,top=.82)
  save(fig,ROOT/('figures/details/time_response_ABC_long' if long else 'figures/paper/time_response_ABC'))
 for case in main_cases()+study()['cases']['additional']:
  d=obs(case);v=d[(d.t_post_s>=study()['figures']['detail_time_s'][0])&(d.t_post_s<=study()['figures']['detail_time_s'][1])]
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
 for case,basecolor in zip(study()['cases']['damping_comparison'],['#B2182B','#2166AC']):
  d=obs(case);v=d[(d.t_post_s>=study()['figures']['damping_time_s'][0])&(d.t_post_s<=study()['figures']['damping_time_s'][1])]
  for b,style in zip(BUS,STYLES):
   axes[0].plot(v.t_post_s,v[f'b{b}_delta_rad']-d[f'b{b}_delta_rad'].iloc[0],color=basecolor,ls=style,lw=1,label=case+f', Bus {b}')
   axes[1].plot(v.t_post_s,v[f'b{b}_df_Hz'],color=basecolor,ls=style,lw=1)
 axes[0].set_ylabel('Internal angle change [rad]');axes[1].set_ylabel('Frequency deviation [Hz]');axes[1].set_xlabel('Time from clearing [s]')
 for ax in axes:ax.grid(alpha=.2);ax.axvline(0,color='.5',ls=':',lw=.7)
 fig.legend(*axes[0].get_legend_handles_labels(),loc='upper center',ncol=4,fontsize=7,frameon=False,bbox_to_anchor=(.5,1.04));fig.tight_layout(rect=[0,0,1,.9]);save(fig,ROOT/'figures/details/C_D1_comparison')
def local_basins():
 palette={'recovery':'#56B4E9','negative_running':'#D55E00','positive_running':'#CC79A7','unresolved':'#BBBBBB','numerical_failure':'#333333'}
 for case in main_cases():
  folder=verify(option('--local-results',RESULTS/'basins')/case);files=sorted((folder/'points').glob('*.toml'))
  if len(files)!=section_settings(True)['angle_count']*len(section_settings(True)['frequency_Hz']):raise RuntimeError(f'{case}: expected 49 classified points, found {len(files)}')
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
    theta,df=native_coordinates(d,case)
    ax.plot(theta,df,color=color,lw=.9,alpha=.9,label=label.replace('_',' ')+' trajectory (projection)',zorder=3)
  ax.set(xlabel='Mean internal angle to Bus6 [rad]',ylabel='Mean internal frequency deviation [Hz]',xlim=tuple(roots.remote_angle_rad.iloc[0]+v for v in section_settings(True)['plot_angle_offset_rad']),ylim=section_settings(True)['plot_frequency_Hz'])
  ax.xaxis.set_major_locator(MaxNLocator(4));ax.xaxis.set_major_formatter(FormatStrFormatter('%.2f'))
  ax.set_title(case+' — conditional classification at 1000 s',fontsize=9);ax.grid(alpha=.15)
  ax.legend(loc='upper left',bbox_to_anchor=(1.02,1),fontsize=6,frameon=False)
  save(fig,ROOT/'figures/details'/f'basin_local_{case}')

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--only',choices=['time','basins','local-basins','all'],default='all');parser.add_argument('--output');parser.add_argument('--results');parser.add_argument('--section-results');parser.add_argument('--local-results');a=parser.parse_args()
 if a.only in ['time','all']:main_time()
 if a.only in ['local-basins','all']:local_basins()
 if a.only in ['basins','all']:
  from plot_fault_basins import plot_all
  plot_all()
