"""Draw a saved single-line snapshot without rewriting its numeric data."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from network_plot import main
if __name__=="__main__":main()
