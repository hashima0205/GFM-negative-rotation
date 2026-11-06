"""Check saved identities, figure files, local documentation links and import safety."""
from pathlib import Path
import json,re,runpy,sys,tomllib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from postprocess import ROOT,catalog,verify,sha,write_check
def main():
    for dataset in catalog()['datasets']:verify(ROOT/dataset)
    figures=tomllib.loads((ROOT/'figures/catalog.toml').read_text())
    assert figures['presentation_hash']==sha(ROOT/'inputs/figures.toml'),'Archived figures have different presentation settings; redraw into a new output directory.'
    for path,record in figures['figures'].items():
        for filename,expected in record['files'].items():assert sha(ROOT/filename)==expected,filename
    links=0
    for document in [ROOT/'README.md',*sorted((ROOT/'docs').glob('*.md'))]:
        text=document.read_text();assert text.count('```')%2==0,document
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
            if '://' in target:continue
            filename,separator,anchor=target.partition('#')
            destination=document.parent/filename if filename else document
            assert destination.exists(),(document,target)
            if separator and destination.is_file() and destination.suffix=='.md':
                content=re.sub(r'```.*?```','',destination.read_text(),flags=re.S)
                headings=re.findall(r'^#{1,6}\s+(.+)$',content,flags=re.M)
                slugs={re.sub(r'[^\w\- ]','',h.lower()).replace(' ','-') for h in headings}
                assert anchor in slugs,(document,target,'missing anchor')
            links+=1
    before={str(p):sha(p) for prefix in ['results','figures'] for p in (ROOT/prefix).rglob('*') if p.is_file()}
    for script in sorted((ROOT/'scripts').glob('*.py')):
        if script.name==Path(__file__).name:continue
        runpy.run_path(str(script),run_name='_import_check_')
    after={str(p):sha(p) for prefix in ['results','figures'] for p in (ROOT/prefix).rglob('*') if p.is_file()}
    assert before==after,'Import modified reference data'
    report=dict(datasets=len(catalog()['datasets']),figures=len(figures['figures']),relative_links=links,imports_changed_reference_data=False,math_fences_balanced=True)
    print(write_check('repository_checks.json',report));print(json.dumps(report,indent=2))
if __name__=='__main__':main()
