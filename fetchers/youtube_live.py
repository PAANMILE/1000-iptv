import re
import sys
import time
import subprocess

FALLBACK_HANDLES = {
    "OxQQsIvJTTU": "https://www.youtube.com/@KBSWorldTV/live",
    "oPonPGALYaU": "https://www.youtube.com/@MrBean/live",
    "PU4emHQmC2o": "https://www.youtube.com/@SpongeBobOfficial/live",
}

def _ytdlp_m3u8(target):
    for client in ["ios", "android", "tv_embedded", "mweb"]:
        try:
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "--extractor-args", f"youtube:player_client={client}",
                "-g", "--no-warnings", target
            ]
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=25).decode("utf-8").strip()
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("http") and ".m3u8" in line:
                    return line
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("http"):
                    return line
        except Exception:
            continue
    return None

def fetch(driver, url, channel_name, seen_urls=None):
    candidates = []
    if url:
        candidates.append(url)
        for vid, handle_url in FALLBACK_HANDLES.items():
            if vid in url and handle_url not in candidates:
                candidates.append(handle_url)

    for target in candidates:
        m3u8 = _ytdlp_m3u8(target)
        if m3u8:
            return m3u8

    if driver is not None and url:
        try:
            driver.get(url)
            time.sleep(5)
            src = driver.page_source or ""
            m = re.search(r'"hlsManifestUrl"\s*:\s*"([^"]+\.m3u8[^"]*)"', src)
            if m:
                return m.group(1).replace("\\u0026", "&").replace("\\/", "/")
        except Exception:
            pass
    return None
