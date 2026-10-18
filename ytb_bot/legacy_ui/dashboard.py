"""Creator Studio view: presentation, local interaction and progress feedback."""
import os
import tkinter as tk
import customtkinter as ctk

from ytb_bot.legacy_ui import theme as t
from ytb_bot.legacy_ui.excel_viewer import ExcelViewer
from ytb_bot.version import APP_VERSION
from ytb_bot.build_info import build_id


def system_motion_enabled():
    if os.name == "nt":
        import ctypes
        enabled = ctypes.c_int(1)
        if ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0):
            return bool(enabled.value)
    return True


class StudioDashboard(ctk.CTkFrame):
    def __init__(self, master, compact, on_scan, on_stop, on_excel, on_results, on_update, on_import):
        super().__init__(master, fg_color=t.color("canvas"), corner_radius=0)
        self.compact = compact
        self.motion = tk.BooleanVar(self, value=system_motion_enabled())
        self._progress = 0
        self._animation = None
        self._count_timer = None
        self._sidebar_visible = True
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar(on_update)
        self.main_frame = ctk.CTkScrollableFrame(self, fg_color="transparent",
            scrollbar_button_color=t.color("hover"), scrollbar_button_hover_color=t.color("border"))
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=16 if compact else 24, pady=16)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)
        header = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        header.grid_columnconfigure(0, weight=1)
        t.label(header, "DISCOVERY WORKSPACE", size=11, bold=True, muted=True).grid(row=0, column=0, sticky="w")
        t.label(header, "Find new channels. Discover trends.", size=23 if compact else 27, bold=True).grid(
            row=1, column=0, sticky="w", pady=(3, 4))
        t.label(header, "Turn keywords into your next creative opportunity.", muted=True).grid(row=2, column=0, sticky="w")
        self.state_badge = t.label(header, "READY", size=11, bold=True,
                                   fg_color=t.color("inset"), corner_radius=12, width=112, height=30)
        self.state_badge.grid(row=0, column=1, padx=(12, 0), sticky="e")
        self.sidebar_toggle = t.button(header, "Show filters", self.toggle_sidebar, width=125)
        self.sidebar_toggle.grid(row=2, column=1, padx=(12, 0))

        stats = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        stats.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        stats.grid_columnconfigure((0, 1, 2), weight=1, uniform="stats")
        self.stat_values = {}
        for index, (key, title, value, note) in enumerate([
            ("keywords", "KEYWORDS", "0", "Topics to explore"),
            ("matches", "MATCHING CHANNELS", "0", "Match the current filters"),
            ("completed", "PROCESSED", "0 / 0", "Scan progress")]):
            card = ctk.CTkFrame(stats, fg_color=t.color("surface"), corner_radius=14,
                               border_width=1, border_color=t.color("border"))
            card.grid(row=0, column=index, sticky="nsew", padx=(0 if index == 0 else 6, 0 if index == 2 else 6))
            t.label(card, title, size=10, bold=True, muted=True).pack(anchor="w", padx=16, pady=(12, 0))
            self.stat_values[key] = t.label(card, value, size=26, bold=True)
            self.stat_values[key].pack(anchor="w", padx=16)
            t.label(card, note, size=11, muted=True).pack(anchor="w", padx=16, pady=(0, 12))

        self.content_tabs = ctk.CTkTabview(self.main_frame, height=570, corner_radius=16,
            fg_color=t.color("surface"), segmented_button_fg_color=t.color("inset"),
            segmented_button_selected_color=("#F6CED6", "#B92F43"),
            segmented_button_selected_hover_color=("#F0B9C5", "#9F2336"),
            segmented_button_unselected_color=t.color("inset"), segmented_button_unselected_hover_color=t.color("hover"),
            text_color=t.color("text"))
        self.content_tabs.grid(row=2, column=0, sticky="nsew")
        scan = self.content_tabs.add("Activity")
        excel = self.content_tabs.add("Excel")
        for tab in (scan, excel):
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
        self.excel_viewer = ExcelViewer(excel, on_import=on_import)
        self.excel_viewer.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        body = ctk.CTkFrame(scan, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew", padx=12, pady=8)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(5, weight=1)
        kw_header = ctk.CTkFrame(body, fg_color="transparent")
        kw_header.grid(row=0, column=0, sticky="ew")
        kw_header.grid_columnconfigure(0, weight=1)
        t.label(kw_header, "Which topics would you like to explore?", size=16, bold=True).grid(row=0, column=0, sticky="w")
        t.button(kw_header, "Import Excel", on_excel, width=115).grid(row=0, column=1, padx=(8, 0))
        self.kw_textbox = ctk.CTkTextbox(body, height=90, corner_radius=10, fg_color=t.color("inset"),
            border_width=1, border_color=t.color("border"), text_color=t.color("text"),
            font=ctk.CTkFont(family="Segoe UI", size=14), wrap="word")
        self.kw_textbox.grid(row=1, column=0, sticky="ew", pady=(10, 8))
        self.kw_textbox.insert("1.0", "AI Automation\nAI Agent\nAI video creation")
        self.kw_textbox.bind("<KeyRelease>", self._keywords_changed, add="+")
        presets = ctk.CTkFrame(body, fg_color="transparent")
        presets.grid(row=2, column=0, sticky="ew")
        for index, (title, words) in enumerate([
            ("AI & Technology", ["AI Automation", "AI Agent", "AI Technology"]),
            ("Content creation", ["YouTube Shorts", "Video editing", "Content creator"])]):
            t.button(presets, title, lambda values=words: self.add_keywords(values), width=140).grid(
                row=0, column=index, padx=(0, 8))
        self.keyword_hint = t.label(presets, "", size=11, muted=True)
        self.keyword_hint.grid(row=0, column=2, sticky="w")

        self.form_error = t.label(body, "", size=12, anchor="w", wraplength=520)
        self.form_error.configure(text_color=t.color("danger"))
        self.form_error.grid(row=3, column=0, sticky="ew", pady=(4, 0))
        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.grid(row=4, column=0, sticky="ew", pady=(4, 16))
        actions.grid_columnconfigure(0, weight=1)
        self.start_btn = t.button(actions, "Start exploring", on_scan, primary=True)
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.stop_btn = t.button(actions, "Stop", on_stop, width=72, state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=(0, 8))
        self.open_output_btn = t.button(actions, "View results", on_results, width=115)
        self.open_output_btn.grid(row=0, column=2)

        activity = ctk.CTkFrame(body, fg_color=t.color("inset"), corner_radius=12)
        activity.grid(row=5, column=0, sticky="nsew")
        activity.grid_columnconfigure(0, weight=1)
        activity.grid_rowconfigure(2, weight=1)
        self.status_label = t.label(activity, "Ready for your first discovery scan", anchor="w", size=12)
        self.status_label.grid(row=0, column=0, padx=14, pady=(12, 8), sticky="ew")
        self.progress_label = t.label(activity, "0%", size=12, bold=True)
        self.progress_label.grid(row=0, column=1, padx=(8, 14), pady=(12, 8))
        self.progress_bar = ctk.CTkProgressBar(activity, height=5, progress_color=t.color("accent"), fg_color=t.color("hover"))
        self.progress_bar.grid(row=1, column=0, columnspan=2, padx=14, sticky="ew")
        self.progress_bar.set(0)
        self.log_box = ctk.CTkTextbox(activity, height=120, fg_color="transparent", state="disabled",
            text_color=t.color("muted"), font=ctk.CTkFont(family="Consolas", size=12), wrap="word")
        self.log_box.grid(row=2, column=0, columnspan=2, padx=8, pady=8, sticky="nsew")
        self.log_box.tag_config("match", foreground=t.resolved("success"))
        self.log_box.tag_config("error", foreground=t.resolved("danger"))
        footer = ctk.CTkFrame(body, fg_color="transparent")
        footer.grid(row=6, column=0, sticky="ew", pady=(8, 0))
        footer.grid_columnconfigure(0, weight=1)
        self.elapsed_label = t.label(footer, "Elapsed: 00:00", size=11, muted=True)
        self.elapsed_label.grid(row=0, column=0, sticky="w")
        t.button(footer, "Clear log", self.clear_log, width=100).grid(row=0, column=1)
        self.refresh_keywords()
        master.bind("<Configure>", self._responsive, add="+")
        self._narrow = None

    def _build_sidebar(self, on_update):
        self.sidebar = ctk.CTkScrollableFrame(self, width=220, fg_color=t.color("sidebar"), corner_radius=0,
            scrollbar_button_color=t.color("hover"), scrollbar_button_hover_color=t.color("border"))
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_columnconfigure(0, weight=1)
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=14, pady=(20, 24))
        mark = t.label(brand, "Y", size=25, bold=True, fg_color=t.color("accent"), corner_radius=12, width=44, height=44)
        mark.configure(text_color="#FFFFFF")
        mark.grid(row=0, column=0, rowspan=2, padx=(0, 10))
        t.label(brand, "YTB-BOT", size=21, bold=True).grid(row=0, column=1, sticky="w")
        t.label(brand, "CREATOR STUDIO", size=10, muted=True).grid(row=1, column=1, sticky="w")
        t.label(self.sidebar, "DISCOVERY FILTERS", size=11, bold=True, muted=True).grid(
            row=1, column=0, padx=14, sticky="w", pady=(0, 12))
        self.field_errors = {}

        def field(row, key, title, value, help_text, masked=False):
            t.label(self.sidebar, title, size=12, bold=True, anchor="w").grid(row=row, column=0, padx=14, sticky="ew", pady=(10, 6))
            control = t.entry(self.sidebar, show="*" if masked else "")
            control.grid(row=row + 1, column=0, padx=14, sticky="ew")
            control.insert(0, value)
            hint = t.label(self.sidebar, help_text, size=11, muted=True, anchor="w", wraplength=195, justify="left")
            hint.grid(row=row + 2, column=0, padx=14, sticky="ew", pady=(4, 0))
            self.field_errors[key] = (control, hint, help_text)
            control.bind("<FocusIn>", lambda event: control.configure(border_color=t.color("blue")))
            control.bind("<FocusOut>", lambda event: control.configure(border_color=t.color("border")))
            return control

        self.api_entry = field(2, "api", "YouTube API Key", os.getenv("YOUTUBE_API_KEY", ""), "Your key is stored only on this computer.", True)
        self.reveal_button = t.button(self.sidebar, "Show API key", self._toggle_key, width=120)
        self.reveal_button.grid(row=5, column=0, padx=14, pady=(6, 0), sticky="ew")
        self.max_age_entry = field(6, "age", "Maximum channel age (days)", "90", "Only include channels created within this period.")
        self.min_views_entry = field(9, "views", "Minimum total views", "500", "Cumulative views across the channel.")
        self.pages_label = t.label(self.sidebar, "Depth: 2 pages / keyword", size=12, bold=True, anchor="w")
        self.pages_label.grid(row=12, column=0, padx=14, pady=(18, 10), sticky="ew")
        self.max_pages_slider = ctk.CTkSlider(self.sidebar, from_=1, to=5, number_of_steps=4,
            progress_color=t.color("accent"), button_color=t.color("accent"), button_hover_color=t.color("accent_hover"),
            command=lambda value: self.pages_label.configure(text=f"Depth: {int(value)} pages / keyword"))
        self.max_pages_slider.grid(row=13, column=0, padx=14, sticky="ew")
        self.max_pages_slider.set(2)
        t.label(self.sidebar, "Each page finds up to 50 videos.\nDeeper scans use more quota.", size=11,
                muted=True, anchor="w", justify="left", wraplength=195).grid(row=14, column=0, padx=14, pady=(8, 22), sticky="ew")
        t.label(self.sidebar, "PERSONALIZATION", size=11, bold=True, muted=True).grid(row=15, column=0, padx=14, sticky="w")
        self.theme_switch = ctk.CTkOptionMenu(self.sidebar, values=["Dark", "Light", "System"], height=36,
            fg_color=t.color("inset"), button_color=t.color("hover"), button_hover_color=t.color("border"),
            text_color=t.color("text"), command=self.change_theme)
        self.theme_switch.grid(row=16, column=0, padx=14, pady=(10, 12), sticky="ew")
        self.motion_switch = ctk.CTkSwitch(self.sidebar, text="Motion effects", variable=self.motion,
            progress_color=t.color("accent"), text_color=t.color("text"), font=ctk.CTkFont(size=11),
            command=self._motion_changed)
        self.motion_switch.grid(row=17, column=0, padx=14, pady=(0, 22), sticky="ew")
        self.update_label = t.label(self.sidebar, f"v{APP_VERSION}\nBuild: {build_id()}", size=11, muted=True, wraplength=190, justify="left")
        self.update_label.grid(row=18, column=0, padx=14, sticky="ew")
        self.update_button = t.button(self.sidebar, "Check for updates", on_update)
        self.update_button.grid(row=19, column=0, padx=14, pady=(10, 20), sticky="ew")

    def _responsive(self, event):
        if event.widget is not self.winfo_toplevel():
            return
        narrow = event.width / self._get_widget_scaling() < 1030
        if narrow != self._narrow:
            self._narrow = narrow
            if narrow:
                self._set_sidebar_visible(False)
            else:
                self._set_sidebar_visible(True)
            if narrow:
                self.sidebar_toggle.grid()
            else:
                self.sidebar_toggle.grid_remove()

    def toggle_sidebar(self):
        self._set_sidebar_visible(not self._sidebar_visible)

    def _set_sidebar_visible(self, visible):
        if visible:
            self.sidebar.grid()
        else:
            self.sidebar.grid_remove()
        self._sidebar_visible = visible
        self.sidebar_toggle.configure(text="Hide filters" if visible else "Show filters")

    def _toggle_key(self):
        reveal = self.api_entry.cget("show") == "*"
        self.api_entry.configure(show="" if reveal else "*")
        self.reveal_button.configure(text="Hide API key" if reveal else "Show API key")

    def change_theme(self, value):
        ctk.set_appearance_mode({"Dark": "Dark", "Light": "Light", "System": "System"}[value])
        self.log_box.tag_config("match", foreground=t.resolved("success"))
        self.log_box.tag_config("error", foreground=t.resolved("danger"))

    def _keywords_changed(self, event=None):
        if self._count_timer:
            self.after_cancel(self._count_timer)
        self._count_timer = self.after(140, self.refresh_keywords)

    def refresh_keywords(self):
        self._count_timer = None
        count = len(self.keywords())
        self.stat_values["keywords"].configure(text=str(count))
        self.keyword_hint.configure(text=f"{count} keywords\nOne topic per line")

    def keywords(self):
        return list(dict.fromkeys(line.strip() for line in self.kw_textbox.get("1.0", "end").splitlines() if line.strip()))

    def add_keywords(self, words):
        values = list(dict.fromkeys(self.keywords() + words))
        self.kw_textbox.delete("1.0", "end")
        self.kw_textbox.insert("1.0", "\n".join(values))
        self.refresh_keywords()

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def clear_errors(self):
        self.form_error.configure(text="")
        for control, hint, help_text in self.field_errors.values():
            control.configure(border_color=t.color("border"))
            hint.configure(text=help_text, text_color=t.color("muted"))
        self.kw_textbox.configure(border_color=t.color("border"))

    def show_error(self, key, message):
        self.form_error.configure(text=message)
        if key in self.field_errors:
            control, hint, _ = self.field_errors[key]
            control.configure(border_color=t.color("danger"))
            hint.configure(text=message, text_color=t.color("danger"))
            if not self._sidebar_visible:
                self.toggle_sidebar()
            control.focus_set()
        else:
            self.kw_textbox.configure(border_color=t.color("danger"))
            self.kw_textbox.focus_set()

    def _motion_changed(self):
        if self._animation:
            self.after_cancel(self._animation)
            self._animation = None
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(self._progress)

    def set_progress(self, fraction):
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_label.configure(text=f"{fraction:.0%}")
        if self._animation:
            self.after_cancel(self._animation)
        start = self._progress
        self._progress = fraction
        def step(index=1):
            eased = 1 - (1 - index / 10) ** 3
            self.progress_bar.set(start + (fraction - start) * eased)
            self._animation = self.after(18, step, index + 1) if index < 10 else None
        if self.motion.get():
            step()
        else:
            self.progress_bar.set(fraction)
