import json
import re
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from .common import USER_AGENT, build_channel_element

URL = "https://www.ch7.com/th/schedule/"

def fetch(tvg_id, channel_name, logo_url="", epg_url=None):
    ch_elem = build_channel_element(tvg_id, channel_name, logo_url)
    programmes = []
    tz_th = timezone(timedelta(hours=7))

    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT, "Accept-Language": "th-TH,th;q=0.9"})
        html = urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8", errors="ignore")

        # Unescape escaped JSON inside script payload
        unescaped = html.replace('\\"', '"').replace('\\\\', '\\')
        records = []
        seen = set()
        for m in re.finditer(r'\{\s*"title"\s*:\s*"([^"]+)"\s*,\s*"time"\s*:\s*"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)"', unescaped):
            title = m.group(1).strip()
            t_str = m.group(2).strip()
            if not title or (t_str, title) in seen:
                continue
            seen.add((t_str, title))
            try:
                clean_t = re.sub(r"\.\d+Z$", "Z", t_str).replace("Z", "+0000")
                dt_obj = datetime.strptime(clean_t, "%Y-%m-%dT%H:%M:%S%z").astimezone(tz_th)
                records.append((dt_obj, title))
            except Exception:
                pass

        records.sort(key=lambda x: x[0])
        for i, (dt_start, title) in enumerate(records):
            if i + 1 < len(records) and (records[i + 1][0] - dt_start).total_seconds() <= 6 * 3600:
                dt_stop = records[i + 1][0]
            else:
                dt_stop = dt_start + timedelta(minutes=60)

            p_elem = ET.Element("programme", {
                "start": dt_start.strftime("%Y%m%d%H%M%S +0700"),
                "stop": dt_stop.strftime("%Y%m%d%H%M%S +0700"),
                "channel": tvg_id
            })
            t_elem = ET.SubElement(p_elem, "title", {"lang": "th"})
            t_elem.text = title
            programmes.append(p_elem)

    except Exception as e:
        print(f"⚠️  [{channel_name}] Direct EPG fetch error: {e}")

    return ch_elem, programmes
