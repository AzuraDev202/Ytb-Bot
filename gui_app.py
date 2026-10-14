import os
import threading
import datetime
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pandas as pd
from dotenv import load_dotenv, set_key
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Cấu hình giao diện chung
ctk.set_appearance_mode("Dark")  # "Dark", "Light", hoặc "System"
ctk.set_default_color_theme("blue")

ENV_FILE = ".env"
load_dotenv(ENV_FILE)


class YtbBotApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Viral New Channel Scanner - Ytb-Bot")
        self.geometry("950x680")
        self.minsize(850, 600)

        self.excel_keyword_path = ""
        self.is_scanning = False

        # Bố cục chính: Sidebar bên trái, Main Content bên phải
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main_area()

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(8, weight=1)

        # Logo / Title
        self.logo_label = ctk.CTkLabel(
            self.sidebar, text="🚀 YTB-BOT SCANNER",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(25, 15))

        # 1. API Key
        ctk.CTkLabel(self.sidebar, text="YouTube API Key:", anchor="w").grid(
            row=1, column=0, padx=20, pady=(10, 0), sticky="ew"
        )
        self.api_entry = ctk.CTkEntry(self.sidebar, placeholder_text="Nhập API Key...", show="*")
        self.api_entry.grid(row=2, column=0, padx=20, pady=(5, 10), sticky="ew")
        saved_key = os.getenv("YOUTUBE_API_KEY", "")
        if saved_key:
            self.api_entry.insert(0, saved_key)

        # 2. Tuổi kênh tối đa (ngày)
        ctk.CTkLabel(self.sidebar, text="Tuổi kênh tối đa (ngày):", anchor="w").grid(
            row=3, column=0, padx=20, pady=(10, 0), sticky="ew"
        )
        self.max_age_entry = ctk.CTkEntry(self.sidebar)
        self.max_age_entry.grid(row=4, column=0, padx=20, pady=(5, 10), sticky="ew")
        self.max_age_entry.insert(0, "90")

        # 3. Lượt xem tối thiểu
        ctk.CTkLabel(self.sidebar, text="Tổng lượt xem tối thiểu:", anchor="w").grid(
            row=5, column=0, padx=20, pady=(10, 0), sticky="ew"
        )
        self.min_views_entry = ctk.CTkEntry(self.sidebar)
        self.min_views_entry.grid(row=6, column=0, padx=20, pady=(5, 10), sticky="ew")
        self.min_views_entry.insert(0, "500")

        # 4. Số trang quét mỗi từ khóa
        ctk.CTkLabel(self.sidebar, text="Số trang quét / key (1 trang = 50 video):", anchor="w").grid(
            row=7, column=0, padx=20, pady=(10, 0), sticky="ew"
        )
        self.max_pages_slider = ctk.CTkSlider(self.sidebar, from_=1, to=5, number_of_steps=4)
        self.max_pages_slider.grid(row=8, column=0, padx=20, pady=(5, 20), sticky="new")
        self.max_pages_slider.set(2)

        # Chế độ Sáng / Tối
        self.theme_switch = ctk.CTkOptionMenu(
            self.sidebar, values=["Dark", "Light", "System"],
            command=lambda mode: ctk.set_appearance_mode(mode)
        )
        self.theme_switch.grid(row=9, column=0, padx=20, pady=20, sticky="ew")

    def _build_main_area(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=12)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=1)

        # Khu vực nhập / chọn file từ khóa
        kw_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        kw_frame.grid(row=0, column=0, padx=15, pady=15, sticky="ew")
        kw_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            kw_frame, text="Danh sách từ khóa (Mỗi dòng 1 key hoặc nạp từ file Excel):",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        btn_load_excel = ctk.CTkButton(
            kw_frame, text="📂 Nạp từ Excel (.xlsx)", width=160,
            fg_color="#2B7A0B", hover_color="#1E5607",
            command=self.load_keywords_excel
        )
        btn_load_excel.grid(row=0, column=1, padx=(10, 0), pady=(0, 8))

        self.kw_textbox = ctk.CTkTextbox(kw_frame, height=110, corner_radius=8)
        self.kw_textbox.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.kw_textbox.insert("0.0", "AI Automation\nAI Agent\ntạo video bằng AI")

        # Nút điều khiển
        action_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        action_frame.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="ew")
        action_frame.grid_columnconfigure((0, 1), weight=1)

        self.start_btn = ctk.CTkButton(
            action_frame, text="▶ BẮT ĐẦU QUÉT KÊNH", height=42,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.start_scan_thread
        )
        self.start_btn.grid(row=0, column=0, padx=(0, 8), sticky="ew")

        self.open_output_btn = ctk.CTkButton(
            action_frame, text="📊 Mở File Kết Quả Excel", height=42,
            fg_color="#4A5568", hover_color="#2D3748",
            command=self.open_output_excel
        )
        self.open_output_btn.grid(row=0, column=1, padx=(8, 0), sticky="ew")

        # Thanh tiến trình
        self.progress_bar = ctk.CTkProgressBar(self.main_frame)
        self.progress_bar.grid(row=2, column=0, padx=15, pady=(5, 10), sticky="ew")
        self.progress_bar.set(0)

        # Cửa sổ Log kết quả trực tiếp
        self.log_box = ctk.CTkTextbox(
            self.main_frame, corner_radius=8,
            font=ctk.CTkFont(family="Consolas", size=13)
        )
        self.log_box.grid(row=3, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.log("[*] Sẵn sàng! Nhập API Key và danh sách từ khóa để bắt đầu.")

    def log(self, message):
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)

    def load_keywords_excel(self):
        file_path = filedialog.askopenfilename(
            title="Chọn file Excel chứa từ khóa",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if not file_path:
            return
        try:
            df = pd.read_excel(file_path)
            col = "Keyword" if "Keyword" in df.columns else df.columns[0]
            keywords = [str(k).strip() for k in df[col].dropna() if str(k).strip()]
            self.kw_textbox.delete("0.0", tk.END)
            self.kw_textbox.insert("0.0", "\n".join(keywords))
            self.log(f"[+] Đã nạp {len(keywords)} từ khóa từ file: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Lỗi đọc file Excel", f"Không thể đọc file:\n{e}")

    def open_output_excel(self):
        output_file = "danh_sach_kenh_viral_moi.xlsx"
        if os.path.exists(output_file):
            os.startfile(output_file)
        else:
            messagebox.showinfo("Thông báo", "Chưa có file kết quả. Hãy chạy quét kênh trước!")

    def start_scan_thread(self):
        if self.is_scanning:
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
        self.start_btn.configure(state="disabled", text="⏳ ĐANG QUÉT...")
        self.progress_bar.set(0)
        self.log_box.delete("0.0", tk.END)

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

                self.progress_bar.set(idx / total_kw)

            # Lưu kết quả ra Excel
            if collected_channels:
                results = list(collected_channels.values())
                df = pd.DataFrame(results)
                df.sort_values(by="Tổng Lượt Xem", ascending=False, inplace=True)
                df.insert(0, "STT", range(1, len(df) + 1))

                output_excel = "danh_sach_kenh_viral_moi.xlsx"
                with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
                    df.to_excel(writer, sheet_name="Kênh Mới Viral", index=False)

                self.log(f"\n🎉 HOÀN TẤT! Đã lưu {len(results)} kênh vào '{output_excel}'.")
                messagebox.showinfo("Thành công", f"Đã tìm thấy {len(results)} kênh mới và lưu vào file Excel!")
            else:
                self.log("\n[-] Không tìm thấy kênh nào thỏa mãn điều kiện.")
                messagebox.showinfo("Kết quả", "Không tìm thấy kênh nào thỏa mãn bộ lọc hiện tại.")

        except HttpError as err:
            self.log(f"\n[!] Lỗi YouTube API: {err}")
            messagebox.showerror("Lỗi API", f"YouTube API báo lỗi:\n{err}")
        except Exception as e:
            self.log(f"\n[!] Lỗi hệ thống: {e}")
            messagebox.showerror("Lỗi", str(e))
        finally:
            self.is_scanning = False
            self.start_btn.configure(state="normal", text="▶ BẮT ĐẦU QUÉT KÊNH")


if __name__ == "__main__":
    app = YtbBotApp()
    app.mainloop()