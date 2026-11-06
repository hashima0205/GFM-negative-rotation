"""Retain audited validation channels without altering the saved time grid."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];BUS=[1,2,3,7]
STRICT=['delta_rad','df_Hz','U_pu','Ig_pu','Pcap_pu','Qcap_pu','ref_out_d_pu','ref_out_q_pu']
ORIGINAL=['delta_rad','df_Hz','U_pu','Vc_pu','Ig_pu','If_pu','Pcap_pu','Qcap_pu','Pterminal_pu','Qterminal_pu','ref_in_d_pu','ref_in_q_pu','ref_out_d_pu','ref_out_q_pu']
def compact(path,fields,source=False):
 d=pd.read_csv(path)
 if source:
  for b in BUS:
   for key,r,i in [('U_pu','U_r_pu','U_i_pu'),('Ig_pu','Ig_r_pu','Ig_i_pu'),('If_pu','If_r_pu','If_i_pu'),('Vc_pu','Vc_r_pu','Vc_i_pu')]:
    if f'b{b}_{r}' in d:d[f'b{b}_{key}']=np.hypot(d[f'b{b}_{r}'],d[f'b{b}_{i}'])
 cols=['t_absolute_s','t_post_s','stage']+[f'b{b}_{key}' for b in BUS for key in fields]
 d=d[cols];d.to_csv(path,index=False,compression='gzip');return len(d),cols
if __name__=='__main__':
 record={}
 for case in ['A','B','C']:
  folder=ROOT/'results'/(case+'_strict');record[case+'_strict']=compact(folder/'observations.csv.gz',STRICT)
  (folder/'states.csv.gz').unlink(missing_ok=True)
 for name in ['A','B']:
  folder=ROOT/'results'/('original_'+name);record['original_'+name]=compact(folder/'observations.csv.gz',ORIGINAL)
  (folder/'states.csv.gz').unlink(missing_ok=True)
  record['source_original_'+name]=compact(ROOT/'provenance/reference_results'/('droop_original_'+name+'_observations.csv.gz'),ORIGINAL,True)
 p=ROOT/'results/validation/channel_selection.json';p.write_text(json.dumps({'operation':'column selection only; all saved timestamps and samples retained; source magnitudes are hypot(original real, imaginary); no temporal averaging, smoothing or decimation','datasets':record},indent=2)+'\n')
 print('Compacted validation-only tables; detailed main/additional states and observations retained')
