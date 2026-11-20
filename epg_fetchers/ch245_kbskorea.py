import re
import ssl
import html as html_lib
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
            raw_html = urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8", errors="ignore")

            ul_match = re.search(r'<ul[^>]*class=["\'][^"\']*schedule-list[^"\']*["\'][^>]*>(.*?)</ul>', raw_html, flags=re.DOTALL | re.IGNORECASE)
            section = ul_match.group(1) if ul_match else raw_html

            blocks = re.findall(r'<li[^>]*>(.*?)</li>', section, flags=re.DOTALL | re.IGNORECASE)
            day_items = []
            last_minutes = -1
            day_shift = 0

            for blk in blocks:
                t_m = re.search(r'<span[^>]*class=["\']time["\'][^>]*>\s*(\d{1,2}):(\d{2})\s*</span>', blk, flags=re.IGNORECASE)
                title_m = re.search(r'<div[^>]*class=["\']title["\'][^>]*>(.*?)</div>', blk, flags=re.DOTALL | re.IGNORECASE)
                if not t_m or not title_m:
                    continue

                hh, mm = int(t_m.group(1)), int(t_m.group(2))
                cur_minutes = hh * 60 + mm
                if last_minutes != -1 and cur_minutes < last_minutes:
                    day_shift += 1
                last_minutes = cur_minutes

                title_clean = html_lib.unescape(re.sub(r'<[^>]+>', ' ', title_m.group(1)))
                title_clean = re.sub(r'\s+', ' ', title_clean).strip()
                if not title_clean:
                    continue

                img_m = re.search(r'<img[^>]*src=["\']([^"\']+)["\']', blk, flags=re.IGNORECASE)
                icon_url = img_m.group(1).strip() if img_m else ""

                st_dt = (target_date + timedelta(days=day_shift)).replace(hour=hh, minute=mm, second=0, microsecond=0)
                day_items.append((st_dt, title_clean, icon_url))

            for idx, (st_dt, title_clean, icon_url) in enumerate(day_items):
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
                t_el.text = title_clean
                if icon_url.startswith("http"):
                    ET.SubElement(p, "icon", {"src": icon_url})
                programmes.append(p)
        except Exception as e:
            print(f"⚠️  [{channel_name}] EPG fetch error ({sdate}): {e}")

    return ch_elem, programmes
