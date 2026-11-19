import json
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from .common import USER_AGENT, build_channel_element, fetch_from_xml_sources

API_URL = "https://api-service.mcot.net/api/web/v1/tv/program/?date=&categoryId=35"

def fetch(tvg_id, channel_name, logo_url=""):
    ch_elem = build_channel_element(tvg_id, channel_name, logo_url)
    programmes = []
    tz_th = timezone(timedelta(hours=7))
    now = datetime.now(tz_th)
    today_base = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_str = str(now.day)

    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(
            API_URL,
            headers={"User-Agent": USER_AGENT, "Referer": "https://tv.mcot.net/tv/th/program/35", "Accept": "application/json"}
        )
        data = json.loads(urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8"))
        channels = data.get("responseObject", {}).get("programChannels", [])

        target_day = next((c for c in channels if str(c.get("date")) == day_str and c.get("items")), None)
        if not target_day:
            target_day = next((c for c in channels if c.get("items")), None)

        if target_day:
            for item in target_day.get("items", []):
                title = (item.get("name") or "").strip()
                st = (item.get("broadcastTime") or "").strip()
                et = (item.get("broadcastEndTime") or "").strip()
                desc = (item.get("description") or "").strip()
                if not (title and ":" in st and ":" in et):
                    continue
                sh, sm = map(int, st.split(":")[:2])
                eh, em = map(int, et.split(":")[:2])
                dt_start = today_base.replace(hour=sh, minute=sm)
                dt_stop = today_base.replace(hour=eh, minute=em)
                if dt_stop <= dt_start:
                    dt_stop += timedelta(days=1)

                p_elem = ET.Element("programme", {
                    "start": dt_start.strftime("%Y%m%d%H%M%S +0700"),
                    "stop": dt_stop.strftime("%Y%m%d%H%M%S +0700"),
                    "channel": tvg_id
                })
                t_elem = ET.SubElement(p_elem, "title", {"lang": "th"})
                t_elem.text = title
                if desc:
                    d_elem = ET.SubElement(p_elem, "desc", {"lang": "th"})
                    d_elem.text = desc
                programmes.append(p_elem)

    except Exception as e:
        print(f"⚠️  [{channel_name}] Direct EPG fetch error: {e}")

    if not programmes:
        return fetch_from_xml_sources(tvg_id, channel_name, logo_url, ["MCOT.HD.th"])
    return ch_elem, programmes
