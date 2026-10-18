"""Workbook sessions for the React bridge; import always uses original data."""
import json
from pathlib import Path
import threading
import pandas as pd


class Workbook:
    PAGE_SIZE = 100

    def __init__(self):
        self._lock = threading.RLock()
        self._path = None
        self._sheets = []
        self._frames = {}

    def open(self, path):
        path = Path(path)
        with pd.ExcelFile(path) as excel:
            sheets = excel.sheet_names
            first = excel.parse(sheets[0])
        with self._lock:
            self._path, self._sheets, self._frames = path, sheets, {sheets[0]: first}
            return {"filename": path.name, "sheets": list(sheets)}

    def _frame(self, sheet):
        if sheet not in self._sheets:
            raise ValueError("Select a valid Excel file and worksheet.")
        if sheet not in self._frames:
            self._frames[sheet] = pd.read_excel(self._path, sheet_name=sheet)
        return self._frames[sheet]

    def from_rows(self, rows, name="Results", columns=None):
        """Present saved application data through the same paged table interface."""
        with self._lock:
            self._path = None
            self._sheets = [name]
            self._frames = {name: pd.DataFrame(rows, columns=columns)}
            return {"filename": name, "sheets": [name], "internal": True}

    def page(self, sheet, query="", page=0, sort=None, descending=False):
        with self._lock:
            original = self._frame(sheet)
            data = original
            if query and not data.empty:
                mask = data.fillna("").astype(str).apply(lambda col: col.str.contains(str(query), case=False, regex=False)).any(axis=1)
                data = data.loc[mask]
            if sort is not None and len(data.columns):
                column = data.columns[int(sort)]
                try:
                    data = data.sort_values(column, ascending=not descending, kind="stable", na_position="last")
                except TypeError:
                    data = data.sort_values(column, ascending=not descending, kind="stable", key=lambda s: s.astype(str).str.casefold())
            page = max(0, min(int(page), max(0, (len(data) - 1) // self.PAGE_SIZE)))
            start = page * self.PAGE_SIZE
            rows = json.loads(data.iloc[start:start + self.PAGE_SIZE].to_json(orient="values", date_format="iso"))
            return {"columns": [str(col) for col in original.columns], "rows": rows, "page": page,
                    "pages": max(1, (len(data) + self.PAGE_SIZE - 1) // self.PAGE_SIZE), "total": len(data), "original_total": len(original)}

    def keywords(self, sheet, column):
        with self._lock:
            values = self._frame(sheet).iloc[:, int(column)].dropna()
            return list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))
