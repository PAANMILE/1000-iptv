import os
import re
import base64
import importlib
import json
import ssl
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from selenium import webdriver
from selenium.webdriver.safari.options import Options

THAI_ZERO_WIDTH = set("ัิีึืฺุู็่้๊๋์ํ๎")

def pad_display(text, width=26):
    vis_len = sum(0 if (unicodedata.combining(c) or c in THAI_ZERO_WIDTH) else 1 for c in text)
    return text + " " * max(0, width - vis_len)

BASE_DIR = Path(__file__).resolve().parent
CHANNELS_FILE = BASE_DIR / "channels.json"
OUTPUT_FILE = BASE_DIR / "1000tv.m3u"

BASE_LOGO_URL = "https://raw.githubusercontent.com/PAANMILE/1000-iptv/main/logos"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15"
EXPIRY_BUFFER_SECONDS = 3600  # 1 hour

def get_referer(url):
    parsed = urlparse(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}/"
    return "https://tv.trueid.net/"

def load_existing_streams():
    existing = {}
    if not OUTPUT_FILE.exists():
        return existing
    lines = OUTPUT_FILE.read_text(encoding="utf-8").splitlines()
    current_name = None
    current_ref = None
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            current_name = line.split(",")[-1].strip()
            current_ref = None
        elif line.startswith("#EXTVLCOPT:http-referrer="):
            current_ref = line.split("=", 1)[1].strip()
        elif line and not line.startswith("#") and current_name:
            existing[current_name] = {
                "stream_url": line,
                "referer": current_ref
            }
            current_name = None
    return existing

def get_token_expiry(stream_url):
    parsed = urlparse(stream_url)
    qs = parse_qs(parsed.query)
    for key in ["x_ark_expires", "expires", "expire", "exp", "end", "validto"]:
        if key in qs:
            try:
                val = int(qs[key][0])
                if val > 1_000_000_000:
                    return val
            except ValueError:
                pass

    for part in parsed.path.split("/"):
        if part.count(".") == 2:
            try:
                payload_b64 = part.split(".")[1]
                payload_b64 += "=" * (-len(payload_b64) % 4)
                payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode("utf-8"))
                if "exp" in payload:
                    return int(payload["exp"])
            except Exception:
                pass
    return None

