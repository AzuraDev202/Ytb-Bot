"""Write public scan data as text rather than executable Excel formulas."""
import os
from pathlib import Path
import tempfile

import pandas as pd


def write_results_excel(frame, path, sheet_name):
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.xlsx', delete=False) as handle:
            temporary = Path(handle.name)
        with pd.ExcelWriter(temporary, engine='openpyxl') as writer:
            frame.to_excel(writer, sheet_name=sheet_name, index=False)
            for row in writer.sheets[sheet_name].iter_rows():
                for cell in row:
                    if cell.data_type == 'f':
                        cell.data_type = 's'
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
