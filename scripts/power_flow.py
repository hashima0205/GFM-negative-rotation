from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from flows import draw_all_flows,export_flows
if __name__=="__main__":
    if "--export" in sys.argv:export_flows()
    else:draw_all_flows()
