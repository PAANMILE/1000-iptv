from datetime import datetime, timedelta, timezone
import json
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from .common import USER_AGENT, build_channel_element, fetch_from_xml_sources

API_URL = "https://api-service.mcot.net/api/web/v1/tv/program/?date=&categoryId=35"

def fetch(tvg_id, channel_name, logo_url, driver=None, epg_url=None):
    ch_elem = build_channel_element(tvg_id, channel_name, logo_url)
    programmes = []
    tz_th = timezone(timedelta(hours=7))
    now = datetime.now(tz_th)
    today_base = now.replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(
            epg_url or API_URL,
            headers={"User-Agent": USER_AGENT, "Referer": "https://tv.mcot.net/tv/th/program/35", "Accept": "application/json"}
        )
        data = json.loads(urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8"))
        channels = data.get("responseObject", {}).get("programChannels", [])
        
        for day_idx, ch_day in enumerate(channels[:3]):
            items = ch_day.get("items") or []
            if not items:
                continue
            try:
                day_num = int(str(ch_day.get("date")).strip())
                base_dt = today_base.replace(day=day_num)
                if base_dt < today_base - timedelta(days=1):
                    # กรณีข้ามเดือน
                    next_month = (today_base.replace(day=28) + timedelta(days=4)).replace(day=day_num)
                    base_dt = next_month
            except Exception:
                base_dt = today_base + timedelta(days=day_idx)

            day_slots = []
            for item in items:
                title = (item.get("name") or "").strip()
                st = (item.get("broadcastTime") or "").strip()
                et = (item.get("broadcastEndTime") or "").strip()
                desc = (item.get("description") or "").strip()
                if not (title and ":" in st and ":" in et):
                    continue
                sh, sm = map(int, st.split(":")[:2])
                eh, em = map(int, et.split(":")[:2])
                dt_start = base_dt.replace(hour=sh, minute=sm)
                dt_stop = base_dt.replace(hour=eh, minute=em)
                if dt_stop <= dt_start:
                    dt_stop += timedelta(days=1)
                day_slots.append((dt_start, dt_stop, title, desc))

            day_slots.sort(key=lambda x: x[0])
            # ถ้าช่วงเช้า (00:00 ถึงรายการแรก เช่น 07:00) ไม่มีรายการใน API ให้เติมช่วงปิดสถานี/รายการทั่วไป
            if day_slots and day_slots[0][0] > base_dt:
                day_slots.insert(0, (base_dt, day_slots[0][0], "รายการทั่วไป 9 MCOT HD", ""))

            for dt_start, dt_stop, title, desc in day_slots:
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
