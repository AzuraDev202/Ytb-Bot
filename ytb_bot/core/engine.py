"""Thread-safe scan engine independent of any desktop UI framework."""
from collections import deque
import datetime as dt
from pathlib import Path
import threading
import time
import json

from googleapiclient.errors import HttpError
import httplib2
from googleapiclient.discovery import build
from ytb_bot.core.quota import next_reset
from ytb_bot.core.storage import WorkspaceStore
from ytb_bot.core.contacts import extract_contacts


class ScanPaused(Exception):
    """A resumable scan reached its local request budget."""


class ScanEngine:
    def __init__(self, output_dir, client_factory=None, store=None):
        self._store = store or WorkspaceStore(Path(output_dir) / "workspace.sqlite3")
        self._run_id = None
        self._client_factory = client_factory or (lambda key: build("youtube", "v3", developerKey=key, http=httplib2.Http(timeout=20)))
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread = None
        self._logs = deque(maxlen=300)
        self._state = {"status": "ready", "completed": 0, "total": 0, "matches": 0, "rows": [], "error": "", "elapsed": 0, "output": False}
        self._started = None

    def snapshot(self):
        with self._lock:
            state = dict(self._state)
            state["rows"] = list(self._state["rows"][:200])
            state["logs"] = list(self._logs)
            if state["status"] in ("running", "stopping"):
                state["elapsed"] = int(time.monotonic() - self._started)
            checkpoint = self._store.scan_checkpoint()
            now = dt.datetime.now(dt.timezone.utc)
            reset = next_reset(now)
            blocked = checkpoint.get("blocked_until") if checkpoint else None
            state.update(can_resume=bool(checkpoint), reset_at=reset.isoformat(),
                         reset_seconds=max(0, int((reset - now).total_seconds())),
                         resume_available=not blocked or now >= dt.datetime.fromisoformat(blocked),
                         resume_keyword=checkpoint["keywords"][checkpoint["index"]] if checkpoint and checkpoint["index"] < len(checkpoint["keywords"]) else "")
            return state

    def clear_logs(self):
        with self._lock:
            self._logs.clear()

    def _log(self, text, kind="info"):
        with self._lock:
            self._logs.append({"text": text, "kind": kind, "time": dt.datetime.now(dt.timezone.utc).isoformat()})

    def start(self, api_key, keywords, max_days=90, min_views=500, max_pages=2, search_budget=50, _checkpoint=None):
        keywords = list(dict.fromkeys(str(k).strip() for k in keywords if str(k).strip()))
        if not api_key or not keywords:
            raise ValueError("Enter an API key and at least one keyword.")
        max_days, min_views, max_pages = int(max_days), int(min_views), int(max_pages)
        if max_days < 1 or min_views < 0 or not 1 <= max_pages <= 5:
            raise ValueError("Channel age must be at least 1 day, views at least 0, and depth between 1 and 5 pages.")
        search_budget = int(search_budget)
        if not 1 <= search_budget <= 10000:
            raise ValueError("Search budget must be between 1 and 10000 calls.")
        with self._lock:
            if self._state["status"] in ("running", "stopping") or (self._thread is not None and self._thread.is_alive()):
                raise ValueError("A scan is already running.")
            self._checkpoint = _checkpoint or {
                "keywords": keywords, "max_days": max_days, "min_views": min_views,
                "max_pages": max_pages, "index": 0, "page": 0, "token": None, "videos": {},
                "cutoff": (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=max_days)).strftime('%Y-%m-%dT%H:%M:%SZ')}
            self._checkpoint.pop("blocked_until", None)
            self._store.save_scan_checkpoint(self._checkpoint)
            self._stop.clear()
            self._run_id = self._store.begin_run(keywords)
            self._logs.clear()
            self._started = time.monotonic()
            self._state = {"status": "running", "completed": 0, "total": len(keywords), "matches": 0, "rows": [], "error": "", "elapsed": 0, "output": False}
            self._state.update(search_budget=search_budget, search_used=0)
            self._state["completed"] = self._checkpoint["index"]
            self._thread = threading.Thread(target=self._run, args=(api_key, keywords, max_days, min_views, max_pages), daemon=True)
            self._thread.start()

    def resume(self, api_key, search_budget=50):
        with self._lock:
            checkpoint = self._store.scan_checkpoint()
            if not checkpoint:
                raise ValueError("No saved scan to resume.")
            blocked = checkpoint.get("blocked_until")
            if blocked and dt.datetime.now(dt.timezone.utc) < dt.datetime.fromisoformat(blocked):
                raise ValueError("YouTube daily quota is exhausted. Resume after the reset.")
            self.start(api_key, checkpoint["keywords"], checkpoint["max_days"],
                       checkpoint["min_views"], checkpoint["max_pages"], search_budget, checkpoint)

    def stop(self):
        with self._lock:
            if self._state["status"] == "running":
                self._state["status"] = "stopping"
                self._stop.set()
                self._log("Stopping after the current request; collected results will be saved.")

    def wait(self, timeout=10):
        if self._thread:
            self._thread.join(timeout)
        return self.snapshot()

    def _run(self, key, keywords, max_days, min_views, max_pages):
        channels = {}
        try:
            known_ids = self._store.known_channel_ids()
            checked_ids, skipped_ids = set(), set()
            self._log(f"Checked {len(known_ids)} channels in history. Only new channel IDs will be included.")
            self._log("Searching across countries and languages; results depend on keywords and page depth.")
            youtube = self._client_factory(key)
            cutoff = self._checkpoint["cutoff"]
            for index, keyword in enumerate(keywords, 1):
                if index - 1 < self._checkpoint["index"]:
                    continue
                if self._stop.is_set():
                    break
                self._log(f"Scanning: {keyword} ({index}/{len(keywords)})")
                videos, token = dict(self._checkpoint["videos"]), self._checkpoint["token"]
                for page in range(self._checkpoint["page"], max_pages):
                    if self._stop.is_set():
                        break
                    if self._state["search_used"] >= self._state["search_budget"]:
                        raise ScanPaused("Search budget reached. Progress saved; resume to continue.")
                    with self._lock:
                        self._state["search_used"] += 1
                    response = youtube.search().list(q=keyword, part="snippet", type="video", order="date", publishedAfter=cutoff, maxResults=50, pageToken=token).execute()
                    for item in response.get("items", []):
                        snippet = item["snippet"]
                        channel_id = snippet["channelId"]
                        if channel_id in known_ids:
                            skipped_ids.add(channel_id)
                            continue
                        if channel_id in checked_ids:
                            continue
                        videos.setdefault(snippet["channelId"], snippet["title"])
                    token = response.get("nextPageToken")
                    self._checkpoint.update(page=page + 1 if token else max_pages, token=token, videos=videos)
                    self._store.save_scan_checkpoint(self._checkpoint)
                    if not token:
                        break
                ids = list(videos)
                self._log(f"Found {len(ids)} channels with recent videos. Checking filters...")
                for offset in range(0, len(ids), 50):
                    if self._stop.is_set():
                        break
                    response = youtube.channels().list(part="snippet,statistics", id=",".join(ids[offset:offset + 50])).execute()
                    checked_ids.update(ids[offset:offset + 50])
                    for item in response.get("items", []):
                        channel_id = item["id"]
                        if channel_id in channels or channel_id in known_ids or channel_id not in videos:
                            continue
                        snippet, stats = item.get("snippet", {}), item.get("statistics", {})
                        created = snippet.get("publishedAt")
                        if not created:
                            continue
                        age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(created.replace("Z", "+00:00"))).days
                        views = int(stats.get("viewCount", 0))
                        if age > max_days or views < min_views:
                            continue
                        contacts = extract_contacts(snippet.get("description", ""))
                        if not contacts:
                            continue
                        channels[channel_id] = {"Channel Name": snippet.get("title", ""), "Channel ID": channel_id,
                            "Channel URL": f"https://www.youtube.com/channel/{channel_id}", "Search Keyword": keyword,
                            "Created Date": created[:10], "Channel Age (Days)": age,
                            "Subscribers": "Hidden" if stats.get("hiddenSubscriberCount") else int(stats.get("subscriberCount", 0)),
                            "Total Views": views, "Total Videos": int(stats.get("videoCount", 0)), "Latest Video": videos[channel_id],
                            "Country": snippet.get("country") or "Not disclosed", **contacts}
                        self._log(f"Match: {snippet.get('title', '')} · {views:,} views", "success")
                        with self._lock:
                            self._state["matches"] = len(channels)
                            self._state["rows"] = sorted(channels.values(), key=lambda row: row["Total Views"], reverse=True)
                    self._store.save_run(self._run_id, "running", self._all_rows())
                if not self._stop.is_set():
                    with self._lock:
                        self._state["completed"] = index
                    self._checkpoint.update(index=index, page=0, token=None, videos={})
                    self._store.save_scan_checkpoint(self._checkpoint)
            if not self._stop.is_set():
                self._store.save_scan_checkpoint(None)
            self._log(f"Skipped {len(skipped_ids)} channels already in history.")
            if channels:
                self._log(f"Saved {len(channels)} channels. Open Results to review them.", "success")
            else:
                self._log("No new channels match the filters and have public contact details. Saved channels are skipped. Try more keywords or increase the search depth.")
            with self._lock:
                self._state["status"] = "stopped" if self._stop.is_set() else "complete"
        except ScanPaused as error:
            self._log(str(error))
            with self._lock:
                self._state["status"] = "stopped"
        except Exception as error:
            daily_quota = False
            if isinstance(error, HttpError):
                try:
                    payload = json.loads(error.content.decode("utf-8"))
                    reasons = {item.get("reason") for item in payload.get("error", {}).get("errors", [])}
                    message = payload.get("error", {}).get("message", "").lower()
                    daily_quota = bool(reasons & {"quotaExceeded", "dailyLimitExceeded"}) or (
                        "per day" in message and "quota" in message)
                except (ValueError, AttributeError, UnicodeError):
                    pass
            if daily_quota:
                self._checkpoint["blocked_until"] = next_reset().isoformat()
                self._store.save_scan_checkpoint(self._checkpoint)
            detail = str(error).replace(key, "<API_KEY>")
            if daily_quota:
                detail = "YouTube daily quota exhausted. Progress saved; resume after the reset."
            self._log(detail, "error")
            with self._lock:
                self._state["status"], self._state["error"] = "error", detail
        finally:
            with self._lock:
                self._state["elapsed"] = int(time.monotonic() - self._started)
                try:
                    self._store.save_run(self._run_id, self._state["status"], self._all_rows(), self._state["error"])
                    self._state["output"] = True
                except Exception as error:
                    self._state["status"] = "error"
                    self._state["error"] = f"Could not save results: {str(error).replace(key, '<API_KEY>')}"
                    self._log(self._state["error"], "error")

    def _all_rows(self):
        with self._lock:
            return [dict(row) for row in self._state["rows"]]
