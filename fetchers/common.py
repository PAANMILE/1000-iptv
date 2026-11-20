import json
import os
import time
from datetime import datetime, timezone, timedelta

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

def _extract_oned_epg_from_driver(driver, cache_key):
    try:
        tz_th = timezone(timedelta(hours=7))
        today_base = datetime.now(tz_th).replace(hour=0, minute=0, second=0, microsecond=0)
        items = driver.execute_script("""
            const out = [];
            const nodes = Array.from(document.querySelectorAll('div, button, a'));
            for (const el of nodes) {
                const st = el.getAttribute('style') || '';
                if (!st.includes('left:') || !st.includes('width:')) continue;
                const mLeft = st.match(/left:\\s*([\\d.]+)(px|%)/);
                const mWidth = st.match(/width:\\s*([\\d.]+)(px|%)/);
                const txt = (el.innerText || '').trim().split('\\n')[0].trim();
                if (mLeft && mWidth && txt && txt.length > 1 && !["วันนี้", "พรุ่งนี้", "สด", "รายการถัดไป"].includes(txt)) {
                    out.push({
                        left: parseFloat(mLeft[1]),
                        width: parseFloat(mWidth[1]),
                        unit: mLeft[2],
                        title: txt
                    });
                }
            }
            return out;
        """)
        if not items:
            return
        progs = []
        for it in items:
            if it["unit"] == "%":
                start_min = round((it["left"] / 100.0) * 1440)
                dur_min = round((it["width"] / 100.0) * 1440)
            else:
                start_min = round(it["left"] / 2.0)
                dur_min = round(it["width"] / 2.0)
            if dur_min <= 0 or start_min < 0 or start_min >= 1440:
                continue
            dt_s = today_base + timedelta(minutes=start_min)
            dt_e = dt_s + timedelta(minutes=dur_min)
            progs.append({
                "start": dt_s.isoformat(),
                "stop": dt_e.isoformat(),
                "title": it["title"],
                "desc": ""
            })
        progs.sort(key=lambda x: x["start"])
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
            # 1) Prefer Master Playlist (contains all resolutions up to 1080p)
            for c in candidates:
                if c not in seen_urls and not any(k in c.lower() for k in low_res):
                    if any(m in c.lower() for m in ("playlist.m3u8", "master.m3u8", "/live/index.m3u8")):
                        return c
            # 2) Any non-low-res m3u8
            for c in candidates:
                if c not in seen_urls and not any(k in c.lower() for k in low_res):
                    return c
            # 3) Fallback to highest available
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
    stream_url = sniff_stream(driver, url, channel_name, seen_urls, max_wait=16.0, poll_interval=0.5)
    time.sleep(0.5)  # เผื่อเวลาให้แถบ EPG render ครบเสี้ยววินาที
    slug = url.rstrip("/").split("/")[-1]
    _extract_oned_epg_from_driver(driver, f"oned_{slug}")
    return stream_url