def check_stream_health(stream_url, referer):
    now = time.time()
    expiry = get_token_expiry(stream_url)
    if expiry is not None:
        remaining = expiry - now
        if remaining < EXPIRY_BUFFER_SECONDS:
            mins = max(0, int(remaining // 60))
            return False, f"Token expiring soon ({mins} mins left)"

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        headers = {
            "User-Agent": USER_AGENT,
            "Referer": referer or "https://tv.trueid.net/"
        }
        req = Request(stream_url, headers=headers)
        with urlopen(req, timeout=4, context=ctx) as resp:
            if resp.status != 200:
                return False, f"HTTP {resp.status}"
            body = resp.read(2048).decode("utf-8", errors="ignore")
            if "#EXTM3U" in body or "<MPD" in body:
                return True, "Healthy"
            return False, "Invalid playlist content"
    except Exception as e:
        return False, f"Connection failed ({type(e).__name__})"


def _check_yt_expire(url, min_remaining_sec=3600):
    m = re.search(r"/expire/(\d+)", url or "")
    if not m:
        return False, "No expire timestamp"
    exp_ts = int(m.group(1))
    now_ts = int(time.time())
    rem = exp_ts - now_ts
    exp_str = time.strftime("%H:%M", time.localtime(exp_ts))
    if rem > min_remaining_sec:
        hrs, mins = divmod(rem // 60, 60)
        return True, f"Valid until {exp_str} ({hrs}h {mins}m left)"
    elif rem > 0:
        mins = rem // 60
        return False, f"Expiring soon at {exp_str} ({mins}m left < 1h)"
    else:
        return False, f"Expired at {exp_str}"

def run(force_update=False, driver=None):
    if not CHANNELS_FILE.exists():
        print("❌ Error: channels.json not found")
        return driver

    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        channels = json.load(f)

    existing_streams = {} if force_update else load_existing_streams()
    if force_update:
        print("🔄 Force update mode enabled (--force)")
    results = {}
    to_fetch = []
    seen_urls = set()

    if existing_streams:
        print("🔍 Checking stream health & YouTube token expiration...")
        safari_candidates = []
        for ch in channels:
            name = ch.get("name", "Unknown")
            fetcher = ch.get("fetcher", "")
            old_data = existing_streams.get(name)
            old_url = old_data.get("stream_url", "") if old_data else ""

            if fetcher == "local_stream":
                url = ch.get("url", "")
                print(f"🟢 [LOCAL]  {name:<26} -> Preserved ({url})")
                results[name] = url
            elif fetcher == "youtube_live":
                if old_url:
                    is_valid, msg = _check_yt_expire(old_url, min_remaining_sec=3600)
                    if is_valid:
                        print(f"🟢 [KEEP]   {name:<26} -> {msg}")
                        results[name] = old_url
                    else:
                        print(f"🟡 [UPDATE] {name:<26} -> {msg}")
                        to_fetch.append(ch)
                else:
                    print(f"🟡 [UPDATE] {name:<26} -> No existing stream")
                    to_fetch.append(ch)
            else:
                if old_url:
                    old_ref = old_data.get("referer", "") or ch.get("referer", "") or ch.get("url", "")
                    safari_candidates.append((ch, old_url, old_ref))
                else:
                    print(f"🟡 [UPDATE] {name:<26} -> No existing stream")
                    to_fetch.append(ch)

        if safari_candidates:
            with ThreadPoolExecutor(max_workers=10) as ex:
                fut_map = {ex.submit(check_stream_health, url, ref): (ch, url) for ch, url, ref in safari_candidates}
                for fut in as_completed(fut_map):
                    ch, old_url = fut_map[fut]
                    name = ch.get("name", "Unknown")
                    try:
                        healthy, reason = fut.result()
                    except Exception as e:
                        healthy, reason = False, str(e)
                    if healthy:
                        print(f"🟢 [KEEP]   {name:<26} -> Healthy")
                        results[name] = old_url
                        seen_urls.add(old_url)
                    else:
                        print(f"🟡 [UPDATE] {name:<26} -> {reason}")
                        to_fetch.append(ch)
    else:
        print("🔄 Force update enabled: refreshing all non-local channels...")
        for ch in channels:
            name = ch.get("name", "Unknown")
            if ch.get("fetcher") == "local_stream":
                url = ch.get("url", "")
                print(f"🟢 [LOCAL]  {name:<26} -> Preserved ({url})")
                results[name] = url
            else:
                to_fetch.append(ch)

    yt_tasks = [ch for ch in to_fetch if ch.get("fetcher") == "youtube_live"]
    safari_tasks = [ch for ch in to_fetch if ch.get("fetcher") != "youtube_live"]

    if yt_tasks:
        print(f"\n🚀 Fetching {len(yt_tasks)} YouTube Live channel(s) sequentially via Streamlink...")
        mod = importlib.import_module("fetchers.youtube_live")
        for idx, ch in enumerate(yt_tasks, 1):
            name = ch.get("name", "Unknown")
            url = ch.get("url", "")
            m3u8 = mod.fetch(None, url, name)
            if m3u8:
                print(f"✅ [{idx}/{len(yt_tasks)}] Updated: {name}")
                results[name] = m3u8
            else:
                print(f"⚠️ [{idx}/{len(yt_tasks)}] Failed: {name} (keeping previous fallback)")
                if name in existing_streams:
                    results[name] = existing_streams[name]["stream_url"]
            if idx < len(yt_tasks):
                time.sleep(0.5)

    if safari_tasks:
        if driver is None:
            print(f"\n🌐 Launching Safari to update {len(safari_tasks)} channel(s)...")
            driver = webdriver.Safari(options=Options())
            own_driver = True
        else:
            print(f"\n🌐 Using active Safari session to update {len(safari_tasks)} channel(s)...")

        try:
            for ch in safari_tasks:
                name = ch["name"]
                fetcher_name = ch.get("fetcher")
                target_url = ch["url"]
                print(f"⏳ Fetching ({fetcher_name}): {name} ...")
                try:
                    module = importlib.import_module(f"fetchers.{fetcher_name}")
                    stream_url = module.fetch(driver, target_url, name, seen_urls)
                except Exception as e:
                    print(f"❌ Fetcher error ({fetcher_name}): {e}")
                    stream_url = None

                if stream_url and stream_url not in seen_urls:
                    print(f"✅ Updated: {name}")
                    results[name] = stream_url
                    seen_urls.add(stream_url)
                else:
                    print(f"⚠️ Failed to fetch new stream: {name}")
                    if name in existing_streams:
                        print("   ↪ Keeping previous stream as fallback")
                        results[name] = existing_streams[name]["stream_url"]
        finally:
            if own_driver and driver:
                driver.quit()
                driver = None
    else:
        print("\n⚡ All channels are healthy. Skipping Safari stream fetch!")

    m3u_lines = ['#EXTM3U']
    for ch in channels:
        name = ch["name"]
        stream_url = results.get(name)
        if not stream_url:
            continue
        logo_file = ch.get("logo", "")
        logo_url = f"{BASE_LOGO_URL}/{logo_file}" if logo_file else ""
        referer = get_referer(ch["url"])

        extinf = (
            f'#EXTINF:-1 tvg-chno="{ch.get("chno", "")}" '
            f'tvg-id="{ch.get("tvg_id", "")}" '
            f'tvg-name="{name}" '
            f'tvg-logo="{logo_url}" '
            f'group-title="{ch.get("group", "Digital TV")}",{name}'
        )
        m3u_lines.append(extinf)
        m3u_lines.append(f"#EXTVLCOPT:http-user-agent={USER_AGENT}")
        m3u_lines.append(f"#EXTVLCOPT:http-referrer={referer}")
        m3u_lines.append(stream_url)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines) + "\n")

    print(f"\n🎉 Saved playlist to: {OUTPUT_FILE} ({len(results)}/{len(channels)} channels ready)")
    return driver

def main():
    run(force_update="--force" in sys.argv, driver=None)

if __name__ == "__main__":
    main()
