import json
import os
import re
import ssl
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15"
_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "epg_cache")

def build_channel_element(tvg_id, channel_name, logo_url=""):
    ch_elem = ET.Element("channel", {"id": tvg_id})
    dn = ET.SubElement(ch_elem, "display-name", {"lang": "th"})
    dn.text = channel_name
    if logo_url:
        ET.SubElement(ch_elem, "icon", {"src": logo_url})
    return ch_elem

def _to_xmltv_time(iso_str, tz_th):
    if not iso_str:
        return ""
    try:
        clean_str = re.sub(r"\.\d+Z$", "Z", iso_str).replace("Z", "+0000")
        dt_utc = datetime.strptime(clean_str, "%Y-%m-%dT%H:%M:%S%z")
        return dt_utc.astimezone(tz_th).strftime("%Y%m%d%H%M%S +0700")
    except Exception:
        return ""

def _load_epg_cache(cache_key, tvg_id, channel_name, logo_url, max_age=21600):
    path = os.path.join(_CACHE_DIR, f"{cache_key}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if time.time() - payload.get("fetched_at", 0) > max_age:
            return None
        ch_elem = build_channel_element(tvg_id, channel_name, logo_url)
        progs = []
        tz_th = timezone(timedelta(hours=7))
        for item in payload.get("programmes", []):
            dt_s = datetime.fromisoformat(item["start"].replace("Z", "+00:00")).astimezone(tz_th)
            dt_e = datetime.fromisoformat(item["stop"].replace("Z", "+00:00")).astimezone(tz_th)
            p_elem = ET.Element("programme", {
                "start": dt_s.strftime("%Y%m%d%H%M%S +0700"),
                "stop": dt_e.strftime("%Y%m%d%H%M%S +0700"),
                "channel": tvg_id
            })
            t_elem = ET.SubElement(p_elem, "title", {"lang": "th"})
            t_elem.text = item["title"]
            if item.get("desc"):
                d_elem = ET.SubElement(p_elem, "desc", {"lang": "th"})
                d_elem.text = item["desc"]
            progs.append(p_elem)
        if progs:
            return ch_elem, progs
    except Exception:
        pass
    return None

def fetch_from_trueid_epg(slug, tvg_id, channel_name, logo_url="", epg_url=None):
    cached = _load_epg_cache(f"trueid_{slug}", tvg_id, channel_name, logo_url)
    if cached:
        return cached
    ch_elem = build_channel_element(tvg_id, channel_name, logo_url)
    programmes = []
    tz_th = timezone(timedelta(hours=7))
    url = epg_url or f"https://tv.trueid.net/th-th/live/{slug}"

    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "th-TH,th;q=0.9"}
        )
        html = urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8", errors="ignore")
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
        if m:
            data = json.loads(m.group(1))
            epg_list = data.get("props", {}).get("pageProps", {}).get("epgList", [])
            for item in epg_list:
                start = _to_xmltv_time(item.get("start_date", ""), tz_th)
                stop = _to_xmltv_time(item.get("end_date", ""), tz_th)
                title = (item.get("title") or "").strip()
                detail = (item.get("detail") or "").strip()

                if start and stop and title:
                    p_elem = ET.Element("programme", {"start": start, "stop": stop, "channel": tvg_id})
                    t_elem = ET.SubElement(p_elem, "title", {"lang": "th"})
                    t_elem.text = title
                    if detail:
                        d_elem = ET.SubElement(p_elem, "desc", {"lang": "th"})
                        d_elem.text = detail
                    programmes.append(p_elem)
    except Exception as e:
        print(f"⚠️  [{channel_name}] TrueID EPG fetch error: {e}")

    return ch_elem, programmes
