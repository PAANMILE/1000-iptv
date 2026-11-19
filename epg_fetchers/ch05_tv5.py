import re
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from html import unescape
from .common import USER_AGENT, build_channel_element, fetch_from_xml_sources

URL = "https://thaitv5hd.com/schedule/"

def _make_dt(base_dt, h, m):
    if h == 24:
        return base_dt + timedelta(days=1, minutes=m)
    return base_dt.replace(hour=h, minute=m)

def fetch(tvg_id, channel_name, logo_url=""):
    ch_elem = build_channel_element(tvg_id, channel_name, logo_url)
    programmes = []
    tz_th = timezone(timedelta(hours=7))
    today_base = datetime.now(tz_th).replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT, "Accept-Language": "th-TH,th;q=0.9"})
        html = urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8", errors="ignore")
        clean = re.sub(r"<script.*?</script>|<style.*?</style>", "", html, flags=re.S)
        lines = [unescape(re.sub(r"<[^>]+>", "", l)).strip() for l in clean.splitlines()]
        lines = [l for l in lines if l]

        statuses = {"ออกอากาศแล้ว", "กำลังออกอากาศ", "รายการถัดไป", "รายการต่อไป"}
        i = 0
        while i < len(lines):
            m = re.match(r"^(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})$", lines[i])
            if m:
                sh, sm, eh, em = map(int, m.groups())
                j = i + 1
                while j < len(lines) and lines[j] in statuses:
                    j += 1
                if j < len(lines):
                    title = lines[j]
                    dt_start = _make_dt(today_base, sh, sm)
                    dt_stop = _make_dt(today_base, eh, em)
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
                    i = j
            i += 1

    except Exception as e:
        print(f"⚠️  [{channel_name}] Direct EPG fetch error: {e}")

    if not programmes:
        return fetch_from_xml_sources(tvg_id, channel_name, logo_url, ["TV5.HD.th", "TV5.th"])
    return ch_elem, programmes
