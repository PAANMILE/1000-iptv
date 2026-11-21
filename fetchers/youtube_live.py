import time
import shutil
import subprocess

FALLBACK_HANDLES = {
    "OxQQsIvJTTU": "https://www.youtube.com/@KBSWorldTV/live",
    "oPonPGALYaU": "https://www.youtube.com/@MrBean/live",
    "PU4emHQmC2o": "https://www.youtube.com/@SpongeBobOfficial/live",
}

def _get_streamlink_bin():
    return shutil.which("streamlink") or "/usr/local/bin/streamlink"

def _run_streamlink(target):
    streamlink_bin = _get_streamlink_bin()
    cmd = [
        streamlink_bin,
        "-4",
        "--loglevel", "error",
        "--stream-url",
        target,
        "best"
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                line = line.strip()
                if line.startswith("http") and ".m3u8" in line:
                    return line, None
        err = (proc.stderr or proc.stdout or "").strip().splitlines()
        return None, (err[-1] if err else f"exit code {proc.returncode}")
    except subprocess.TimeoutExpired:
        return None, "timeout (15s)"
    except Exception as e:
        return None, str(e)

def fetch(driver, url, channel_name, seen_urls=None):
    if not url:
        return None

    candidates = [url]
    for vid, handle_url in FALLBACK_HANDLES.items():
        if vid in url and handle_url not in candidates:
            candidates.append(handle_url)

    last_err = None
    for attempt in range(1, 4):
        for target in candidates:
            m3u8, err = _run_streamlink(target)
            if m3u8:
                return m3u8
            last_err = err
        if attempt < 3:
            time.sleep(1.5)

    if last_err:
        print(f"   ⚠️ Streamlink error ({channel_name}): {last_err}")
    return None
