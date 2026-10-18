"""Capture the actual desktop UI for visual checks (does not call YouTube)."""
import argparse
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PIL import ImageGrab
from ytb_bot.legacy_ui.desktop import YtbBotApp

parser = argparse.ArgumentParser()
parser.add_argument("--theme", choices=["dark", "light"], default="dark")
parser.add_argument("--compact", action="store_true")
parser.add_argument("--excel", action="store_true", help="Preview with a clearly named sample workbook")
parser.add_argument("--output", default="artifacts/ui/dashboard.png")
args = parser.parse_args()
temporary = tempfile.TemporaryDirectory()
with patch.object(YtbBotApp, "check_updates"):
    app = YtbBotApp()
    result = {}
    try:
        def prepare():
            try:
                if not app.winfo_viewable():
                    raise RuntimeError("Desktop startup left the window hidden")
                app.view.change_theme("Dark" if args.theme == "dark" else "Light")
                app.view.theme_switch.set("Dark" if args.theme == "dark" else "Light")
                if args.compact:
                    app.geometry("940x640+30+30")
                if args.excel:
                    import pandas as pd
                    workbook = Path(temporary.name) / "sample-data.xlsx"
                    pd.DataFrame({"Channel name (example)": ["Demo AI Studio", "Demo Creator", "Demo Technology"],
                                  "Keyword": ["AI Agent", "Content creator", "Technology"],
                                  "Views": [12500, 8300, 6700], "Channel age (days)": [30, 45, 18]}).to_excel(workbook, index=False)
                    app._show_excel(str(workbook))
                app.attributes("-topmost", True)
                app.after(1200, capture)
            except Exception as error:
                result["error"] = error
                app.quit()

        def capture():
            try:
                if not app.winfo_viewable():
                    raise RuntimeError("Desktop window became hidden before capture")
                target = Path(args.output)
                target.parent.mkdir(parents=True, exist_ok=True)
                ImageGrab.grab(bbox=(app.winfo_rootx(), app.winfo_rooty(),
                                    app.winfo_rootx() + app.winfo_width(),
                                    app.winfo_rooty() + app.winfo_height())).save(target)
                result["captured"] = True
                print(f"Saved {target} ({app.winfo_width()}x{app.winfo_height()})")
            except Exception as error:
                result["error"] = error
            finally:
                app.quit()

        app.after(200, prepare)
        app.after(10000, app.quit)
        app.mainloop()
        if "error" in result:
            raise result["error"]
        if not result.get("captured"):
            raise RuntimeError("Desktop preview timed out")
    finally:
        for timer in app.tk.splitlist(app.tk.call("after", "info")):
            app.tk.call("after", "cancel", timer)
        app.destroy()
        temporary.cleanup()
