import re
import sys
import time
import subprocess

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
    candidates = [
        url,
        "https://www.youtube.com/@KBSWorldTV/live"
    ]
    for target in candidates:
        if not target:
            continue
        m3u8 = _ytdlp_m3u8(target)
        if m3u8:
            return m3u8

    # Fallback: ดึง hlsManifestUrl จาก Safari driver
    if driver is not None:
        try:
            driver.get(url or "https://www.youtube.com/watch?v=OxQQsIvJTTU")
            time.sleep(5)
            src = driver.page_source or ""
            m = re.search(r'"hlsManifestUrl"\s*:\s*"([^"]+\.m3u8[^"]*)"', src)
            if m:
                return m.group(1).replace("\\u0026", "&").replace("\\/", "/")
        except Exception:
            pass
    return None
