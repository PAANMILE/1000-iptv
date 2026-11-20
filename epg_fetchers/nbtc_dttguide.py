import re
import ssl
import json
import threading
import urllib.request
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from .common import USER_AGENT, build_channel_element

NBTC_API_URL = "https://dttguide.nbtc.go.th/BcsEpgDataServices/BcsEpgDataController/getProgramDataWeb"
_CACHE_LOCK = threading.Lock()
_CACHE_BY_CHNO = None

def _load_nbtc_data():
    global _CACHE_BY_CHNO
    with _CACHE_LOCK:
        if _CACHE_BY_CHNO is not None:
            return _CACHE_BY_CHNO
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(
            NBTC_API_URL,
            data=json.dumps({"channelType": "1"}).encode("utf-8"),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": USER_AGENT,
            },
        )
        raw = urllib.request.urlopen(req, timeout=25, context=ctx).read().decode("utf-8")
        data = json.loads(raw)
        grouped = {}
        for item in data.get("results") or []:
            cno = str(item.get("channelNo") or "").strip().lstrip("0")
            if cno:
                grouped.setdefault(cno, []).append(item)
        _CACHE_BY_CHNO = grouped
        return _CACHE_BY_CHNO

def _parse_dt(pg_date, pg_time):
    # pg_date format: "DD-MM-YY" (e.g., "20-11-26")
    d_str = str(pg_date or "").strip()
    t_str = str(pg_time or "00:00:00").strip()
    if len(t_str) == 5:
        t_str += ":00"
    dt_base = datetime.strptime(d_str, "%d-%m-%y")
    hh, mm, ss = [int(x) for x in t_str.split(":")[:3]]
    if hh == 24:
        return dt_base + timedelta(days=1, minutes=mm, seconds=ss)
    return dt_base.replace(hour=hh, minute=mm, second=ss)

def fetch(tvg_id, channel_name, logo_url="", driver=None, epg_url=None):
    ch_elem = build_channel_element(tvg_id, channel_name, logo_url)
    programmes = []

    # ดึงเลขช่องจาก epg_url (เช่น "nbtc:33" หรือ "33") หรือเทียบจากชื่อช่อง
    target_cno = ""
    if epg_url:
        m = re.search(r"(\d+)", str(epg_url))
        if m:
            target_cno = m.group(1).lstrip("0")

    if not target_cno:
        name_map = {
            "thai pbs": "3", "ททบ.5": "5", "workpoint": "23", "true4u": "24",
            "gmm25": "25", "ช่อง 8": "27", "mcot": "30", "one 31": "31",
            "3hd": "33", "อมรินทร์": "34", "7hd": "35", "pptv": "36",
        }
        low = channel_name.lower()
        for k, v in name_map.items():
            if k in low:
                target_cno = v
                break

    grouped = _load_nbtc_data()
    items = grouped.get(target_cno, [])

    seen = set()
    for item in items:
        try:
            st_dt = _parse_dt(item.get("pgDate"), item.get("pgBeginTime"))
            et_dt = _parse_dt(item.get("pgDate"), item.get("pgEndTime"))
            if et_dt <= st_dt:
                et_dt += timedelta(days=1)

            st_str = st_dt.strftime("%Y%m%d%H%M%S +0700")
            et_str = et_dt.strftime("%Y%m%d%H%M%S +0700")
            if st_str in seen:
                continue
            seen.add(st_str)

            title = str(item.get("pgTitle") or "").strip() or channel_name
            desc = str(item.get("pgDesc") or "").strip()

            p = ET.Element("programme", {
                "start": st_str,
                "stop": et_str,
                "channel": tvg_id,
            })
            t_el = ET.SubElement(p, "title", {"lang": "th"})
            t_el.text = title
            if desc:
                d_el = ET.SubElement(p, "desc", {"lang": "th"})
                d_el.text = desc
            programmes.append(p)
        except Exception:
            continue

    programmes.sort(key=lambda el: el.attrib.get("start", ""))
    return ch_elem, programmes
