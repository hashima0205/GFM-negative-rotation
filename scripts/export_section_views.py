"""Export plot tables from newly computed section points; inputs stay read-only."""
from pathlib import Path
import argparse,sys,shutil,tomllib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
import matplotlib.tri as mtri
from postprocess import ROOT,RESULTS,verify,case_info,study,main_cases,REMOTE,safe_output,sha
from toml_writer import dumps
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sections',type=Path,required=True)
    p.add_argument('--roots',type=Path,default=ROOT/'results/basins')
    p.add_argument('--results',type=Path)
    p.add_argument('--output',type=Path,default=ROOT/'outputs/section-views')
    p.add_argument('--local',action='store_true');args=p.parse_args()
    for case in main_cases():
        source=verify(args.sections/case);row,cfg=case_info(case)
        destination=safe_output(args.output/case/'placeholder').parent
        if any(destination.iterdir()):raise FileExistsError(destination)
        points=[tomllib.loads(f.read_text()) for f in sorted((source/'points').glob('*.toml'))]
        excluded={'initial_native','final_native','initial_bus_voltage_ri','final_bus_voltage_ri','machine_metrics'}
        pd.DataFrame([{k:v for k,v in a.items() if k not in excluded} for a in points]).to_csv(destination/'classification.csv',index=False)
        metrics=[[a['point'],*m] for a in points for m in a['machine_metrics']]
        pd.DataFrame(metrics,columns=['point','bus','classification','turns','tail_mean_df_Hz','tail_max_abs_df_Hz','phase_error_rad','phase_width_rad','min_window_turns','max_window_turns']).to_csv(destination/'machines.csv',index=False)
        roots=verify(source if args.local else args.roots/case)
        shutil.copyfile(roots/'roots.csv',destination/'roots.csv')
        shutil.copytree(source/'points',destination/'points')
        shutil.copyfile(source/'section.toml',destination/'section.toml')
        record=tomllib.loads((source/'run_record.toml').read_text())
        if not args.local:
            xy=pd.DataFrame([(a['theta_actual'],a['df_actual']) for a in points])
            pd.DataFrame(mtri.Triangulation(xy[0],xy[1]).triangles,columns=['vertex_0','vertex_1','vertex_2']).to_csv(destination/'triangles.csv',index=False)
            columns=['t_absolute_s','t_post_s','stage',*[f'b{b}_{k}' for b in study()['network']['gfm_buses'] for k in ['delta_rad','df_Hz']]]
            d=pd.read_csv(RESULTS/case/'observations.csv.gz',usecols=columns)
            section=tomllib.loads(record['section_text']);d=d[d.t_post_s<=section['fault_trajectory_post_horizon_s']].copy()
            d['theta_rad']=d[[f'b{b}_delta_rad' for b in REMOTE()]].mean(axis=1)
            d['df_Hz']=d[[f'b{b}_df_Hz' for b in REMOTE()]].mean(axis=1)
            d.to_csv(destination/'physical_fault_projection.csv',index=False)
        record['derived_from']=str(source)
        record['files']={str(f.relative_to(ROOT)) if f.is_relative_to(ROOT) else str(f):sha(f) for f in destination.rglob('*') if f.is_file()}
        (destination/'run_record.toml').write_text(dumps(record))
    print('Created section-view tables in',args.output)
if __name__=='__main__':main()
