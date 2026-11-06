"""Check displayed physical paths against saved observations and the historical C-equivalent path."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from postprocess import ROOT,RESULTS,verify,case_info,study,main_cases,section_settings,native_coordinates,base_frequency,control_label,save_figure,write_check,option,safe_output
def main():
    for case in main_cases()+study()['cases']['additional']:
        verify(RESULTS/case)
    records=[]
    for case in main_cases():
        display=pd.read_csv(ROOT/'results/fault_basins'/case/'physical_fault_projection.csv')
        source=pd.read_csv(RESULTS/case/'observations.csv.gz',usecols=['t_absolute_s','t_post_s','stage',*[f'b{b}_{k}' for b in [2,3,7] for k in ['delta_rad','df_Hz']]])
        source=source[source.t_post_s<=30].copy()
        assert np.array_equal(source.t_absolute_s.to_numpy(),display.t_absolute_s.to_numpy())
        assert np.array_equal(source.stage.to_numpy(),display.stage.to_numpy())
        theta=source[[f'b{b}_delta_rad' for b in [2,3,7]]].mean(axis=1)
        freq=source[[f'b{b}_df_Hz' for b in [2,3,7]]].mean(axis=1)
        error=max(np.max(abs(theta.to_numpy()-display.theta_rad.to_numpy())),np.max(abs(freq.to_numpy()-display.df_Hz.to_numpy())))
        assert error<1e-12
        jumps=[]
        for left,right in [('pre','fault'),('fault','post')]:
            a=display[display.stage==left].iloc[-1];b=display[display.stage==right].iloc[0]
            assert abs(a.t_absolute_s-b.t_absolute_s)<1e-12
            jumps.append(max(abs(a.theta_rad-b.theta_rad),abs(a.df_Hz-b.df_Hz)))
        assert max(jumps)<1e-12
        records.append(dict(case=case,rows=len(display),max_projection_export_error=float(error),max_internal_coordinate_switch_jump=max(jumps)))
    old=pd.read_csv(ROOT/'provenance/reference_results/historical_D1_10_fault_projection.csv')
    new=pd.read_csv(ROOT/'results/fault_basins/C/physical_fault_projection.csv')
    old['stamp']=old.t_absolute_s.round(8);new['stamp']=new.t_absolute_s.round(8)
    joined=old.merge(new,on=['stage','stamp'],suffixes=('_old','_new'),validate='one_to_one')
    assert len(joined)==len(old)
    angle_error=float((joined.theta_rad_old-joined.theta_rad_new).abs().max())
    frequency_error=float((joined.df_Hz_old-joined.df_Hz_new).abs().max())
    assert angle_error<1e-8 and frequency_error<1e-8
    report=dict(physical_export_checks=records,historical_D1_10_vs_C=dict(matched_timestamps=len(joined),max_angle_error_rad=angle_error,max_frequency_error_Hz=frequency_error,time_matching='same event stage and absolute timestamp rounded to 1e-8 s; no interpolation',old_mp=0.1,old_D1=10,current_mp=0.05,current_D1=0,effective_nominal_damping=20))
    write_check('basin_view_trajectory_checks.json',report)
    print(json.dumps(report,indent=2))

if __name__=="__main__":main()
