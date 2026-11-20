import re
import ssl
import html as html_lib
import urllib.request
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET
from .common import USER_AGENT, build_channel_element

FALLBACK_HANDLES = {
    "oPonPGALYaU": "https://www.youtube.com/@MrBean/live",
    "PU4emHQmC2o": "https://www.youtube.com/@SpongeBobOfficial/live",
}

def _get_live_title(url, default_title):
    candidates = []
    if url:
        candidates.append(url)
        for vid, h_url in FALLBACK_HANDLES.items():
            if vid in url and h_url not in candidates:
                candidates.append(h_url)

    ctx = ssl._create_unverified_context()
    for target in candidates:
        try:
            req = urllib.request.Request(target, headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})
            page = urllib.request.urlopen(req, timeout=15, context=ctx).read().decode("utf-8", errors="ignore")
            m = re.search(r'<meta[^>]+(?:property=["\']og:title["\']|name=["\']title["\'])[^>]+content=["\']([^"\']+)["\']', page, flags=re.IGNORECASE)
            if not m:
                m = re.search(r'<title>(.*?)</title>', page, flags=re.DOTALL | re.IGNORECASE)
            if m:
                title = html_lib.unescape(m.group(1)).strip()
                title = re.sub(r'\s*-\s*YouTube\s*$', '', title, flags=re.IGNORECASE).strip()
                if title and title.lower() not in ("youtube", "mr bean", "spongebob squarepants official"):
                    return title
        except Exception:
            continue
    return default_title

def fetch(tvg_id, channel_name, logo_url="", driver=None, epg_url=None):
    ch_elem = build_channel_element(tvg_id, channel_name, logo_url)
    live_title = _get_live_title(epg_url, f"{channel_name} (24/7 Live)")
    programmes = []

    tz_th = timezone(timedelta(hours=7))
    now_th = datetime.now(tz_th).replace(hour=0, minute=0, second=0, microsecond=0)

    for offset in range(3):
        st_dt = now_th + timedelta(days=offset)
        et_dt = st_dt + timedelta(days=1)
        p = ET.Element("programme", {
            "start": st_dt.strftime("%Y%m%d%H%M%S +0700"),
            "stop": et_dt.strftime("%Y%m%d%H%M%S +0700"),
            "channel": tvg_id
        })
        t_el = ET.SubElement(p, "title", {"lang": "en"})
        t_el.text = live_title
        d_el = ET.SubElement(p, "desc", {"lang": "en"})
        d_el.text = f"YouTube 24/7 Live Stream: {live_title}"
        programmes.append(p)

    return ch_elem, programmes
