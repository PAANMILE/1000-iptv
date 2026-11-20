import re
import ssl
import urllib.request
from datetime import datetime, timedelta, timezone
import xml.etree.ElementTree as ET
from .common import USER_AGENT, build_channel_element

DEFAULT_EPG_URL = "https://kbsworld.kbs.co.kr/schedule/list_korea.php?language=e&time_add=-2"

def fetch(tvg_id, channel_name, logo_url="", driver=None, epg_url=None):
    ch_elem = build_channel_element(tvg_id, channel_name, logo_url)
    programmes = []
    base_url = (epg_url or DEFAULT_EPG_URL).strip()
    tz_th = timezone(timedelta(hours=7))
    now_th = datetime.now(tz_th)
    ctx = ssl._create_unverified_context()

    for offset in range(3):
        target_date = now_th + timedelta(days=offset)
        sdate = target_date.strftime("%Y-%m-%d")
        sep = "&" if "?" in base_url else "?"
        url = f"{base_url}{sep}sdate={sdate}"

        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            html = urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8", errors="ignore")

            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.DOTALL | re.IGNORECASE)
            day_items = []
            for row in rows:
                t_match = re.search(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", row)
                if not t_match:
                    continue
                hh, mm = int(t_match.group(1)), int(t_match.group(2))
                clean_cells = [re.sub(r"<[^>]+>", " ", c).strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.DOTALL | re.IGNORECASE)]
                clean_cells = [re.sub(r"\s+", " ", c) for c in clean_cells if c and not re.match(r"^([01]?\d|2[0-3]):[0-5]\d$", c)]
                if not clean_cells:
                    continue
                title = max(clean_cells, key=len)
                if len(title) < 2:
                    continue
                start_dt = target_date.replace(hour=hh, minute=mm, second=0, microsecond=0)
                day_items.append((start_dt, title))

            day_items.sort(key=lambda x: x[0])
            for idx, (st_dt, title) in enumerate(day_items):
                if idx + 1 < len(day_items) and day_items[idx + 1][0] > st_dt:
                    et_dt = day_items[idx + 1][0]
                else:
                    et_dt = st_dt + timedelta(minutes=60)

                p = ET.Element("programme", {
                    "start": st_dt.strftime("%Y%m%d%H%M%S +0700"),
                    "stop": et_dt.strftime("%Y%m%d%H%M%S +0700"),
                    "channel": tvg_id
                })
                t_el = ET.SubElement(p, "title", {"lang": "en"})
                t_el.text = title
                programmes.append(p)
        except Exception as e:
            print(f"⚠️  [{channel_name}] EPG fetch error ({sdate}): {e}")

    return ch_elem, programmes
