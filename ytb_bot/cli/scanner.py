import os
import datetime
import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ytb_bot.core.contacts import extract_contacts
from ytb_bot.core.excel import write_results_excel

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

def get_youtube_client():
    if not API_KEY:
        raise ValueError("Please configure YOUTUBE_API_KEY in the .env file")
    return build("youtube", "v3", developerKey=API_KEY)

def is_channel_under_3_months(published_at_str, max_days=90):
    created_date = datetime.datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
    now = datetime.datetime.now(datetime.timezone.utc)
    age = (now - created_date).days
    return age <= max_days, age

def load_keywords_from_excel(file_path="keywords.xlsx", sheet_name=0, column_name="Keyword"):
    if not os.path.exists(file_path):
        df_sample = pd.DataFrame({"Keyword": ["AI Automation", "AI Agent", "AI video creation"]})
        df_sample.to_excel(file_path, index=False)
        print(f"[*] Created sample file '{file_path}'. Add keywords to the '{column_name}' column.")
        return df_sample["Keyword"].tolist()

    df = pd.read_excel(file_path, sheet_name=sheet_name)
    series = df[column_name] if column_name in df.columns else df.iloc[:, 0]
    keywords = [k.strip() for k in series.dropna().astype(str) if k.strip()]
    return keywords

def scan_channels_from_excel(input_excel="keywords.xlsx", output_excel="channel_results.xlsx", min_views=300, max_pages=2):
    youtube = get_youtube_client()
    keywords = load_keywords_from_excel(input_excel)

    if not keywords:
        print("[-] The Excel file contains no keywords!")
        return

    print(f"[*] Loaded {len(keywords)} keywords from '{input_excel}': {keywords}")
    three_months_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    collected_channels = {}

    for kw in keywords:
        print(f"\n==========================================")
        print(f"[*] Scanning keyword: '{kw}'...")
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

            print(f"[*] Found {len(video_map)} channels for keyword '{kw}'. Checking creation dates...")

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
                            "Channel Name": snippet.get("title"),
                            "Channel ID": ch_id,
                            "Channel URL": f"https://www.youtube.com/channel/{ch_id}",
                            "Search Keyword": kw,
                            "Created Date": created_at[:10],
                            "Channel Age (Days)": age_days,
                            "Subscribers": int(stats.get("subscriberCount", 0)) if not stats.get("hiddenSubscriberCount", False) else "Hidden",
                            "Total Views": total_views,
                            "Total Videos": int(stats.get("videoCount", 0)),
                            "Latest Video": video_map[ch_id]["video_title"], **contacts
                        }
                        print(f" -> [MATCH] '{snippet.get('title')}' ({age_days} days) | {total_views:,} views | Key: {kw}")

        except HttpError as err:
            print(f"[!] YouTube API error: {err}")

    # Export collected data to Excel
    if collected_channels:
        results = list(collected_channels.values())
        df = pd.DataFrame(results)
        df.sort_values(by="Total Views", ascending=False, inplace=True)
        df.insert(0, "No.", range(1, len(df) + 1))

        write_results_excel(df, output_excel, "Results")
        print(f"\n[+] COMPLETE! Saved {len(results)} channels to '{output_excel}'.")
    else:
        print("\n[-] No channels matched the criteria.")

def main():
    scan_channels_from_excel(
        input_excel="keywords.xlsx",
        output_excel="channel_results.xlsx",
        min_views=300,
        max_pages=2
    )


if __name__ == "__main__":
    main()
