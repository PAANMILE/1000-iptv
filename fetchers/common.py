import json
import os
import time

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "epg_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def _save_epg_cache(channel_key, programmes_list):
    if not programmes_list:
        return
    path = os.path.join(CACHE_DIR, f"{channel_key}.json")
    payload = {
        "fetched_at": time.time(),
        "programmes": programmes_list
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def _extract_trueid_epg_from_driver(driver, cache_key):
    try:
        raw = driver.execute_script("""
            const el = document.getElementById('__NEXT_DATA__');
            return el ? el.textContent : null;
        """)
        if not raw:
            return
        data = json.loads(raw)
        epg_list = data.get("props", {}).get("pageProps", {}).get("epgList", [])
        progs = []
        for obj in epg_list:
            title = (obj.get("title") or obj.get("program_name") or "").strip()
            desc = (obj.get("detail") or obj.get("synopsis") or obj.get("description") or "").strip()
            st = obj.get("start_date")
            et = obj.get("end_date")
            if title and st and et:
                progs.append({"start": st, "stop": et, "title": title, "desc": desc})
        if progs:
            _save_epg_cache(cache_key, progs)
            print(f"   💾 Cached {len(progs)} EPG items from same page")
    except Exception:
        pass

def sniff_stream(driver, url, channel_name, seen_urls=None, max_wait=15.0, poll_interval=0.5):
    if seen_urls is None:
        seen_urls = set()
    driver.get(url)
    elapsed = 0.0
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval
        candidates = driver.execute_script("""
            return performance.getEntriesByType('resource')
                .map(r => r.name)
                .filter(u => u.includes('.m3u8'));
        """)
        if candidates:
            low_res = ("144p", "240p", "360p", "480p", "chunklist")
            for c in candidates:
                if c not in seen_urls and not any(k in c.lower() for k in low_res):
                    if any(m in c.lower() for m in ("playlist.m3u8", "master.m3u8", "/live/index.m3u8")):
                        return c
            for c in candidates:
                if c not in seen_urls and not any(k in c.lower() for k in low_res):
                    return c
            for c in reversed(candidates):
                if c not in seen_urls:
                    return c
    return None

def sniff_trueid(driver, url, channel_name, seen_urls=None):
    stream_url = sniff_stream(driver, url, channel_name, seen_urls, max_wait=15.0, poll_interval=0.5)
    slug = url.rstrip("/").split("/")[-1]
    _extract_trueid_epg_from_driver(driver, f"trueid_{slug}")
    return stream_url

def sniff_oned(driver, url, channel_name, seen_urls=None):
    return sniff_stream(driver, url, channel_name, seen_urls, max_wait=16.0, poll_interval=0.5)
