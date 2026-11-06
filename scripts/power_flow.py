"""Export signed line-end P/Q and audit terminal-network balances at saved times."""
from pathlib import Path
import json,tomllib,csv
import numpy as np
import pandas as pd
from network_figure import draw_single_line,load_snapshot
from plot import save
ROOT=Path(__file__).resolve().parents[1]
BUS=[1,2,3,7];BRANCHES=[(1,4),(4,6),(5,6),(3,5),(2,3),(2,5),(4,5),(2,8),(2,7),(7,8),(5,8)]
NON=np.array([0,1,2,3,4,6,7])
CFG=tomllib.loads((ROOT/'inputs/common.toml').read_text())
def network(stage):
 y=np.zeros((8,8),complex);lines=[]
 for j,((a,b),(r,x)) in enumerate(zip(BRANCHES,CFG['lines']),1):
  active=0 if stage=='post' and j==7 else 1;g=active/complex(r,x);a-=1;b-=1
  y[a,a]+=g;y[b,b]+=g;y[a,b]-=g;y[b,a]-=g
  lines.append(dict(line=j,from_bus=a+1,to_bus=b+1,R_pu=r,X_pu=x,active=active))
 total=y.copy();total[4,4]+=complex(CFG['G'],CFG['B']);total[3,3]+=20 if stage=='fault' else 0
 return y,total,lines
def export(case,name,stage,ig,time,equilibrium=False):
 yl,y,lines=network(stage);inj=np.zeros(8,complex);inj[np.array(BUS)-1]=ig
 u=np.ones(8,complex);u[NON]=np.linalg.solve(y[np.ix_(NON,NON)],inj[NON]-y[NON,5])
 reference=inj.copy();reference[4]=-complex(CFG['G'],CFG['B'])*u[4];reference[3]=-(20 if stage=='fault' else 0)*u[3]
 current=yl@u;reference[5]=current[5]
 kcl=np.max(np.abs(current-reference));pqerr=np.max(np.abs(u*np.conj(current-reference)))
 folder=ROOT/'results/power_flow'/name;folder.mkdir(parents=True,exist_ok=True)
 pd.DataFrame([dict(bus=b,U_r_pu=u[b-1].real,U_i_pu=u[b-1].imag,reference_P_injection_pu=(u[b-1]*np.conj(reference[b-1])).real,reference_Q_injection_pu=(u[b-1]*np.conj(reference[b-1])).imag) for b in range(1,9)]).to_csv(folder/'voltages.csv',index=False)
 pd.DataFrame(lines).to_csv(folder/'branches.csv',index=False)
 conditions='Common equilibrium of A/B/C' if case=='common' else ('Droop: tau_p='+('0.02' if case=='A' else '1.00')+' s, mp=5%' if case in ['A','B'] else 'VSM: H=2.5 s, mp=5%, D1=0, D2=100')
 pd.DataFrame([dict(snapshot=name,case=case,time_absolute_s=time,t_post_s=time-1.15,stage=stage,is_equilibrium=int(equilibrium),control_conditions=conditions,H_s=2.5 if case=='C' else np.nan,D1=0,D2=100 if case=='C' else (0 if case in ['A','B'] else np.nan),load_G_pu=CFG['G'],capacitor_B_pu=CFG['B'],fault_G_pu=20 if stage=='fault' else 0)]).to_csv(folder/'metadata.csv',index=False)
 buses,edges,meta,total=load_snapshot(folder)
 qbalance=buses.loc[BUS,'Q_injection_pu'].sum()+buses.loc[6,'Q_injection_pu']+total['capacitor_Q_pu']-total['line_Q_loss_pu']
 audit={**total,'max_KCL_current_error_pu':float(kcl),'max_nodal_complex_power_error_pu':float(pqerr),'Q_balance_error_pu':float(qbalance),'kind':'equilibrium' if equilibrium else 'saved dynamic snapshot','time_absolute_s':float(time)}
 assert max(kcl,pqerr,abs(qbalance),abs(total['P_balance_error_pu']))<1e-8
 edges.to_csv(folder/'line_powers.csv');buses.to_csv(folder/'bus_powers.csv');(folder/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 fig=draw_single_line(buses,edges,meta,total,title=name.replace('_',' '));save(fig,ROOT/'figures/details/power_flow'/name)
 return buses,edges,meta,total
if __name__=='__main__':
 for stage in ['pre','post']:
  x=np.loadtxt(ROOT/'results/C'/f'{stage}_root.csv',delimiter=',');ig=[complex(x[13*j+3],x[13*j+2]) for j in range(4)]
  values=export('common','common_'+stage+'_equilibrium',stage,ig,0. if stage=='pre' else 1.15,True)
  if stage=='post':save(draw_single_line(*values,schematic=True,title='Shared eight-bus four-GFM system'),ROOT/'figures/paper/system')
 for case in ['A','B','C']:
  d=pd.read_csv(ROOT/'results'/case/'observations.csv.gz')
  post=d[d.stage=='post']
  for tpost in [0.,1.,5.]:
   row=post.iloc[np.argmin(np.abs(post.t_post_s-tpost))]
   assert abs(row.t_post_s-tpost)<1e-9
   ig=[complex(row[f'b{b}_Ig_r_pu'],row[f'b{b}_Ig_i_pu']) for b in BUS]
   export(case,f'{case}_post_{tpost:g}s','post',ig,float(row.t_absolute_s))
 print('Created common schematic, 2 equilibrium and 9 matched-time dynamic flow figures')
 from plot_flow_comparison import build_comparison
 build_comparison()
