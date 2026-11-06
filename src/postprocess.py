"""Saved-result identities, settings and output paths shared by Python entry points.

Reference data are read-only. Plot outputs and validation reports default to outputs/.
The catalog binds archived data to their verified configuration and equivalent code.
"""
from pathlib import Path
import hashlib,json,sys,tomllib
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
_verified=set();_used=set();_catalog=None
def option(name,default):
    return Path(sys.argv[sys.argv.index(name)+1]).resolve() if name in sys.argv else Path(default)
RESULTS=option('--results',ROOT/'results')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def catalog():
    global _catalog
    if _catalog is None:_catalog=tomllib.loads((ROOT/'provenance/reproduction.toml').read_text())
    return _catalog
def assert_hashes(hashes,kind):
    for path,expected in hashes.items():
        p=ROOT/path
        if not p.is_file() or sha(p)!=expected:
            raise RuntimeError(f'Stale {kind}: {path} differs from the saved identity. Recompute to a new output directory; do not reuse these results.')
def verify_identity():
    if 'identity' not in _verified:
        c=catalog();assert_hashes(c['code'],'model/code');_verified.add('identity')
def verify(folder):
    folder=Path(folder).resolve();key=str(folder.relative_to(ROOT)) if folder.is_relative_to(ROOT) else str(folder)
    if key not in _verified:
        c=catalog()
        if key in c['datasets']:
            verify_identity();record=c['datasets'][key];assert_hashes(record['inputs'],'input');assert_hashes(record['files'],'saved data')
        else:
            record=tomllib.loads((folder/'run_record.toml').read_text())
            assert_hashes(record['code'],'model/code');assert_hashes(record['inputs'],'input');assert_hashes(record.get('files',{}),'saved data')
        _verified.add(key)
    _used.add(key)
    return folder
def case_info(tag):
    folder=verify(RESULTS/tag)
    if RESULTS==ROOT/'results':
        row=catalog()['cases'][tag];physical=tomllib.loads(catalog()['snapshots']['inputs/'+row['config']])
        return dict(row),physical
    record=tomllib.loads((folder/'run_record.toml').read_text())
    return record['case'],tomllib.loads(record['config_text'])
def study():
    if RESULTS!=ROOT/'results':
        records=sorted(RESULTS.glob('*/run_record.toml'))
        if not records:raise RuntimeError(f'No run settings in {RESULTS}')
        result=tomllib.loads(tomllib.loads(records[0].read_text())['study_text'])
    else:result=tomllib.loads(catalog()['snapshots']['inputs/study.toml'])
    result['figures']=tomllib.loads((ROOT/'inputs/figures.toml').read_text())
    return result
def section_settings(local=False):
    flag='--local-results' if local else '--section-results'
    folder=option(flag,RESULTS/('basins' if local else 'fault_basins'))
    records=sorted(folder.glob('*/run_record.toml'))
    if records:
        verify(records[0].parent)
        return tomllib.loads(tomllib.loads(records[0].read_text())['section_text'])
    verify_identity()
    return tomllib.loads(catalog()['snapshots']['inputs/local_basin.toml' if local else 'inputs/fault_basin.toml'])
def main_cases():return study()['cases']['main']
BUS=lambda:study()['network']['gfm_buses']
REMOTE=lambda:study()['network']['remote_buses']
def base_frequency(case):
    _,cfg=case_info(case);return round(cfg['machines'][0]['droop₊ω0']/(2*np.pi),12)
def control_label(case,math=False):
    row,_=case_info(case)
    if row['control']=='Droop':return (r'Droop, $\tau_p='+f"{float(row['taup']):.2f}"+'$ s') if math else f"Droop: tau_p={float(row['taup']):.2f} s, mp={100*float(row['mp']):g}%"
    return (r'VSM, $H='+f"{float(row['H']):g}"+'$ s') if math else f"VSM: H={float(row['H']):g} s, mp={100*float(row['mp']):g}%, D1={float(row['D1']):g}, D2={float(row['D2']):g}"
def machine_indices(field,remote=False):
    # Fixed native state layout, documented in PARAMETERS; one definition for readers.
    offsets={'angle':13,'frequency':12,'Ig_r':4,'Ig_i':3}
    buses=BUS();chosen=REMOTE() if remote else buses
    return [13*j+offsets[field] for j,b in enumerate(buses) if b in chosen]
def native_coordinates(frame,case):
    row,cfg=case_info(case);idx=machine_indices('angle',True);fi=machine_indices('frequency',True)
    angle=frame[[f'x{i}' for i in idx]].mean(axis=1)
    if row['control']=='VSM':freq=frame[[f'x{i}' for i in fi]].mean(axis=1)*base_frequency(case)
    else:
        freq=np.mean([base_frequency(case)*float(row['mp'])*(cfg['machines'][BUS().index(b)]['droop₊Pset']-frame[f'x{i}']) for b,i in zip(REMOTE(),fi)],axis=0)
    return angle,freq
def safe_output(path):
    path=Path(path).resolve()
    if any(path.is_relative_to(ROOT/p) for p in ['results','figures','provenance']):
        raise RuntimeError(f'Reference directory is read-only: {path}. Choose --output outside results/, figures/, provenance/.')
    path.parent.mkdir(parents=True,exist_ok=True);return path
def figure_path(path):
    relative=Path(path).relative_to(ROOT/'figures')
    return safe_output(option('--output',ROOT/'outputs/figures')/relative)
def write_check(name,value):
    path=safe_output(option('--output',ROOT/'outputs/checks')/name)
    path.write_text(json.dumps(value,indent=2)+'\n');return path
def save_figure(fig,path):
    import matplotlib.pyplot as plt
    path=figure_path(path)
    for ext in ['png','pdf']:fig.savefig(path.with_suffix('.'+ext),dpi=240,bbox_inches='tight',facecolor='white')
    sources=dict(datasets=sorted(_used),input_hashes=catalog()['inputs'],presentation_hash=sha(ROOT/'inputs/figures.toml'),plot_code={str(p.relative_to(ROOT)):sha(p) for p in sorted([*(ROOT/'scripts').glob('*.py'),*(ROOT/'src').glob('*.py')])},axes=[dict(xlabel=a.get_xlabel(),ylabel=a.get_ylabel(),xlim=list(a.get_xlim()),ylim=list(a.get_ylim()),title=a.get_title()) for a in fig.axes])
    path.with_suffix('.sources.json').write_text(json.dumps(sources,indent=2)+'\n');plt.close(fig)
