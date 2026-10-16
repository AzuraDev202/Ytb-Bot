"""Capture the actual desktop UI for visual checks (does not call YouTube)."""
import argparse
from pathlib import Path
import sys
import time
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import ImageGrab
from ytb_bot.ui.desktop import YtbBotApp

parser = argparse.ArgumentParser()
parser.add_argument("--theme", choices=["dark", "light"], default="dark")
parser.add_argument("--compact", action="store_true")
parser.add_argument("--excel", action="store_true", help="Preview with a clearly named sample workbook")
parser.add_argument("--output", default="artifacts/ui/dashboard.png")
args = parser.parse_args()
temporary = tempfile.TemporaryDirectory()
with patch.object(YtbBotApp, "check_updates"):
    app = YtbBotApp()
    try:
        app.view.change_theme("Tối" if args.theme == "dark" else "Sáng")
        app.view.theme_switch.set("Tối" if args.theme == "dark" else "Sáng")
        if args.compact:
            app.geometry("940x640+30+30")
        if args.excel:
            import pandas as pd
            workbook = Path(temporary.name) / "du-lieu-minh-hoa.xlsx"
            pd.DataFrame({"Tên kênh (minh họa)": ["Demo AI Studio", "Demo Creator", "Demo Technology"],
                          "Từ khóa": ["AI Agent", "Content creator", "Công nghệ"],
                          "Lượt xem": [12500, 8300, 6700], "Tuổi kênh (ngày)": [30, 45, 18]}).to_excel(workbook, index=False)
            app._show_excel(str(workbook))
        app.attributes("-topmost", True)
        deadline = time.monotonic() + 1.2
        while time.monotonic() < deadline:
            app.update()
            time.sleep(0.02)
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        app.deiconify()
        app.lift()
        app.update()
        ImageGrab.grab(bbox=(app.winfo_rootx(), app.winfo_rooty(),
                            app.winfo_rootx() + app.winfo_width(),
                            app.winfo_rooty() + app.winfo_height())).save(target)
        print(f"Saved {target} ({app.winfo_width()}x{app.winfo_height()})")
    finally:
        for timer in app.tk.splitlist(app.tk.call("after", "info")):
            app.tk.call("after", "cancel", timer)
        app.destroy()
        temporary.cleanup()
