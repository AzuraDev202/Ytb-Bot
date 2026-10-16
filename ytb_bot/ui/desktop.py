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
from ytb_bot.build_info import build_id
from ytb_bot.updater import check_for_update, download_update, install_update
from ytb_bot.paths import APP_DIR, ENV_FILE
from ytb_bot.ui.dashboard import StudioDashboard
from ytb_bot.ui import theme as t
from ytb_bot.ui.window_layout import fit_window, screen_work_area

# Cấu hình giao diện chung
ctk.set_appearance_mode("Dark")  # "Dark", "Light", hoặc "System"
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

        # Bố cục chính: Sidebar bên trái, Main Content bên phải
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.configure(fg_color=t.color("canvas"))
        self.view = StudioDashboard(self, compact=self._compact,
            on_scan=self.start_scan_thread, on_stop=self.stop_scan,
            on_excel=self.load_keywords_excel, on_results=self.open_output_excel,
            on_update=self.update_action, on_import=self._import_excel_keywords)
        self.view.grid(row=0, column=0, sticky="nsew")
        self.log("Chọn chủ đề và bộ lọc, sau đó bắt đầu khám phá. Ctrl+Enter để quét · Ctrl+O để mở Excel.")
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
        self.view.update_label.configure(text="Đang kiểm tra phiên bản…")
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
        self.view.update_button.configure(state="normal", text="Cập nhật ngay" if release else "Kiểm tra cập nhật")
        if error:
            self.view.update_label.configure(text="Chưa kiểm tra được cập nhật")
            self.log(f"[Cập nhật] {error}")
        elif release:
            self.view.update_label.configure(text=f"Có bản cập nhật: v{release.version}")
            self.log(f"[Cập nhật] Có bản build mới của v{release.version}. Chọn Cập nhật ngay để tải và khởi động lại.")
        else:
            self.view.update_label.configure(text=f"v{APP_VERSION}\nBuild: {build_id()}")

    def update_action(self):
        if not self.available_release:
            self.check_updates()
            return
        if self.is_scanning:
            messagebox.showinfo("Cập nhật", "Hãy chờ quét hoàn tất trước khi cập nhật.")
            return
        if not getattr(sys, "frozen", False):
            messagebox.showinfo("Cập nhật", "Tự cập nhật dành cho bản EXE. Bản mã nguồn cần cập nhật qua Git.")
            return
        release = self.available_release
        if not messagebox.askyesno("Cập nhật Ytb-Bot", f"Tải v{release.version} và khởi động lại app?\nAPI Key và file Excel được giữ nguyên."):
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
        self.view.update_label.configure(text=f"Đang tải cập nhật… {fraction:.0%}")

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
        self.view.update_label.configure(text="Cập nhật thất bại · có thể thử lại")
        messagebox.showerror("Cập nhật", error)

    def log(self, message):
        if threading.current_thread() is not threading.main_thread():
            self.ui_events.put((self.log, (message,)))
            return
        self.view.log_box.configure(state="normal")
        tag = "error" if "[!]" in message else "match" if "[+]" in message or "TRÚNG:" in message else ""
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
        self.log(f"[+] Đã nạp {len(keywords)} từ khóa từ file: {os.path.basename(file_path)}")
        self.view.excel_viewer.status.configure(text=f"Đã nhập {len(keywords)} từ khóa vào danh sách phía trên.")

    def open_output_excel(self):
        output_file = str(APP_DIR / "danh_sach_kenh_viral_moi.xlsx")
        if os.path.exists(output_file):
            self._show_excel(output_file)
        else:
            messagebox.showinfo("Thông báo", "Chưa có file kết quả. Hãy chạy quét kênh trước!")

    def _show_excel(self, path):
        self.view.content_tabs.set("Excel")
        self.view.excel_viewer.open_file(path)

    def start_scan_thread(self):
        if self.is_scanning or self.is_installing:
            return
        self.view.clear_errors()
        self.view.content_tabs.set("Hoạt động")
        api_key = self.view.api_entry.get().strip()
        if not api_key:
            self.view.show_error("api", "Nhập YouTube API Key để bắt đầu.")
            return
        keywords = self.view.keywords()
        if not keywords:
            self.view.show_error("keywords", "Thêm ít nhất một từ khóa; mỗi dòng một chủ đề.")
            return
        values = {}
        for key, control, minimum, title in [
            ("age", self.view.max_age_entry, 1, "Tuổi kênh"),
            ("views", self.view.min_views_entry, 0, "Lượt xem")]:
            try:
                values[key] = int(control.get().strip())
                if values[key] < minimum:
                    raise ValueError
            except ValueError:
                self.view.show_error(key, f"{title} phải là số nguyên từ {minimum} trở lên.")
                return
        max_days, min_views = values["age"], values["views"]
        max_pages = int(self.view.max_pages_slider.get())
        try:
            set_key(ENV_FILE, "YOUTUBE_API_KEY", api_key)
        except OSError:
            self.view.show_error("api", "Không lưu được API Key. Kiểm tra quyền ghi thư mục app.")
            return
        self.is_scanning = True
        self.stop_requested.clear()
        self._scan_outcome = "success"
        self._scan_started = time.monotonic()
        self.view.content_tabs.set("Hoạt động")
        self.view.start_btn.configure(state="disabled", text="Đang quét…")
        self.view.stop_btn.configure(state="normal", text="Dừng")
        self.view.set_progress(0)
        if self.view.motion.get():
            self.view.progress_bar.configure(mode="indeterminate")
            self.view.progress_bar.start()
        self.view.state_badge.configure(text="ĐANG KHÁM PHÁ", text_color=t.color("blue"))
        self.view.stat_values["matches"].configure(text="0")
        self.view.stat_values["completed"].configure(text=f"0 / {len(keywords)}")
        self.view.refresh_keywords()
        self.view.clear_log()
        self.view.status_label.configure(text="Đang bắt đầu quét…")
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
            self.view.stop_btn.configure(state="disabled", text="Đang dừng")
            self.view.status_label.configure(text="Đang dừng sau yêu cầu hiện tại; sẽ lưu các kênh đã tìm thấy…")
            self.log("[*] Đã yêu cầu dừng. App sẽ lưu các kết quả đã tìm thấy.")

    def _tick_elapsed(self):
        if self._scan_started is None:
            return
        elapsed = int(time.monotonic() - self._scan_started)
        self.view.elapsed_label.configure(text=f"Thời gian: {elapsed // 60:02d}:{elapsed % 60:02d}")
        if self.is_scanning:
            self.after(500, self._tick_elapsed)

    def _close_window(self):
        if self.is_scanning and not messagebox.askyesno("Đóng YTB-BOT", "App đang quét. Đóng bây giờ có thể mất kết quả chưa lưu. Bạn vẫn muốn đóng?"):
            return
        self.stop_requested.set()
        self.destroy()

    def run_scanner(self, api_key, keywords, max_days, min_views, max_pages):
        try:
            youtube = build("youtube", "v3", developerKey=api_key, http=httplib2.Http(timeout=20))
            cutoff_date = (
                datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=max_days)
            ).strftime('%Y-%m-%dT%H:%M:%SZ')

            collected_channels = {}
            total_kw = len(keywords)

            for idx, kw in enumerate(keywords, 1):
                if self.stop_requested.is_set():
                    break
                self.log(f"\n==========================================")
                self.log(f"[*] ({idx}/{total_kw}) Đang quét từ khóa: '{kw}'...")
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

                self.log(f" -> Tìm thấy {len(video_map)} kênh có video mới. Đang kiểm tra độ tuổi kênh...")

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

                        if age_days <= max_days and total_views >= min_views:
                            collected_channels[ch_id] = {
                                "Tên Kênh": snippet.get("title"),
                                "Channel ID": ch_id,
                                "URL Kênh": f"https://www.youtube.com/channel/{ch_id}",
                                "Từ Khóa Quét": kw,
                                "Ngày Tạo": created_at[:10],
                                "Tuổi Kênh (Ngày)": age_days,
                                "Subscribers": int(stats.get("subscriberCount", 0)) if not stats.get("hiddenSubscriberCount", False) else "Ẩn",
                                "Tổng Lượt Xem": total_views,
                                "Tổng Video": int(stats.get("videoCount", 0)),
                                "Video Gần Nhất": video_map[ch_id]
                            }
                            self.log(f"    [+] TRÚNG: {snippet.get('title')} ({age_days} ngày) - {total_views:,} views")
                            self.ui_events.put((self._scan_match_count, (len(collected_channels),)))

                if not self.stop_requested.is_set():
                    self.ui_events.put((self._scan_progress, (idx, total_kw)))

            # Lưu kết quả ra Excel
            if collected_channels:
                results = list(collected_channels.values())
                df = pd.DataFrame(results)
                df.sort_values(by="Tổng Lượt Xem", ascending=False, inplace=True)
                df.insert(0, "STT", range(1, len(df) + 1))

                output_excel = str(APP_DIR / "danh_sach_kenh_viral_moi.xlsx")
                with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
                    df.to_excel(writer, sheet_name="Kênh Mới Viral", index=False)

                self.log(f"\n🎉 HOÀN TẤT! Đã lưu {len(results)} kênh vào '{output_excel}'.")
                self.ui_events.put((self._show_excel, (output_excel,)))
                self.ui_events.put((self._scan_notice, (f"Đã lưu {len(results)} kênh vào Excel.",)))
            else:
                self.log("\n[-] Không tìm thấy kênh nào thỏa mãn điều kiện.")
                self.ui_events.put((self._scan_notice, ("Chưa có kênh phù hợp. Thử mở rộng bộ lọc hoặc thêm chủ đề mới.",)))

        except HttpError as err:
            detail = str(err).replace(api_key, "<API_KEY>")
            self.log(f"\n[!] Lỗi YouTube API: {detail}")
            self.ui_events.put((self._scan_failed, ("YouTube API báo lỗi. Kiểm tra khóa API, quota và kết nối mạng.",)))
        except Exception as e:
            self.log(f"\n[!] Lỗi hệ thống: {str(e).replace(api_key, '<API_KEY>')}")
            self.ui_events.put((self._scan_failed, ("Lượt quét gặp lỗi. Xem nhật ký để biết chi tiết.",)))
        finally:
            self.ui_events.put((self._scan_finished, ()))

    def _scan_progress(self, done, total):
        self.view.set_progress(done / total)
        self.view.stat_values["completed"].configure(text=f"{done} / {total}")
        self.view.status_label.configure(text=f"Đã xử lý {done}/{total} từ khóa")

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
            self.view.state_badge.configure(text="CẦN KIỂM TRA", text_color=t.color("danger"))
        elif self.stop_requested.is_set():
            self.view.state_badge.configure(text="ĐÃ DỪNG", text_color=t.color("warning"))
        else:
            self.view.set_progress(1)
            self.view.state_badge.configure(text="HOÀN TẤT", text_color=t.color("success"))
        self.view.stop_btn.configure(state="disabled", text="Dừng")
        self.view.start_btn.configure(state="normal", text="Khám phá tiếp")


if __name__ == "__main__":
    app = YtbBotApp()
    app.mainloop()
