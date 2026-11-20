import sys
import subprocess

def fetch(*args, **kwargs):
    url = kwargs.get("url") or next((a for a in args if isinstance(a, str) and a.startswith("http")), "https://www.youtube.com/watch?v=OxQQsIvJTTU")
    candidates = [
        url,
        "https://www.youtube.com/@KBSWorldTV/live"
    ]
    for target in candidates:
        if not target:
            continue
        try:
            cmd = [sys.executable, "-m", "yt_dlp", "-g", "-f", "best[ext=mp4]/best", "--no-warnings", target]
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=25).decode("utf-8").strip()
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("http") and ".m3u8" in line:
                    return line
            if out.startswith("http"):
                return out.splitlines()[0].strip()
        except Exception:
            continue
    return None
