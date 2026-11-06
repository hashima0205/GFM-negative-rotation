from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from flows import comparison_views
from postprocess import write_check
if __name__=="__main__":
    _,report=comparison_views(draw=False)
    print(write_check("power_flow_comparison.json",report))
