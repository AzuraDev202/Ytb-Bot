"""Embedded, paginated Excel preview and keyword-column import."""
import math
from pathlib import Path
import queue
import threading
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
import pandas as pd


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
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(top, text="Mở file Excel", width=125, command=self.open_file).grid(row=0, column=0)
        self.filename = ctk.CTkLabel(top, text="Chưa mở file Excel", anchor="w")
        self.filename.grid(row=0, column=1, padx=12, sticky="ew")

        options = ctk.CTkFrame(self, fg_color="transparent")
        options.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        options.grid_columnconfigure((0, 1), weight=1)
        self.sheet_menu = ctk.CTkOptionMenu(options, values=["Chọn sheet"], state="disabled",
                                           command=self._select_sheet, dynamic_resizing=False)
        self.sheet_menu.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self.column_menu = ctk.CTkOptionMenu(options, values=["Chọn cột từ khóa"], state="disabled",
                                            dynamic_resizing=False)
        self.column_menu.grid(row=0, column=1, padx=(0, 8), sticky="ew")
        self.import_button = ctk.CTkButton(options, text="Dùng cột làm từ khóa", state="disabled",
                                           command=self.import_keywords)
        self.import_button.grid(row=0, column=2)
        self.status = ctk.CTkLabel(self, text="Mở .xlsx hoặc .xls để xem dữ liệu ngay trong app.",
                                    anchor="w", wraplength=600, justify="left")
        self.status.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        table_frame = ctk.CTkFrame(self, corner_radius=0)
        table_frame.grid(row=3, column=0, sticky="nsew")
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        self.table = ttk.Treeview(table_frame, show="headings", selectmode="extended", style="Excel.Treeview")
        self.table.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(table_frame, orient="horizontal", command=self.table.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        bottom.grid_columnconfigure(1, weight=1)
        self.previous = ctk.CTkButton(bottom, text="Trang trước", width=110, state="disabled",
                                        command=lambda: self._move_page(-1))
        self.previous.grid(row=0, column=0)
        self.page_label = ctk.CTkLabel(bottom, text="0 dòng")
        self.page_label.grid(row=0, column=1)
        self.next = ctk.CTkButton(bottom, text="Trang sau", width=110, state="disabled",
                                    command=lambda: self._move_page(1))
        self.next.grid(row=0, column=2)
        self._timer = self.after(100, self._poll)
        self.bind("<Destroy>", self._destroyed, add="+")

    def _destroyed(self, event):
        if event.widget is self:
            self.after_cancel(self._timer)

    def open_file(self, path=None):
        if path is None:
            path = filedialog.askopenfilename(parent=self.winfo_toplevel(), title="Mở file Excel",
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
        self.status.configure(text="Đang đọc Excel…")
        self.sheet_menu.configure(state="disabled")
        self.column_menu.configure(state="disabled")
        self.import_button.configure(state="disabled")
        self.previous.configure(state="disabled")
        self.next.configure(state="disabled")
        self.data = pd.DataFrame()
        self.table.delete(*self.table.get_children())
        self.table.configure(columns=())
        self.page_label.configure(text="Đang đọc…")

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
                    self.status.configure(text="Không đọc được file. Hãy chọn lại file Excel hợp lệ.")
                    self.page_label.configure(text="0 dòng")
                    messagebox.showerror("Lỗi đọc Excel", error, parent=self.winfo_toplevel())
                    continue
                sheets, selected, self.data = result
                self.sheet_menu.configure(values=sheets, state="normal")
                self.sheet_menu.set(selected)
                self.column_names = [f"{index + 1}. {name}" for index, name in enumerate(self.data.columns)]
                self.column_menu.configure(values=self.column_names or ["Không có cột"],
                                             state="normal" if self.column_names else "disabled")
                default = next((index for index, name in enumerate(self.data.columns)
                                if str(name).strip().casefold() == "keyword"), 0)
                self.column_menu.set(self.column_names[default] if self.column_names else "Không có cột")
                self.import_button.configure(state="normal" if len(self.data) and self.column_names else "disabled")
                self.page = 0
                self._render()
        except queue.Empty:
            pass
        self._timer = self.after(100, self._poll)

    def _move_page(self, change):
        self.page += change
        self._render()

    def _set_appearance_mode(self, mode_string):
        super()._set_appearance_mode(mode_string)
        if hasattr(self, "table"):
            self._apply_table_style()

    def _apply_table_style(self):
        style = ttk.Style(self)
        dark = ctk.get_appearance_mode() == "Dark"
        background, foreground = ("#182233", "#e2e8f0") if dark else ("#ffffff", "#1e293b")
        style.configure("Excel.Treeview", background=background, foreground=foreground,
                        fieldbackground=background, rowheight=28, font=("Segoe UI", 11))
        style.configure("Excel.Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _render(self):
        self._apply_table_style()
        self.table.delete(*self.table.get_children())
        columns = [f"column_{i}" for i in range(len(self.data.columns))]
        self.table.configure(columns=columns)
        for key, name in zip(columns, self.data.columns):
            self.table.heading(key, text=str(name))
            self.table.column(key, width=170, minwidth=90, stretch=False)
        start = self.page * self.PAGE_SIZE
        for row in self.data.iloc[start:start + self.PAGE_SIZE].itertuples(index=False, name=None):
            self.table.insert("", "end", values=["" if pd.isna(value) else str(value) for value in row])
        total = len(self.data)
        pages = max(1, math.ceil(total / self.PAGE_SIZE))
        self.status.configure(text=f"{total:,} dòng · {len(columns)} cột. Chọn cột để nhập toàn bộ từ khóa; bảng chỉ dùng để xem.")
        self.page_label.configure(text=f"Trang {self.page + 1}/{pages} · {total:,} dòng")
        self.previous.configure(state="normal" if self.page else "disabled")
        self.next.configure(state="normal" if self.page + 1 < pages else "disabled")

    def import_keywords(self):
        if not self.column_names or self.data.empty:
            return
        column = self.column_names.index(self.column_menu.get())
        keywords = list(dict.fromkeys(str(value).strip() for value in self.data.iloc[:, column].dropna()
                                      if str(value).strip()))
        if not keywords:
            messagebox.showinfo("Nhập từ khóa", "Cột này không chứa từ khóa.", parent=self.winfo_toplevel())
            return
        if not messagebox.askyesno("Nhập từ khóa", f"Thay danh sách từ khóa hiện tại bằng {len(keywords)} từ khóa từ cột này?",
                                   parent=self.winfo_toplevel()):
            return
        self.on_import(keywords, str(self.path))
