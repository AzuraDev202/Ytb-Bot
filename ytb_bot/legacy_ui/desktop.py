import os
import threading
import datetime
import queue
import sys
import time
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import pandas as pd
import httplib2
from dotenv import load_dotenv, set_key
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ytb_bot.version import APP_VERSION
from ytb_bot.core.contacts import extract_contacts
from ytb_bot.core.excel import write_results_excel
from ytb_bot.build_info import build_id
from ytb_bot.updater import check_for_update, download_update, install_update
from ytb_bot.paths import APP_DIR, ENV_FILE
from ytb_bot.legacy_ui.dashboard import StudioDashboard
from ytb_bot.legacy_ui import theme as t
from ytb_bot.legacy_ui.window_layout import fit_window, screen_work_area

# Shared interface settings
ctk.set_appearance_mode("Dark")  # "Dark", "Light", or "System"
ctk.set_default_color_theme("blue")

load_dotenv(ENV_FILE)
if not os.path.exists(ENV_FILE):
    load_dotenv(".env")  # Read the legacy working-directory settings on first launch.


class YtbBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()

        self.title(f"Ytb-Bot · v{APP_VERSION} · {build_id()}")
        self._startup_layout = fit_window(screen_work_area(self), self._get_window_scaling(),
                                           frame=(round(20 * self._get_window_scaling()),
                                                  round(44 * self._get_window_scaling())))
        layout = self._startup_layout
        self._compact = layout.compact
        self.minsize(min(900, layout.width), min(580, layout.height))
        self.geometry(f"{layout.width}x{layout.height}+{layout.x}+{layout.y}")

        self.excel_keyword_path = ""
        self.is_scanning = False
        self.update_busy = False
        self.is_installing = False
        self.available_release = None
        self.ui_events = queue.Queue()
        self.stop_requested = threading.Event()
        self._scan_outcome = "ready"
        self._scan_started = None

        # Main layout: sidebar on the left, main content on the right
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.configure(fg_color=t.color("canvas"))
        self.view = StudioDashboard(self, compact=self._compact,
            on_scan=self.start_scan_thread, on_stop=self.stop_scan,
            on_excel=self.load_keywords_excel, on_results=self.open_output_excel,
            on_update=self.update_action, on_import=self._import_excel_keywords)
        self.view.grid(row=0, column=0, sticky="nsew")
        self.log("Choose topics and filters, then start exploring. Ctrl+Enter to scan · Ctrl+O to open Excel.")
        self.bind("<Control-Return>", lambda event: (self.start_scan_thread(), "break")[1])
        self.bind("<Control-o>", lambda event: (self.load_keywords_excel(), "break")[1])
        self.bind("<Escape>", lambda event: self.stop_scan())
        self.protocol("WM_DELETE_WINDOW", self._close_window)
        self.update_idletasks()
        # CTk refreshes the Windows titlebar on the first mainloop(). Reveal
        # after that initialization, so it cannot restore the withdrawn state.
        self.after(0, self._show_window)
        self.after(100, self._process_ui_events)
        self.after(2000, self.check_updates)
        self.after(6 * 60 * 60 * 1000, self._scheduled_update_check)

    def _show_window(self):
        # CTk's titlebar setup itself pumps pending events with update(). An
        # after(0) callback can therefore run before the first mainloop is ready.
        # Wait for CTk's initialization flag; do not mutate its internal flags.
        if not self._window_exists:
            self.after(10, self._show_window)
            return
        self.deiconify()
        self.lift()

    def _process_ui_events(self):
        try:
            for _ in range(60):
                callback, args = self.ui_events.get_nowait()
                callback(*args)
        except queue.Empty:
            pass
        self.after(50, self._process_ui_events)

    def _scheduled_update_check(self):
        self.check_updates()
        self.after(6 * 60 * 60 * 1000, self._scheduled_update_check)

    def check_updates(self):
        if self.update_busy:
            return
        self.update_busy = True
        self.view.update_button.configure(state="disabled")
        self.view.update_label.configure(text="Checking version…")
        def work():
            try:
                release = check_for_update()
                self.ui_events.put((self._update_checked, (release, None)))
            except Exception as error:
                self.ui_events.put((self._update_checked, (None, str(error))))
        threading.Thread(target=work, daemon=True).start()

    def _update_checked(self, release, error):
        self.update_busy = False
        self.available_release = release
        self.view.update_button.configure(state="normal", text="Update now" if release else "Check for updates")
        if error:
            self.view.update_label.configure(text="Unable to check for updates")
            self.log(f"[Update] {error}")
        elif release:
            self.view.update_label.configure(text=f"Update available: v{release.version}")
            self.log(f"[Update] A new build of v{release.version} is available. Select Update now to download and restart.")
        else:
            self.view.update_label.configure(text=f"v{APP_VERSION}\nBuild: {build_id()}")

    def update_action(self):
        if not self.available_release:
            self.check_updates()
            return
        if self.is_scanning:
            messagebox.showinfo("Update", "Wait for the scan to finish before updating.")
            return
        if not getattr(sys, "frozen", False):
            messagebox.showinfo("Update", "Automatic updates are available for the EXE. Update source installations through Git.")
            return
        release = self.available_release
        if not messagebox.askyesno("Update Ytb-Bot", f"Download v{release.version} and restart the app?\nYour API key and Excel files will be preserved."):
            return
        self.update_busy = True
        self.view.start_btn.configure(state="disabled")
        self.is_installing = True
        self.view.update_button.configure(state="disabled")
        def work():
            try:
                staged = download_update(release, lambda fraction: self.ui_events.put(
                    (self._download_progress, (fraction,))))
                self.ui_events.put((self._install_download, (staged,)))
            except Exception as error:
                self.ui_events.put((self._update_failed, (str(error),)))
        threading.Thread(target=work, daemon=True).start()

    def _download_progress(self, fraction):
        self.view.update_label.configure(text=f"Downloading update… {fraction:.0%}")

    def _install_download(self, staged):
        try:
            install_update(staged)
        except Exception as error:
            staged.unlink(missing_ok=True)
            self._update_failed(str(error))
            return
        self.destroy()

    def _update_failed(self, error):
        self.update_busy = False
        self.is_installing = False
        self.view.start_btn.configure(state="normal")
        self.view.update_button.configure(state="normal")
        self.view.update_label.configure(text="Update failed · try again")
        messagebox.showerror("Update", error)

    def log(self, message):
        if threading.current_thread() is not threading.main_thread():
            self.ui_events.put((self.log, (message,)))
            return
        self.view.log_box.configure(state="normal")
        tag = "error" if "[!]" in message else "match" if "[+]" in message or "MATCH:" in message else ""
        self.view.log_box.insert(tk.END, message + "\n", tag)
        self.view.log_box.see(tk.END)
        self.view.log_box.configure(state="disabled")

    def load_keywords_excel(self):
        self.view.content_tabs.set("Excel")
        self.view.excel_viewer.open_file()

    def _import_excel_keywords(self, keywords, file_path):
        self.excel_keyword_path = file_path
        self.view.kw_textbox.delete("0.0", tk.END)
        self.view.kw_textbox.insert("0.0", "\n".join(keywords))
        self.view.refresh_keywords()
        self.log(f"[+] Loaded {len(keywords)} keywords from file: {os.path.basename(file_path)}")
        self.view.excel_viewer.status.configure(text=f"Imported {len(keywords)} keywords into the list above.")

    def open_output_excel(self):
        output_file = str(APP_DIR / "channel_results.xlsx")
        if os.path.exists(output_file):
            self._show_excel(output_file)
        else:
            messagebox.showinfo("Notice", "No results file yet. Run a channel scan first!")

    def _show_excel(self, path):
        self.view.content_tabs.set("Excel")
        self.view.excel_viewer.open_file(path)

    def start_scan_thread(self):
        if self.is_scanning or self.is_installing:
            return
        self.view.clear_errors()
        self.view.content_tabs.set("Activity")
        api_key = self.view.api_entry.get().strip()
        if not api_key:
            self.view.show_error("api", "Enter a YouTube API key to start.")
            return
        keywords = self.view.keywords()
        if not keywords:
            self.view.show_error("keywords", "Add at least one keyword; one topic per line.")
            return
        values = {}
        for key, control, minimum, title in [
            ("age", self.view.max_age_entry, 1, "Channel age"),
            ("views", self.view.min_views_entry, 0, "Views")]:
            try:
                values[key] = int(control.get().strip())
                if values[key] < minimum:
                    raise ValueError
            except ValueError:
                self.view.show_error(key, f"{title} must be an integer of at least {minimum}.")
                return
        max_days, min_views = values["age"], values["views"]
        max_pages = int(self.view.max_pages_slider.get())
        try:
            set_key(ENV_FILE, "YOUTUBE_API_KEY", api_key)
        except OSError:
            self.view.show_error("api", "Unable to save the API key. Check write permissions for the app folder.")
            return
        self.is_scanning = True
        self.stop_requested.clear()
        self._scan_outcome = "success"
        self._scan_started = time.monotonic()
        self.view.content_tabs.set("Activity")
        self.view.start_btn.configure(state="disabled", text="Scanning…")
        self.view.stop_btn.configure(state="normal", text="Stop")
        self.view.set_progress(0)
        if self.view.motion.get():
            self.view.progress_bar.configure(mode="indeterminate")
            self.view.progress_bar.start()
        self.view.state_badge.configure(text="EXPLORING", text_color=t.color("blue"))
        self.view.stat_values["matches"].configure(text="0")
        self.view.stat_values["completed"].configure(text=f"0 / {len(keywords)}")
        self.view.refresh_keywords()
        self.view.clear_log()
        self.view.status_label.configure(text="Starting scan…")
        self._tick_elapsed()

        thread = threading.Thread(
            target=self.run_scanner,
            args=(api_key, keywords, max_days, min_views, max_pages),
            daemon=True
        )
        thread.start()

    def stop_scan(self):
        if self.is_scanning and not self.stop_requested.is_set():
            self.stop_requested.set()
            self.view.stop_btn.configure(state="disabled", text="Stopping")
            self.view.status_label.configure(text="Stopping after the current request; discovered channels will be saved…")
            self.log("[*] Stop requested. The app will save discovered results.")

    def _tick_elapsed(self):
        if self._scan_started is None:
            return
        elapsed = int(time.monotonic() - self._scan_started)
        self.view.elapsed_label.configure(text=f"Elapsed: {elapsed // 60:02d}:{elapsed % 60:02d}")
        if self.is_scanning:
            self.after(500, self._tick_elapsed)

    def _close_window(self):
        if self.is_scanning and not messagebox.askyesno("Close YTB-BOT", "The app is scanning. Closing now may lose unsaved results. Close anyway?"):
            return
        self.stop_requested.set()
        self.destroy()

    def run_scanner(self, api_key, keywords, max_days, min_views, max_pages):
        collected_channels = {}
        try:
            youtube = build("youtube", "v3", developerKey=api_key, http=httplib2.Http(timeout=20))
            cutoff_date = (
                datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=max_days)
            ).strftime('%Y-%m-%dT%H:%M:%SZ')

            total_kw = len(keywords)

            for idx, kw in enumerate(keywords, 1):
                if self.stop_requested.is_set():
                    break
                self.log(f"\n==========================================")
                self.log(f"[*] ({idx}/{total_kw}) Scanning keyword: '{kw}'...")
                video_map = {}
                next_page_token = None

                for _ in range(max_pages):
                    if self.stop_requested.is_set():
                        break
                    search_res = youtube.search().list(
                        q=kw,
                        part="snippet",
                        type="video",
                        order="date",
                        publishedAfter=cutoff_date,
                        maxResults=50,
                        pageToken=next_page_token
                    ).execute()

                    for item in search_res.get("items", []):
                        ch_id = item["snippet"]["channelId"]
                        if ch_id not in video_map:
                            video_map[ch_id] = item["snippet"]["title"]

                    next_page_token = search_res.get("nextPageToken")
                    if not next_page_token:
                        break

                self.log(f" -> Found {len(video_map)} channels with new videos. Checking channel ages...")

                ch_ids = list(video_map.keys())
                for i in range(0, len(ch_ids), 50):
                    if self.stop_requested.is_set():
                        break
                    batch_ids = ch_ids[i:i+50]
                    ch_res = youtube.channels().list(
                        part="snippet,statistics",
                        id=",".join(batch_ids)
                    ).execute()

                    for item in ch_res.get("items", []):
                        ch_id = item["id"]
                        if ch_id in collected_channels:
                            continue

                        snippet = item.get("snippet", {})
                        stats = item.get("statistics", {})
                        created_at = snippet.get("publishedAt", "")
                        if not created_at:
                            continue

                        created_dt = datetime.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        age_days = (datetime.datetime.now(datetime.timezone.utc) - created_dt).days
                        total_views = int(stats.get("viewCount", 0))

                        contacts = extract_contacts(snippet.get("description", ""))
                        if age_days <= max_days and total_views >= min_views and contacts:
                            collected_channels[ch_id] = {
                                "Channel Name": snippet.get("title"),
                                "Channel ID": ch_id,
                                "Channel URL": f"https://www.youtube.com/channel/{ch_id}",
                                "Search Keyword": kw,
                                "Created Date": created_at[:10],
                                "Channel Age (Days)": age_days,
                                "Subscribers": int(stats.get("subscriberCount", 0)) if not stats.get("hiddenSubscriberCount", False) else "Hidden",
                                "Total Views": total_views,
                                "Total Videos": int(stats.get("videoCount", 0)),
                                "Latest Video": video_map[ch_id], **contacts
                            }
                            self.log(f"    [+] MATCH: {snippet.get('title')} ({age_days} days) - {total_views:,} views")
                            self.ui_events.put((self._scan_match_count, (len(collected_channels),)))

                if not self.stop_requested.is_set():
                    self.ui_events.put((self._scan_progress, (idx, total_kw)))

        except HttpError as err:
            detail = str(err).replace(api_key, "<API_KEY>")
            self.log(f"\n[!] YouTube API error: {detail}")
            self.ui_events.put((self._scan_failed, ("YouTube API returned an error. Check the API key, quota, and network connection.",)))
        except Exception as e:
            self.log(f"\n[!] System error: {str(e).replace(api_key, '<API_KEY>')}")
            self.ui_events.put((self._scan_failed, ("The scan failed. See the log for details.",)))
        finally:
            try:
                if collected_channels:
                    results = list(collected_channels.values())
                    df = pd.DataFrame(results)
                    df.sort_values(by="Total Views", ascending=False, inplace=True)
                    df.insert(0, "No.", range(1, len(df) + 1))

                    output_excel = str(APP_DIR / "channel_results.xlsx")
                    write_results_excel(df, output_excel, "Results")

                    self.log(f"\n[+] Saved {len(results)} channels to '{output_excel}'.")
                    self.ui_events.put((self._show_excel, (output_excel,)))
                    self.ui_events.put((self._scan_notice, (f"Saved {len(results)} channels to Excel.",)))
                else:
                    self.log("\n[-] No channels matched the criteria.")
                    self.ui_events.put((self._scan_notice, ("No matching channels yet. Try broader filters or add new topics.",)))
            except Exception as error:
                self.log("[!] Excel: " + str(error).replace(api_key, "<API_KEY>"))
                self.ui_events.put((self._scan_failed, ("Unable to save Excel results. Close the open file and check write permissions.",)))
            finally:
                self.ui_events.put((self._scan_finished, ()))

    def _scan_progress(self, done, total):
        self.view.set_progress(done / total)
        self.view.stat_values["completed"].configure(text=f"{done} / {total}")
        self.view.status_label.configure(text=f"Processed {done}/{total} keywords")

    def _scan_notice(self, text):
        self.view.status_label.configure(text=text)

    def _scan_match_count(self, count):
        self.view.stat_values["matches"].configure(text=str(count))

    def _scan_failed(self, text):
        self._scan_outcome = "error"
        self.view.form_error.configure(text=text)
        self.view.status_label.configure(text=text)

    def _scan_finished(self):
        self.is_scanning = False
        self._tick_elapsed()
        self.view.progress_bar.stop()
        self.view.progress_bar.configure(mode="determinate")
        if self._scan_outcome == "error":
            self.view.state_badge.configure(text="NEEDS ATTENTION", text_color=t.color("danger"))
        elif self.stop_requested.is_set():
            self.view.state_badge.configure(text="STOPPED", text_color=t.color("warning"))
        else:
            self.view.set_progress(1)
            self.view.state_badge.configure(text="COMPLETE", text_color=t.color("success"))
        self.view.stop_btn.configure(state="disabled", text="Stop")
        self.view.start_btn.configure(state="normal", text="Explore more")


if __name__ == "__main__":
    app = YtbBotApp()
    app.mainloop()
