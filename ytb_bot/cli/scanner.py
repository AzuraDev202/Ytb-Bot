import os
import datetime
import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ytb_bot.core.contacts import extract_contacts

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

def get_youtube_client():
    if not API_KEY:
        raise ValueError("Vui lòng cấu hình YOUTUBE_API_KEY trong file .env")
    return build("youtube", "v3", developerKey=API_KEY)

def is_channel_under_3_months(published_at_str, max_days=90):
    created_date = datetime.datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
    now = datetime.datetime.now(datetime.timezone.utc)
    age = (now - created_date).days
    return age <= max_days, age

def load_keywords_from_excel(file_path="keywords.xlsx", sheet_name=0, column_name="Keyword"):
    if not os.path.exists(file_path):
        df_sample = pd.DataFrame({"Keyword": ["AI Automation", "AI Agent", "tạo video AI"]})
        df_sample.to_excel(file_path, index=False)
        print(f"[*] Đã tạo file mẫu '{file_path}'. Vui lòng bổ sung từ khóa vào cột '{column_name}'.")
        return df_sample["Keyword"].tolist()

    df = pd.read_excel(file_path, sheet_name=sheet_name)
    series = df[column_name] if column_name in df.columns else df.iloc[:, 0]
    keywords = [k.strip() for k in series.dropna().astype(str) if k.strip()]
    return keywords

def scan_channels_from_excel(input_excel="keywords.xlsx", output_excel="danh_sach_kenh_viral_moi.xlsx", min_views=300, max_pages=2):
    youtube = get_youtube_client()
    keywords = load_keywords_from_excel(input_excel)

    if not keywords:
        print("[-] File Excel không có từ khóa nào!")
        return

    print(f"[*] Đã nạp {len(keywords)} từ khóa từ '{input_excel}': {keywords}")
    three_months_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    collected_channels = {}

    for kw in keywords:
        print(f"\n==========================================")
        print(f"[*] Đang quét từ khóa: '{kw}'...")
        video_map = {}
        next_page_token = None

        try:
            for _ in range(max_pages):
                search_res = youtube.search().list(
                    q=kw,
                    part="snippet",
                    type="video",
                    order="date",
                    publishedAfter=three_months_ago,
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()

                for item in search_res.get("items", []):
                    ch_id = item["snippet"]["channelId"]
                    if ch_id not in video_map:
                        video_map[ch_id] = {
                            "video_title": item["snippet"]["title"],
                            "keyword": kw
                        }

                next_page_token = search_res.get("nextPageToken")
                if not next_page_token:
                    break

            print(f"[*] Tìm thấy {len(video_map)} kênh từ key '{kw}'. Đang kiểm tra ngày thành lập...")

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

                    under_3_months, age_days = is_channel_under_3_months(created_at)
                    total_views = int(stats.get("viewCount", 0))

                    contacts = extract_contacts(snippet.get("description", ""))
                    if under_3_months and total_views >= min_views and contacts:
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
                            "Video Gần Nhất": video_map[ch_id]["video_title"], **contacts
                        }
                        print(f" -> [TRÚNG] '{snippet.get('title')}' ({age_days} ngày) | {total_views:,} views | Key: {kw}")

        except HttpError as err:
            print(f"[!] Lỗi YouTube API: {err}")

    # Xuất dữ liệu đã gom ra Excel
    if collected_channels:
        results = list(collected_channels.values())
        df = pd.DataFrame(results)
        df.sort_values(by="Tổng Lượt Xem", ascending=False, inplace=True)
        df.insert(0, "STT", range(1, len(df) + 1))

        with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Kênh Mới Viral", index=False)
        print(f"\n[+] HOÀN TẤT! Đã lưu {len(results)} kênh vào '{output_excel}'.")
    else:
        print("\n[-] Không tìm thấy kênh nào thỏa điều kiện.")

def main():
    scan_channels_from_excel(
        input_excel="keywords.xlsx",
        output_excel="danh_sach_kenh_viral_moi.xlsx",
        min_views=300,
        max_pages=2
    )


if __name__ == "__main__":
    main()
