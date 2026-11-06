"""Export selected validation columns to a new file; never modify source waveforms."""
from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
from postprocess import safe_output,study
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('destination',type=Path)
    args=parser.parse_args();destination=safe_output(args.destination)
    if destination.exists():raise FileExistsError(destination)
    fields=['delta_rad','df_Hz','U_pu','Ig_pu','Pcap_pu','Qcap_pu','ref_out_d_pu','ref_out_q_pu']
    columns=['t_absolute_s','t_post_s','stage']+[f'b{b}_{key}' for b in study()['network']['gfm_buses'] for key in fields]
    pd.read_csv(args.source,usecols=columns).to_csv(destination,index=False,compression='gzip' if destination.suffix=='.gz' else None)
if __name__=='__main__':main()
