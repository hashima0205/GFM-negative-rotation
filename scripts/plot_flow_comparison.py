"""Publish six audited A/B/C pre-fault and clearing+1 s power-flow views.

The three pre-fault views share one canonical equilibrium dataset. Each view is
also checked against its own case's saved observations before it is rendered.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from network_figure import draw_single_line,load_snapshot
from plot import save

ROOT=Path(__file__).resolve().parents[1]
BUS=[1,2,3,7]
POST_TIME=1.0

def build_comparison():
    records=[];checks=[]
    for case in ['A','B','C']:
        columns=['t_absolute_s','t_post_s','stage',*[f'b{b}_{key}' for b in BUS for key in ['U_r_pu','U_i_pu','Ig_r_pu','Ig_i_pu','Pterminal_pu','Qterminal_pu']]]
        observations=pd.read_csv(ROOT/'results'/case/'observations.csv.gz',usecols=columns)
        postfolder=ROOT/'results/power_flow'/f'{case}_post_{POST_TIME:g}s'
        postmeta=pd.read_csv(postfolder/'metadata.csv').iloc[0].to_dict()
        for stage in ['pre','post']:
            prefault=stage=='pre'
            folder=ROOT/'results/power_flow/common_pre_equilibrium' if prefault else postfolder
            buses,lines,meta,summary=load_snapshot(folder)
            meta=dict(meta)
            meta.update(case=case,control_conditions=postmeta['control_conditions'])
            sample=observations[observations.stage==stage]
            row=sample.iloc[0] if prefault else sample.iloc[np.argmin(abs(sample.t_post_s-POST_TIME))]
            expected_absolute=0.0 if prefault else 2.15
            assert abs(float(row.t_absolute_s)-expected_absolute)<1e-9
            assert abs(float(meta['time_absolute_s'])-expected_absolute)<1e-9
            assert bool(int(meta['is_equilibrium']))==prefault
            exported=pd.read_csv(folder/'voltages.csv').set_index('bus')
            errors=[]
            for b in BUS:
                voltage=complex(row[f'b{b}_U_r_pu'],row[f'b{b}_U_i_pu'])
                current=complex(row[f'b{b}_Ig_r_pu'],row[f'b{b}_Ig_i_pu'])
                reference=complex(exported.loc[b,'U_r_pu'],exported.loc[b,'U_i_pu'])
                injection=complex(buses.loc[b,'P_injection_pu'],buses.loc[b,'Q_injection_pu'])
                measured=complex(row[f'b{b}_Pterminal_pu'],row[f'b{b}_Qterminal_pu'])
                errors.extend([abs(voltage-reference),abs(voltage*np.conj(current)-injection),abs(measured-injection)])
            qerror=float(buses.loc[BUS,'Q_injection_pu'].sum()+buses.loc[6,'Q_injection_pu']+summary['capacitor_Q_pu']-summary['line_Q_loss_pu'])
            assert max(*errors,abs(qerror),abs(summary['P_balance_error_pu']),summary['max_nodal_power_error_pu'])<1e-8
            assert bool(lines.loc[7,'active'])==prefault
            name=f'{case}_pre_equilibrium' if prefault else f'{case}_post_{POST_TIME:g}s'
            title=f'Case {case}: pre-fault equilibrium (t = 0.00 s)' if prefault else f'Case {case}: 1.00 s after fault clearing'
            meta['snapshot']=name
            figure=ROOT/'figures/details/power_flow'/name
            save(draw_single_line(buses,lines,meta,summary,title=title),figure)
            records.append(dict(case=case,stage=stage,time_absolute_s=expected_absolute,time_post_clearing_s=float(row.t_post_s),state_kind='equilibrium' if prefault else 'saved dynamic snapshot',control_conditions=meta['control_conditions'],source_data=str(folder.relative_to(ROOT)),source_observations=f'results/{case}/observations.csv.gz',PNG=str(figure.with_suffix('.png').relative_to(ROOT)),PDF=str(figure.with_suffix('.pdf').relative_to(ROOT))))
            checks.append(dict(case=case,stage=stage,max_saved_observation_error_pu=float(max(errors)),max_nodal_power_error_pu=summary['max_nodal_power_error_pu'],P_balance_error_pu=summary['P_balance_error_pu'],Q_balance_error_pu=qerror,L7_active=bool(lines.loc[7,'active'])))
    pd.DataFrame(records).to_csv(ROOT/'results/power_flow/comparison.csv',index=False)
    report=dict(post_clearing_time_s=POST_TIME,figure_count=len(records),prefault_data_shared=True,all_passed=True,checks=checks)
    (ROOT/'results/validation/power_flow_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':build_comparison()
