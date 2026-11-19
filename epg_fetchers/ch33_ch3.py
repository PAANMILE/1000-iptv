import json
import re
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from .common import USER_AGENT, build_channel_element

URL = "https://ch3plus.com/schedule"

def _collect_schedule_items(obj, out):
    if isinstance(obj, dict):
        if "day" in obj and "start" in obj and "end" in obj and "title" in obj:
            out.append(obj)
        else:
            for v in obj.values():
                _collect_schedule_items(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _collect_schedule_items(item, out)

def fetch(tvg_id, channel_name, logo_url=""):
    ch_elem = build_channel_element(tvg_id, channel_name, logo_url)
    programmes = []

    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT, "Accept-Language": "th-TH,th;q=0.9"})
        html = urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8", errors="ignore")
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
        if m:
            data = json.loads(m.group(1))
            items = []
            _collect_schedule_items(data, items)

            seen = set()
            for item in items:
                day_str = (item.get("day") or "").strip()
                st = (item.get("start") or "").strip()
                et = (item.get("end") or "").strip()
                title = (item.get("title") or "").strip()
                desc = (item.get("desc") or "").strip()
                if not (day_str and ":" in st and ":" in et and title):
                    continue
                key = (day_str, st, title)
                if key in seen:
                    continue
                seen.add(key)

                base_dt = datetime.strptime(day_str, "%Y-%m-%d")
                sh, sm = map(int, st.split(":")[:2])
                eh, em = map(int, et.split(":")[:2])
                dt_start = base_dt.replace(hour=sh, minute=sm)
                dt_stop = base_dt.replace(hour=eh, minute=em)
                if dt_stop <= dt_start:
                    dt_stop += timedelta(days=1)

                p_elem = ET.Element("programme", {
                    "start": dt_start.strftime("%Y%m%d%H%M%S +0700"),
                    "stop": dt_stop.strftime("%Y%m%d%H%M%S +0700"),
                    "channel": tvg_id
                })
                t_elem = ET.SubElement(p_elem, "title", {"lang": "th"})
                t_elem.text = title
                if desc and desc != title:
                    d_elem = ET.SubElement(p_elem, "desc", {"lang": "th"})
                    d_elem.text = desc
                programmes.append(p_elem)

    except Exception as e:
        print(f"⚠️  [{channel_name}] Direct EPG fetch error: {e}")

    return ch_elem, programmes
