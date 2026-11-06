"""Compare saved profiles and source references; no re-integration is performed here."""
from pathlib import Path
import json,tomllib
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];BUS=[1,2,3,7]
OUT=ROOT/'results/validation';OUT.mkdir(parents=True,exist_ok=True)
def load(path,old=False):
 d=pd.read_csv(path);d['stage']=d.stage.str.replace(r'^post.*','post',regex=True)
 d['time_key']=d.t_absolute_s.round(9)
 d=d.drop_duplicates(['stage','time_key'],keep='last').set_index(['stage','time_key'])
 if old:
  for b in BUS:
   for new,r,i in [('U_pu','U_r_pu','U_i_pu'),('Ig_pu','Ig_r_pu','Ig_i_pu'),('If_pu','If_r_pu','If_i_pu'),('Vc_pu','Vc_r_pu','Vc_i_pu')]:
    if f'b{b}_{r}' in d:d[f'b{b}_{new}']=np.hypot(d[f'b{b}_{r}'],d[f'b{b}_{i}'])
 return d
records=[]
def compare(label,a,b,columns,limit=1e-5):
 common=a.index.intersection(b.index);assert len(common)>50000,(label,len(common))
 for col in columns:
  err=np.abs(a.loc[common,col].to_numpy()-b.loc[common,col].to_numpy());peak=float(np.nanmax(err))
  records.append(dict(comparison=label,observable=col,matched_samples=len(common),max_abs_error=peak,limit=limit,passed=bool(peak<limit)))
  assert peak<limit,(label,col,peak)
for case in ['A','B','C']:
 a=load(ROOT/'results'/case/'observations.csv.gz');b=load(ROOT/'results'/(case+'_strict')/'observations.csv.gz')
 columns=[f'b{bus}_{key}' for bus in BUS for key in ['delta_rad','df_Hz','U_pu','Ig_pu','Pcap_pu','Qcap_pu','ref_out_d_pu','ref_out_q_pu']]
 compare(case+'_accuracy',a,b,columns)
 ma=pd.read_csv(ROOT/'results'/case/'machines.csv');mb=pd.read_csv(ROOT/'results'/(case+'_strict')/'machines.csv')
 assert ma.classification.equals(mb.classification)
for case in ['C','C_D1_10']:
 a=load(ROOT/'results'/case/'observations.csv.gz').copy();b=load(ROOT/'provenance/reference_results'/(case+'_response.csv.gz'))
 for name,keys in [('remote_Pcap_pu','Pcap_pu'),('remote_Qterminal_pu','Qterminal_pu'),('remote_mean_Ig_pu','Ig_pu')]:a[name]=a[[f'b{bus}_{keys}' for bus in [2,3,7]]].mean(axis=1) if name=='remote_mean_Ig_pu' else a[[f'b{bus}_{keys}' for bus in [2,3,7]]].sum(axis=1)
 columns=[f'b{bus}_{key}' for bus in BUS for key in ['delta_rad','df_Hz']]+['remote_Pcap_pu','remote_Qterminal_pu','remote_mean_Ig_pu']
 compare(case+'_source_reproduction',a,b,columns)
for name in ['A','B']:
 a=load(ROOT/'results'/('original_'+name)/'observations.csv.gz');b=load(ROOT/'provenance/reference_results'/('droop_original_'+name+'_observations.csv.gz'),old=True)
 columns=[f'b{bus}_{key}' for bus in BUS for key in ['delta_rad','df_Hz','U_pu','Vc_pu','Ig_pu','If_pu','Pcap_pu','Qcap_pu','Pterminal_pu','Qterminal_pu','ref_in_d_pu','ref_in_q_pu','ref_out_d_pu','ref_out_q_pu']]
 compare('original_droop_'+name+'_migration',a,b,columns)
pd.DataFrame(records).to_csv(OUT/'waveform_comparisons.csv',index=False)
summary={'all_passed':all(r['passed'] for r in records),'comparison_count':len(records),'max_absolute_error':max(r['max_abs_error'] for r in records),'groups':{group:max(r['max_abs_error'] for r in records if r['comparison']==group) for group in sorted({r['comparison'] for r in records})}}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))

# Command limits constrain references, not instantaneous physical currents.
limits=[]
for case in ['A','B','C','C_D1_10']:
 d=pd.read_csv(ROOT/'results'/case/'observations.csv.gz')
 maxref=max(np.hypot(d[f'b{bus}_ref_out_d_pu'],d[f'b{bus}_ref_out_q_pu']).max() for bus in BUS)
 assert maxref<=1.2+1e-12
 limits.append(dict(case=case,max_limited_command_pu=maxref,max_actual_If_pu=max(d[f'b{bus}_If_pu'].max() for bus in BUS),max_actual_Ig_pu=max(d[f'b{bus}_Ig_pu'].max() for bus in BUS),command_limit_check_passed=True))
pd.DataFrame(limits).to_csv(OUT/'current_limit_checks.csv',index=False)
