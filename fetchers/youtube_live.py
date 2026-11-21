import sys
import subprocess

FALLBACK_HANDLES = {
    "OxQQsIvJTTU": "https://www.youtube.com/@KBSWorldTV/live",
    "oPonPGALYaU": "https://www.youtube.com/@MrBean/live",
    "PU4emHQmC2o": "https://www.youtube.com/@SpongeBobOfficial/live",
}

def _ytdlp_safari_cookies(target):
    for client in ["web_safari", "mweb", "web"]:
        try:
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "--cookies-from-browser", "safari",
                "--extractor-args", f"youtube:player_client={client}",
                "--no-playlist",
                "-g", "--no-warnings", target
            ]
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=15).decode("utf-8").strip()
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
    if not url:
        return None
    candidates = [url]
    for vid, handle_url in FALLBACK_HANDLES.items():
        if vid in url and handle_url not in candidates:
            candidates.append(handle_url)

    for target in candidates:
        m3u8 = _ytdlp_safari_cookies(target)
        if m3u8:
            return m3u8
    return None
