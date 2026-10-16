import os
import threading
import datetime
import queue
import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app_version import APP_VERSION
from updater import check_for_update, download_update, install_update
from excel_viewer import ExcelViewer

# Cấu hình giao diện chung
ctk.set_appearance_mode("Dark")  # "Dark", "Light", hoặc "System"
ctk.set_default_color_theme("blue")

APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
ENV_FILE = str(APP_DIR / ".env")
load_dotenv(ENV_FILE)
if not os.path.exists(ENV_FILE):
    load_dotenv(".env")  # Read the legacy working-directory settings on first launch.


class YtbBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Ytb-Bot · v{APP_VERSION}")
        self.geometry("1180x900")
        self.minsize(1020, 800)

        self.excel_keyword_path = ""
        self.is_scanning = False
        self.update_busy = False
        self.available_release = None
        self.ui_events = queue.Queue()

        # Bố cục chính: Sidebar bên trái, Main Content bên phải
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()
        self.after(100, self._process_ui_events)
        self.after(2000, self.check_updates)
        self.after(6 * 60 * 60 * 1000, self._scheduled_update_check)

    def _process_ui_events(self):
        try:
            while True:
                callback, args = self.ui_events.get_nowait()
                callback(*args)
        except queue.Empty:
            pass
        self.after(100, self._process_ui_events)

    def _scheduled_update_check(self):
        self.check_updates()
        self.after(6 * 60 * 60 * 1000, self._scheduled_update_check)

    def check_updates(self):
        if self.update_busy:
            return
        self.update_busy = True
        self.update_button.configure(state="disabled")
        self.update_label.configure(text="Đang kiểm tra phiên bản…")
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
        self.update_button.configure(state="normal", text="Cập nhật ngay" if release else "Kiểm tra cập nhật")
        if error:
            self.update_label.configure(text="Chưa kiểm tra được cập nhật")
            self.log(f"[Cập nhật] {error}")
        elif release:
            self.update_label.configure(text=f"Có phiên bản mới: v{release.version}")
            self.log(f"[Cập nhật] Có v{release.version}. Chọn Cập nhật ngay để tải và khởi động lại.")
        else:
            self.update_label.configure(text=f"Phiên bản hiện tại: v{APP_VERSION}")

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
        self.start_btn.configure(state="disabled")
        self.update_button.configure(state="disabled")
        def work():
            try:
                staged = download_update(release, lambda fraction: self.ui_events.put(
                    (self._download_progress, (fraction,))))
                self.ui_events.put((self._install_download, (staged,)))
            except Exception as error:
                self.ui_events.put((self._update_failed, (str(error),)))
        threading.Thread(target=work, daemon=True).start()

    def _download_progress(self, fraction):
        self.update_label.configure(text=f"Đang tải cập nhật… {fraction:.0%}")

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
        self.start_btn.configure(state="normal")
        self.update_button.configure(state="normal")
        self.update_label.configure(text="Cập nhật thất bại · có thể thử lại")
        messagebox.showerror("Cập nhật", error)

    def _build_sidebar(self):
        self.sidebar = ctk.CTkScrollableFrame(self, width=265, corner_radius=0,
                                             fg_color=("#eef2f7", "#111827"))
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.sidebar, text="YTB / SCANNER", anchor="w",
                     font=ctk.CTkFont(size=23, weight="bold")).grid(
                         row=0, column=0, padx=18, pady=(26, 4), sticky="ew")
        ctk.CTkLabel(self.sidebar, text="Khám phá kênh YouTube mới", anchor="w",
                     text_color=("#64748b", "#94a3b8")).grid(
                         row=1, column=0, padx=18, pady=(0, 26), sticky="ew")
        ctk.CTkLabel(self.sidebar, text="CẤU HÌNH QUÉT", anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold")).grid(
                         row=2, column=0, padx=18, pady=(0, 14), sticky="ew")
        def field(row, title, hint, value, masked=False):
            ctk.CTkLabel(self.sidebar, text=title, anchor="w").grid(
                row=row, column=0, padx=18, pady=(12, 4), sticky="ew")
            entry = ctk.CTkEntry(self.sidebar, height=38, show="*" if masked else "")
            entry.grid(row=row+1, column=0, padx=18, sticky="ew")
            entry.insert(0, value)
            ctk.CTkLabel(self.sidebar, text=hint, anchor="w", wraplength=225,
                         justify="left", text_color=("#64748b", "#94a3b8"),
                         font=ctk.CTkFont(size=11)).grid(
                             row=row+2, column=0, padx=18, pady=(4, 0), sticky="ew")
            return entry
        self.api_entry = field(3, "YouTube API Key", "Khóa được lưu khi bắt đầu quét.",
                               os.getenv("YOUTUBE_API_KEY", ""), True)
        self.max_age_entry = field(6, "Tuổi kênh tối đa · ngày", "Chỉ tìm kênh mới trong khoảng này.", "90")
        self.min_views_entry = field(9, "Tổng lượt xem tối thiểu", "Lọc theo tổng lượt xem của kênh.", "500")
        self.pages_label = ctk.CTkLabel(self.sidebar, text="Độ sâu quét · 2 trang / từ khóa", anchor="w")
        self.pages_label.grid(row=12, column=0, padx=18, pady=(20, 8), sticky="ew")
        self.max_pages_slider = ctk.CTkSlider(
            self.sidebar, from_=1, to=5, number_of_steps=4,
            command=lambda value: self.pages_label.configure(
                text=f"Độ sâu quét · {int(value)} trang / từ khóa"))
        self.max_pages_slider.grid(row=13, column=0, padx=18, sticky="ew")
        self.max_pages_slider.set(2)
        ctk.CTkLabel(self.sidebar, text="1 trang = tối đa 50 video", anchor="w",
                     text_color=("#64748b", "#94a3b8"), font=ctk.CTkFont(size=11)).grid(
                         row=14, column=0, padx=18, pady=(6, 24), sticky="ew")
        ctk.CTkLabel(self.sidebar, text="Giao diện", anchor="w").grid(
            row=15, column=0, padx=18, sticky="ew")
        self.theme_switch = ctk.CTkOptionMenu(
            self.sidebar, values=["Tối", "Sáng", "Theo hệ thống"], height=36,
            command=lambda mode: ctk.set_appearance_mode(
                {"Tối": "Dark", "Sáng": "Light", "Theo hệ thống": "System"}[mode]))
        self.theme_switch.grid(row=16, column=0, padx=18, pady=(6, 24), sticky="ew")
        self.update_label = ctk.CTkLabel(self.sidebar, text=f"Phiên bản hiện tại: v{APP_VERSION}",
                                         wraplength=225, justify="left")
        self.update_label.grid(row=17, column=0, padx=18, pady=(4, 8), sticky="ew")
        self.update_button = ctk.CTkButton(self.sidebar, text="Kiểm tra cập nhật", command=self.update_action)
        self.update_button.grid(row=18, column=0, padx=18, pady=(0, 20), sticky="ew")

    def _build_main_area(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=24, pady=24, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(4, weight=1)
        ctk.CTkLabel(self.main_frame, text="Khám phá kênh tiềm năng", anchor="w",
                     font=ctk.CTkFont(size=27, weight="bold")).grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(self.main_frame, text="Nhập từ khóa, chọn bộ lọc và tìm những kênh mới đang tăng trưởng.",
                     anchor="w", text_color=("#64748b", "#94a3b8"), wraplength=650,
                     justify="left").grid(row=1, column=0, pady=(6, 20), sticky="ew")
        kw_frame = ctk.CTkFrame(self.main_frame, corner_radius=14,
                               fg_color=("#ffffff", "#182233"))
        kw_frame.grid(row=2, column=0, sticky="ew")
        kw_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(kw_frame, text="01  /  Từ khóa tìm kiếm", anchor="w",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(
                         row=0, column=0, padx=18, pady=(16, 4), sticky="ew")
        ctk.CTkButton(kw_frame, text="Nhập Excel", width=120, height=34,
                      command=self.load_keywords_excel).grid(
                          row=0, column=1, padx=18, pady=(16, 4))
        ctk.CTkLabel(kw_frame, text="Mỗi dòng một từ khóa. Nhập Excel để xem sheet và chọn cột từ khóa.",
                     anchor="w", text_color=("#64748b", "#94a3b8"), wraplength=600,
                     justify="left").grid(row=1, column=0, columnspan=2, padx=18, sticky="ew")
        self.kw_textbox = ctk.CTkTextbox(kw_frame, height=110, corner_radius=8,
                                        border_width=1, border_color=("#e2e8f0", "#334155"))
        self.kw_textbox.grid(row=2, column=0, columnspan=2, padx=18, pady=(12, 18), sticky="ew")
        self.kw_textbox.insert("0.0", "AI Automation\nAI Agent\ntạo video bằng AI")
        action_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        action_frame.grid(row=3, column=0, pady=16, sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)
        self.start_btn = ctk.CTkButton(action_frame, text="Bắt đầu quét kênh", height=44,
                                       font=ctk.CTkFont(size=15, weight="bold"),
                                       command=self.start_scan_thread)
        self.start_btn.grid(row=0, column=0, padx=(0, 12), sticky="ew")
        self.open_output_btn = ctk.CTkButton(action_frame, text="Xem kết quả Excel", height=44,
                                             fg_color=("#dbe4ef", "#334155"),
                                             text_color=("#1e293b", "#e2e8f0"),
                                             hover_color=("#cbd5e1", "#475569"),
                                             command=self.open_output_excel)
        self.open_output_btn.grid(row=0, column=1, sticky="ew")
        self.content_tabs = ctk.CTkTabview(self.main_frame)
        self.content_tabs.grid(row=4, column=0, sticky="nsew")
        activity_tab = self.content_tabs.add("Hoạt động")
        excel_tab = self.content_tabs.add("Excel")
        for tab in (activity_tab, excel_tab):
            tab.grid_columnconfigure(0, weight=1)
            tab.grid_rowconfigure(0, weight=1)
        self.excel_viewer = ExcelViewer(excel_tab, on_import=self._import_excel_keywords)
        self.excel_viewer.grid(row=0, column=0, sticky="nsew")
        activity = ctk.CTkFrame(activity_tab, corner_radius=14,
                               fg_color=("#ffffff", "#182233"))
        activity.grid(row=0, column=0, sticky="nsew")
        activity.grid_columnconfigure(0, weight=1)
        activity.grid_rowconfigure(3, weight=1)
        ctk.CTkLabel(activity, text="02  /  Hoạt động quét", anchor="w",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(
                         row=0, column=0, padx=18, pady=(16, 8), sticky="ew")
        self.status_label = ctk.CTkLabel(activity, text="Sẵn sàng quét", anchor="w",
                                         text_color=("#64748b", "#94a3b8"))
        self.status_label.grid(row=1, column=0, padx=18, sticky="ew")
        self.progress_bar = ctk.CTkProgressBar(activity, height=6)
        self.progress_bar.grid(row=2, column=0, padx=18, pady=(8, 12), sticky="ew")
        self.progress_bar.set(0)
        self.log_box = ctk.CTkTextbox(activity, corner_radius=8, state="disabled",
                                     font=ctk.CTkFont(family="Consolas", size=12))
        self.log_box.grid(row=3, column=0, padx=18, pady=(0, 18), sticky="nsew")
        self.log("Sẵn sàng! Kiểm tra bộ lọc và nhấn Bắt đầu quét kênh.")

    def log(self, message):
        if threading.current_thread() is not threading.main_thread():
            self.ui_events.put((self.log, (message,)))
            return
        self.log_box.configure(state="normal")
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state="disabled")

    def load_keywords_excel(self):
        self.content_tabs.set("Excel")
        self.excel_viewer.open_file()

    def _import_excel_keywords(self, keywords, file_path):
        self.excel_keyword_path = file_path
        self.kw_textbox.delete("0.0", tk.END)
        self.kw_textbox.insert("0.0", "\n".join(keywords))
        self.log(f"[+] Đã nạp {len(keywords)} từ khóa từ file: {os.path.basename(file_path)}")
        self.excel_viewer.status.configure(text=f"Đã nhập {len(keywords)} từ khóa vào danh sách phía trên.")

    def open_output_excel(self):
        output_file = str(APP_DIR / "danh_sach_kenh_viral_moi.xlsx")
        if os.path.exists(output_file):
            self._show_excel(output_file)
        else:
            messagebox.showinfo("Thông báo", "Chưa có file kết quả. Hãy chạy quét kênh trước!")

    def _show_excel(self, path):
        self.content_tabs.set("Excel")
        self.excel_viewer.open_file(path)

    def start_scan_thread(self):
        if self.is_scanning or self.update_busy:
            return
        api_key = self.api_entry.get().strip()
        if not api_key:
            messagebox.showwarning("Thiếu API Key", "Vui lòng nhập YouTube API Key ở cột bên trái!")
            return

        # Lưu tự động API key vào file .env
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(f"YOUTUBE_API_KEY={api_key}\n")

        raw_keywords = self.kw_textbox.get("0.0", tk.END).splitlines()
        keywords = [k.strip() for k in raw_keywords if k.strip()]
        if not keywords:
            messagebox.showwarning("Thiếu từ khóa", "Vui lòng nhập ít nhất 1 từ khóa để quét!")
            return

        try:
            max_days = int(self.max_age_entry.get().strip())
            min_views = int(self.min_views_entry.get().strip())
            max_pages = int(self.max_pages_slider.get())
        except ValueError:
            messagebox.showerror("Lỗi định dạng", "Tuổi kênh và Lượt xem tối thiểu phải là số nguyên!")
            return

        self.is_scanning = True
        self.content_tabs.set("Hoạt động")
        self.start_btn.configure(state="disabled", text="Đang quét…")
        self.progress_bar.set(0)
        self.log_box.configure(state="normal")
        self.log_box.delete("0.0", tk.END)
        self.log_box.configure(state="disabled")
        self.status_label.configure(text="Đang bắt đầu quét…")

        thread = threading.Thread(
            target=self.run_scanner,
            args=(api_key, keywords, max_days, min_views, max_pages),
            daemon=True
        )
        thread.start()

    def run_scanner(self, api_key, keywords, max_days, min_views, max_pages):
        try:
            youtube = build("youtube", "v3", developerKey=api_key)
            cutoff_date = (
                datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=max_days)
            ).strftime('%Y-%m-%dT%H:%M:%SZ')

            collected_channels = {}
            total_kw = len(keywords)

            for idx, kw in enumerate(keywords, 1):
                self.log(f"\n==========================================")
                self.log(f"[*] ({idx}/{total_kw}) Đang quét từ khóa: '{kw}'...")
                video_map = {}
                next_page_token = None

                for _ in range(max_pages):
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
                self.ui_events.put((messagebox.showinfo, ("Thành công", f"Đã tìm thấy {len(results)} kênh mới và lưu vào file Excel!")))
            else:
                self.log("\n[-] Không tìm thấy kênh nào thỏa mãn điều kiện.")
                self.ui_events.put((messagebox.showinfo, ("Kết quả", "Không tìm thấy kênh nào thỏa mãn bộ lọc hiện tại.")))

        except HttpError as err:
            self.log(f"\n[!] Lỗi YouTube API: {err}")
            self.ui_events.put((messagebox.showerror, ("Lỗi API", f"YouTube API báo lỗi:\n{err}")))
        except Exception as e:
            self.log(f"\n[!] Lỗi hệ thống: {e}")
            self.ui_events.put((messagebox.showerror, ("Lỗi", str(e))))
        finally:
            self.ui_events.put((self._scan_finished, ()))

    def _scan_progress(self, done, total):
        self.progress_bar.set(done / total)
        self.status_label.configure(text=f"Đã xử lý {done}/{total} từ khóa")

    def _scan_finished(self):
        self.is_scanning = False
        self.start_btn.configure(state="normal", text="Bắt đầu quét kênh")


if __name__ == "__main__":
    app = YtbBotApp()
    app.mainloop()
