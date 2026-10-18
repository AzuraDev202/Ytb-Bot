"""Embedded, paginated Excel preview and keyword-column import."""
import math
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
import pandas as pd
from ytb_bot.legacy_ui import theme as t


class ExcelViewer(ctk.CTkFrame):
    PAGE_SIZE = 200

    def __init__(self, master, on_import):
        super().__init__(master, fg_color="transparent")
        self.on_import = on_import
        self.path = None
        self.data = pd.DataFrame()
        self.page = 0
        self.request_id = 0
        self.events = queue.Queue()
        self.column_names = []
        self.search = tk.StringVar(self)
        self._search_timer = None
        self._sort_column = None
        self._sort_ascending = True
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.grid_columnconfigure(1, weight=1)
        t.button(top, "Open Excel file", self.open_file, width=125).grid(row=0, column=0)
        self.filename = t.label(top, "No Excel file open", anchor="w")
        self.filename.grid(row=0, column=1, padx=12, sticky="ew")

        options = ctk.CTkFrame(self, fg_color="transparent")
        options.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        options.grid_columnconfigure((0, 1), weight=1)
        self.sheet_menu = ctk.CTkOptionMenu(options, values=["Select sheet"], state="disabled", height=36,
                                           fg_color=t.color("inset"), button_color=t.color("hover"), text_color=t.color("text"),
                                           command=self._select_sheet, dynamic_resizing=False)
        self.sheet_menu.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self.column_menu = ctk.CTkOptionMenu(options, values=["Select keyword column"], state="disabled", height=36,
                                            fg_color=t.color("inset"), button_color=t.color("hover"), text_color=t.color("text"),
                                            dynamic_resizing=False)
        self.column_menu.grid(row=0, column=1, padx=(0, 8), sticky="ew")
        self.import_button = t.button(options, "Use column as keywords", self.import_keywords, state="disabled", primary=True)
        self.import_button.grid(row=0, column=2)
        self.status = t.label(self, "Open an .xlsx or .xls file to view data in the app.", muted=True, size=12,
                                    anchor="w", wraplength=600, justify="left")
        self.status.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        table_frame = ctk.CTkFrame(self, corner_radius=0)
        table_frame.grid(row=3, column=0, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        self.table = ttk.Treeview(table_frame, show="headings", selectmode="extended", style="Excel.Treeview")
        self.table.grid(row=0, column=0, sticky="nsew")
        vertical = ctk.CTkScrollbar(table_frame, orientation="vertical", command=self.table.yview,
            fg_color=t.color("surface"), button_color=t.color("hover"), button_hover_color=t.color("border"))
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ctk.CTkScrollbar(table_frame, orientation="horizontal", command=self.table.xview,
            fg_color=t.color("surface"), button_color=t.color("hover"), button_hover_color=t.color("border"))
        horizontal.grid(row=1, column=0, sticky="ew")
        self.table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.empty_label = t.label(table_frame, "No data yet\nOpen an Excel file or scan channels to get started.",
                                    size=14, muted=True, fg_color=t.color("surface"))
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        self.table.bind("<Control-c>", lambda event: (self.copy_selected(), "break")[1])
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        bottom.grid_columnconfigure(1, weight=1)
        self.previous = t.button(bottom, "Previous page", lambda: self._move_page(-1), width=110, state="disabled")
        self.previous.grid(row=0, column=0)
        self.page_label = t.label(bottom, "0 rows", size=12, muted=True)
        self.page_label.grid(row=0, column=1)
        self.next = t.button(bottom, "Next page", lambda: self._move_page(1), width=110, state="disabled")
        self.next.grid(row=0, column=2)
        search_row = ctk.CTkFrame(self, fg_color="transparent")
        search_row.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        search_row.grid_columnconfigure(1, weight=1)
        t.label(search_row, "Search table", size=12, bold=True).grid(row=0, column=0, padx=(0, 8))
        self.search_entry = t.entry(search_row, textvariable=self.search, placeholder_text="Channel name, keyword, views…")
        self.search_entry.grid(row=0, column=1, sticky="ew")
        t.button(search_row, "Copy rows", self.copy_selected, width=120).grid(row=0, column=2, padx=(8, 0))
        self.status.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        table_frame.grid(row=4, column=0, sticky="nsew")
        bottom.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        self.grid_rowconfigure(3, weight=0)
        self.grid_rowconfigure(4, weight=1)
        self.search.trace_add("write", self._search_changed)
        self._apply_table_style()
        self._timer = self.after(100, self._poll)
        self.bind("<Destroy>", self._destroyed, add="+")

    def _destroyed(self, event):
        if event.widget is self:
            self.after_cancel(self._timer)

    def open_file(self, path=None):
        if path is None:
            path = filedialog.askopenfilename(parent=self.winfo_toplevel(), title="Open Excel file",
                                               filetypes=[("Excel", "*.xlsx *.xls")])
        if not path:
            return
        self.path = Path(path)
        self.filename.configure(text=self.path.name)
        self._load()

    def _select_sheet(self, sheet):
        self._load(sheet)

    def _load(self, sheet=None):
        self.request_id += 1
        request_id, path = self.request_id, self.path
        self.status.configure(text="Reading Excel…")
        self.sheet_menu.configure(state="disabled")
        self.column_menu.configure(state="disabled")
        self.import_button.configure(state="disabled")
        self.previous.configure(state="disabled")
        self.next.configure(state="disabled")
        self.data = pd.DataFrame()
        self._sort_column = None
        self.search.set("")
        self.table.delete(*self.table.get_children())
        self.table.configure(columns=())
        self.page_label.configure(text="Reading…")
        self.empty_label.configure(text="Reading workbook…")
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")

        def read():
            try:
                with pd.ExcelFile(path) as workbook:
                    sheets = workbook.sheet_names
                    selected = sheet if sheet is not None else sheets[0]
                    data = workbook.parse(selected)
                self.events.put((request_id, (sheets, selected, data), None))
            except Exception as error:
                self.events.put((request_id, None, str(error)))
        threading.Thread(target=read, daemon=True).start()

    def _poll(self):
        try:
            while True:
                request_id, result, error = self.events.get_nowait()
                if request_id != self.request_id:
                    continue
                if error:
                    self.status.configure(text="Unable to read the file. Select a valid Excel file.")
                    self.page_label.configure(text="0 rows")
                    self.empty_label.configure(text="Unable to read the Excel file.\nOpen a valid file.")
                    messagebox.showerror("Excel read error", error, parent=self.winfo_toplevel())
                    continue
                sheets, selected, self.data = result
                self.sheet_menu.configure(values=sheets, state="normal")
                self.sheet_menu.set(selected)
                self.column_names = [f"{index + 1}. {name}" for index, name in enumerate(self.data.columns)]
                self.column_menu.configure(values=self.column_names or ["No columns"],
                                             state="normal" if self.column_names else "disabled")
                default = next((index for index, name in enumerate(self.data.columns)
                                if str(name).strip().casefold() == "keyword"), 0)
                self.column_menu.set(self.column_names[default] if self.column_names else "No columns")
                self.import_button.configure(state="normal" if len(self.data) and self.column_names else "disabled")
                self.page = 0
                self._render()
        except queue.Empty:
            pass
        self._timer = self.after(100, self._poll)

    def _move_page(self, change):
        self.page = max(0, min(self.page + change, max(0, math.ceil(len(self._display_data()) / self.PAGE_SIZE) - 1)))
        self._render()

    def _search_changed(self, *args):
        if self._search_timer:
            self.after_cancel(self._search_timer)
        self._search_timer = self.after(180, self._apply_search)

    def _apply_search(self):
        self._search_timer = None
        self.page = 0
        self._render()

    def _display_data(self):
        data = self.data
        query = self.search.get().strip()
        if query and not data.empty:
            mask = data.fillna("").astype(str).apply(lambda column: column.str.contains(query, case=False, regex=False)).any(axis=1)
            data = data.loc[mask]
        if self._sort_column is not None and not data.empty:
            column = data.columns[self._sort_column]
            try:
                data = data.sort_values(column, ascending=self._sort_ascending, kind="stable", na_position="last")
            except TypeError:
                data = data.sort_values(column, ascending=self._sort_ascending, kind="stable", key=lambda series: series.astype(str).str.casefold())
        return data

    def _sort(self, index):
        self._sort_ascending = not self._sort_ascending if self._sort_column == index else True
        self._sort_column = index
        self.page = 0
        self._render()

    def copy_selected(self):
        rows = [self.table.item(item, "values") for item in self.table.selection()]
        if not rows:
            self.status.configure(text="Select one or more table rows before copying.")
            return
        self.clipboard_clear()
        self.clipboard_append("\n".join("\t".join(row) for row in rows))
        self.status.configure(text=f"Copied {len(rows)} rows. Paste them into Excel or another document.")

    def _set_appearance_mode(self, mode_string):
        super()._set_appearance_mode(mode_string)
        if hasattr(self, "table"):
            self._apply_table_style()

    def _apply_table_style(self):
        style = ttk.Style(self)
        if style.theme_use() != "clam":
            style.theme_use("clam")
        background, foreground = t.resolved("surface"), t.resolved("text")
        style.configure("Excel.Treeview", background=background, foreground=foreground,
                        fieldbackground=background, rowheight=32, borderwidth=0, relief="flat",
                        bordercolor=t.resolved("border"), lightcolor=background, darkcolor=background,
                        font=("Segoe UI", 11))
        style.configure("Excel.Treeview.Heading", background=t.resolved("inset"), foreground=foreground,
                        bordercolor=t.resolved("border"), lightcolor=t.resolved("inset"),
                        darkcolor=t.resolved("inset"), relief="flat", padding=(10, 10), font=("Segoe UI", 10, "bold"))
        style.map("Excel.Treeview", background=[("selected", t.resolved("selection"))], foreground=[("selected", foreground)])
        style.map("Excel.Treeview.Heading", background=[("active", t.resolved("hover"))])
        self.table.tag_configure("stripe", background=t.resolved("inset"))

    def _render(self):
        self._apply_table_style()
        self.table.delete(*self.table.get_children())
        columns = [f"column_{i}" for i in range(len(self.data.columns))]
        self.table.configure(columns=columns)
        for key, name in zip(columns, self.data.columns):
            index = columns.index(key)
            suffix = (" ↑" if self._sort_ascending else " ↓") if self._sort_column == index else ""
            self.table.heading(key, text=str(name) + suffix, command=lambda column=index: self._sort(column))
            self.table.column(key, width=170, minwidth=90, stretch=False)
        start = self.page * self.PAGE_SIZE
        data = self._display_data()
        for index, row in enumerate(data.iloc[start:start + self.PAGE_SIZE].itertuples(index=False, name=None)):
            self.table.insert("", "end", values=["" if pd.isna(value) else str(value) for value in row], tags=("stripe",) if index % 2 else ())
        total = len(data)
        if total:
            self.empty_label.place_forget()
        else:
            self.empty_label.configure(text="No matching rows.\nTry another search term or select a different sheet.")
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        pages = max(1, math.ceil(total / self.PAGE_SIZE))
        self.status.configure(text=f"{total:,} / {len(self.data):,} rows · {len(columns)} columns · Click a column header to sort. Keyword import always uses the entire column.")
        self.page_label.configure(text=f"Page {self.page + 1}/{pages} · {total:,} rows")
        self.previous.configure(state="normal" if self.page else "disabled")
        self.next.configure(state="normal" if self.page + 1 < pages else "disabled")

    def import_keywords(self):
        if not self.column_names or self.data.empty:
            return
        column = self.column_names.index(self.column_menu.get())
        keywords = list(dict.fromkeys(str(value).strip() for value in self.data.iloc[:, column].dropna()
                                      if str(value).strip()))
        if not keywords:
            messagebox.showinfo("Import keywords", "This column contains no keywords.", parent=self.winfo_toplevel())
            return
        if not messagebox.askyesno("Import keywords", f"Replace the current keyword list with {len(keywords)} keywords from this column?",
                                   parent=self.winfo_toplevel()):
            return
        self.on_import(keywords, str(self.path))
