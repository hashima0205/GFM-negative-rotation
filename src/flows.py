"""Saved network-flow data export and rendering, without time integration."""
from pathlib import Path
import json,tomllib
import numpy as np
import pandas as pd
from network_plot import draw_single_line,load_snapshot
from postprocess import *
BUS=study()['network']['gfm_buses']
BRANCHES=study()['network']['branches']
NON=np.array([b-1 for b in range(1,9) if b!=study()['network']['slack_bus']])
save=save_figure
def register_export(folder,row,cfg):
    # Preserve the verified source-run settings in a derived-data identity.
    source=verify(RESULTS/row['case'])/'run_record.toml'
    if source.exists():
        original=tomllib.loads(source.read_text())
        data={k:original[k] for k in ['case','inputs','code','config_text','study_text']}
    else:
        c=catalog();data=dict(case=row,inputs=c['inputs'],code=c['code'],config_text=c['snapshots']['inputs/'+row['config']],study_text=c['snapshots']['inputs/study.toml'])
    from toml_writer import dumps
    (folder/'run_record.toml').write_text(dumps(data))
def network(stage,cfg):
 y=np.zeros((8,8),complex);lines=[]
 for j,((a,b),(r,x)) in enumerate(zip(BRANCHES,cfg['lines']),1):
  active=0 if stage=='post' and j in study()['network']['opened_lines'] else 1;g=active/complex(r,x);a-=1;b-=1
  y[a,a]+=g;y[b,b]+=g;y[a,b]-=g;y[b,a]-=g
  lines.append(dict(line=j,from_bus=a+1,to_bus=b+1,R_pu=r,X_pu=x,active=active))
 total=y.copy();total[study()['network']['load_bus']-1,study()['network']['load_bus']-1]+=complex(cfg['G'],cfg['B']);total[study()['network']['fault_bus']-1,study()['network']['fault_bus']-1]+=cfg['fault_G'] if stage=='fault' else 0
 return y,total,lines
def export(case,name,stage,ig,time,equilibrium=False):
 row,cfg=case_info(main_cases()[0] if case=="common" else case)
 yl,y,lines=network(stage,cfg);inj=np.zeros(8,complex);inj[np.array(BUS)-1]=ig
 u=np.ones(8,complex);u[NON]=np.linalg.solve(y[np.ix_(NON,NON)],inj[NON]-y[NON,study()['network']['slack_bus']-1])
 reference=inj.copy();reference[study()['network']['load_bus']-1]=-complex(cfg['G'],cfg['B'])*u[study()['network']['load_bus']-1];reference[study()['network']['fault_bus']-1]=-(cfg['fault_G'] if stage=='fault' else 0)*u[study()['network']['fault_bus']-1]
 current=yl@u;reference[study()['network']['slack_bus']-1]=current[study()['network']['slack_bus']-1]
 kcl=np.max(np.abs(current-reference));pqerr=np.max(np.abs(u*np.conj(current-reference)))
 folder=safe_output(option('--output',ROOT/'outputs/power_flow')/name/'placeholder').parent
 if any(folder.iterdir()):raise FileExistsError(f'Export already exists: {folder}; choose a new --output directory.')
 pd.DataFrame([dict(bus=b,U_r_pu=u[b-1].real,U_i_pu=u[b-1].imag,reference_P_injection_pu=(u[b-1]*np.conj(reference[b-1])).real,reference_Q_injection_pu=(u[b-1]*np.conj(reference[b-1])).imag) for b in range(1,9)]).to_csv(folder/'voltages.csv',index=False)
 pd.DataFrame(lines).to_csv(folder/'branches.csv',index=False)
 conditions='Common equilibrium of '+('/'.join(main_cases())) if case=='common' else control_label(case)
 pd.DataFrame([dict(snapshot=name,case=case,time_absolute_s=time,t_post_s=time-cfg['clearing'],stage=stage,is_equilibrium=int(equilibrium),control_conditions=conditions,H_s=float(row['H']) if row['control']=='VSM' else np.nan,D1=float(row['D1']),D2=float(row['D2']),load_G_pu=cfg['G'],capacitor_B_pu=cfg['B'],fault_G_pu=cfg['fault_G'] if stage=='fault' else 0)]).to_csv(folder/'metadata.csv',index=False)
 register_export(folder,row,cfg)
 buses,edges,meta,total=load_snapshot(folder)
 qbalance=buses.loc[BUS,'Q_injection_pu'].sum()+buses.loc[6,'Q_injection_pu']+total['capacitor_Q_pu']-total['line_Q_loss_pu']
 audit={**total,'max_KCL_current_error_pu':float(kcl),'max_nodal_complex_power_error_pu':float(pqerr),'Q_balance_error_pu':float(qbalance),'kind':'equilibrium' if equilibrium else 'saved dynamic snapshot','time_absolute_s':float(time)}
 assert max(kcl,pqerr,abs(qbalance),abs(total['P_balance_error_pu']))<1e-8
 edges.to_csv(folder/'line_powers.csv');buses.to_csv(folder/'bus_powers.csv');(folder/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
 from toml_writer import dumps
 record=tomllib.loads((folder/'run_record.toml').read_text());record['files']={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):sha(p) for p in folder.iterdir() if p.name!='run_record.toml'}
 (folder/'run_record.toml').write_text(dumps(record))
 return buses,edges,meta,total

