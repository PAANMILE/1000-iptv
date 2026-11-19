import re
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from html import unescape
from .common import USER_AGENT, build_channel_element

URL = "https://www.thaipbs.or.th/program/schedules"

def fetch(tvg_id, channel_name, logo_url=""):
    ch_elem = build_channel_element(tvg_id, channel_name, logo_url)
    programmes = []
    tz_th = timezone(timedelta(hours=7))
    today_str = datetime.now(tz_th).strftime("%Y-%m-%d")

    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT, "Accept-Language": "th-TH,th;q=0.9"})
        html = urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8", errors="ignore")

        records = []
        for m in re.finditer(r"<[^>]+data-date-time=\"([^\"]+)\"[^>]*>", html):
            tag = m.group(0)
            dt_raw = m.group(1)
            # Keep all valid dates returned by schedule page
            m_prog = re.search(r'data-(?:title|program-name)="([^"]*)"', tag)
            m_ep = re.search(r'data-episode-name="([^"]*)"', tag)
            title = unescape(m_prog.group(1)).strip() if m_prog else ""
            ep = unescape(m_ep.group(1)).strip() if m_ep else ""
            if not title:
                continue
            try:
                dt_obj = datetime.fromisoformat(dt_raw).astimezone(tz_th)
                records.append((dt_obj, title, ep))
            except Exception:
                pass

        records.sort(key=lambda x: x[0])
        # Deduplicate same start time
        dedup = []
        for r in records:
            if not dedup or dedup[-1][0] != r[0]:
                dedup.append(r)

        for i, (dt_start, title, ep) in enumerate(dedup):
            if i + 1 < len(dedup):
                dt_stop = dedup[i + 1][0]
            else:
                dt_stop = dt_start.replace(hour=23, minute=59, second=59)
                if dt_stop <= dt_start:
                    dt_stop = dt_start + timedelta(minutes=30)

            p_elem = ET.Element("programme", {
                "start": dt_start.strftime("%Y%m%d%H%M%S +0700"),
                "stop": dt_stop.strftime("%Y%m%d%H%M%S +0700"),
                "channel": tvg_id
            })
            t_elem = ET.SubElement(p_elem, "title", {"lang": "th"})
            t_elem.text = title
            if ep:
                d_elem = ET.SubElement(p_elem, "desc", {"lang": "th"})
                d_elem.text = ep
            programmes.append(p_elem)

    except Exception as e:
        print(f"⚠️  [{channel_name}] Direct EPG fetch error: {e}")

    return ch_elem, programmes
