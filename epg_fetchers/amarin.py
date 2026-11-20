import json
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from .common import USER_AGENT, build_channel_element

def fetch(tvg_id, channel_name, logo_url="", epg_url=None):
    ch_elem = build_channel_element(tvg_id, channel_name, logo_url)
    programmes = []
    tz_th = timezone(timedelta(hours=7))
    today_base = datetime.now(tz_th).replace(hour=0, minute=0, second=0, microsecond=0)
    today_str = today_base.strftime("%Y-%m-%d")
    url = f"https://web-api.amarintv.com/web/schedules/by-date?date={today_str}"

    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Referer": "https://www.amarintv.com/schedule", "Accept": "application/json"}
        )
        data = json.loads(urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8"))
        slots = data.get("data", {}).get("items", {})
        for period in ["morning", "afternoon", "evening", "night"]:
            for item in slots.get(period, []):
                title = (item.get("title") or "").strip()
                st = (item.get("startTime") or "").strip()
                et = (item.get("endTime") or "").strip()
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
                programmes.append(p_elem)

    except Exception as e:
        print(f"⚠️  [{channel_name}] Direct EPG fetch error: {e}")

    return ch_elem, programmes