POST_TIME=study()["figures"]["flow_comparison_post_s"]
def comparison_views(draw=True):
    records=[];checks=[]
    for case in main_cases():
        row_settings,cfg=case_info(case)
        columns=['t_absolute_s','t_post_s','stage',*[f'b{b}_{key}' for b in BUS for key in ['U_r_pu','U_i_pu','Ig_r_pu','Ig_i_pu','Pterminal_pu','Qterminal_pu']]]
        observations=pd.read_csv(RESULTS/case/'observations.csv.gz',usecols=columns)
        postfolder=RESULTS/'power_flow'/f'{case}_post_{POST_TIME:g}s'
        postmeta=pd.read_csv(postfolder/'metadata.csv').iloc[0].to_dict()
        for stage in ['pre','post']:
            prefault=stage=='pre'
            folder=RESULTS/'power_flow/common_pre_equilibrium' if prefault else postfolder
            buses,lines,meta,summary=load_snapshot(folder)
            meta=dict(meta)
            meta.update(case=case,control_conditions=postmeta['control_conditions'])
            sample=observations[observations.stage==stage]
            row=sample.iloc[0] if prefault else sample.iloc[np.argmin(abs(sample.t_post_s-POST_TIME))]
            expected_absolute=float(sample.t_absolute_s.iloc[0]) if prefault else cfg['clearing']+POST_TIME
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
            assert all(bool(lines.loc[i,'active'])==prefault for i in study()['network']['opened_lines'])
            name=f'{case}_pre_equilibrium' if prefault else f'{case}_post_{POST_TIME:g}s'
            title=f'Case {case}: pre-fault equilibrium (t = {expected_absolute:.2f} s)' if prefault else f'Case {case}: {POST_TIME:.2f} s after fault clearing'
            meta['snapshot']=name
            figure=ROOT/'figures/details/power_flow'/name
            if draw:save(draw_single_line(buses,lines,meta,summary,title=title),figure)
            records.append(dict(case=case,stage=stage,time_absolute_s=expected_absolute,time_post_clearing_s=float(row.t_post_s),state_kind='equilibrium' if prefault else 'saved dynamic snapshot',control_conditions=meta['control_conditions'],source_data=str(folder.relative_to(ROOT)),source_observations=f'results/{case}/observations.csv.gz',PNG=str(figure.with_suffix('.png').relative_to(ROOT)),PDF=str(figure.with_suffix('.pdf').relative_to(ROOT))))
            checks.append(dict(case=case,stage=stage,max_saved_observation_error_pu=float(max(errors)),max_nodal_power_error_pu=summary['max_nodal_power_error_pu'],P_balance_error_pu=summary['P_balance_error_pu'],Q_balance_error_pu=qerror,opened_line_status={str(i):bool(lines.loc[i,'active']) for i in study()['network']['opened_lines']}))
    return records,dict(post_clearing_time_s=POST_TIME,figure_count=len(records),prefault_data_shared=True,all_passed=True,checks=checks)

def draw_all_flows():
    for folder in sorted((RESULTS/'power_flow').iterdir()):
        if not folder.is_dir() or not (folder/'metadata.csv').exists():continue
        values=load_snapshot(folder)
        save(draw_single_line(*values,title=folder.name.replace('_',' ')),ROOT/'figures/details/power_flow'/folder.name)
        if folder.name=='common_post_equilibrium':
            save(draw_single_line(*values,schematic=True,title='Shared eight-bus four-GFM system'),ROOT/'figures/paper/system')
    comparison_views()

def export_flows():
    case=main_cases()[0];_,cfg=case_info(case)
    for stage in ['pre','post']:
        x=np.loadtxt(RESULTS/case/f'{stage}_root.csv',delimiter=',')
        ig=[complex(x[i-1],x[j-1]) for i,j in zip(machine_indices('Ig_r'),machine_indices('Ig_i'))]
        export('common','common_'+stage+'_equilibrium',stage,ig,0. if stage=='pre' else cfg['clearing'],True)
    for case in main_cases():
        _,cfg=case_info(case);d=pd.read_csv(RESULTS/case/'observations.csv.gz');post=d[d.stage=='post']
        for time in study()['figures']['flow_post_times_s']:
            row=post.iloc[np.argmin(abs(post.t_post_s-time))];assert abs(row.t_post_s-time)<1e-9
            ig=[complex(row[f'b{b}_Ig_r_pu'],row[f'b{b}_Ig_i_pu']) for b in BUS]
            export(case,f'{case}_post_{time:g}s','post',ig,float(row.t_absolute_s))
