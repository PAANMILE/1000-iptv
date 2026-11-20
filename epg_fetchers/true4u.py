import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from selenium import webdriver
from .common import build_channel_element

URL = "https://true4u.com/tvplan/"

def _make_dt(base_dt, h, m):
    if h == 24:
        return base_dt + timedelta(days=1, minutes=m)
    return base_dt.replace(hour=h, minute=m)

def fetch(tvg_id, channel_name, logo_url="", driver=None, epg_url=None):
    ch_elem = build_channel_element(tvg_id, channel_name, logo_url)
    programmes = []
    tz_th = timezone(timedelta(hours=7))
    today_base = datetime.now(tz_th).replace(hour=0, minute=0, second=0, microsecond=0)

    own_driver = False
    try:
        if driver is None:
            driver = webdriver.Safari()
            own_driver = True
        driver.get(URL)
        # Polling รอให้ตารางรายการโหลดเสร็จ (สูงสุด 12 วินาที)
        body = ""
        for _ in range(24):
            time.sleep(0.5)
            body = driver.execute_script("return document.body.innerText;")
            if re.search(r"\d{2}:\d{2}\s*-\s*\d{2}:\d{2}", body):
                break

        last_start_min = -1
        for line in body.splitlines():
            m = re.match(r"^\s*(\d{2}):(\d{2})\s*-\s*(\d{2}):(\d{2})\s+(.+?)\s*$", line)
            if m:
                sh, sm, eh, em, title = m.groups()
                sh, sm, eh, em = int(sh), int(sm), int(eh), int(em)
                cur_start_min = sh * 60 + sm
                if last_start_min != -1 and cur_start_min < last_start_min - 360:
                    break
                last_start_min = cur_start_min

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
                t_elem.text = title.strip()
                programmes.append(p_elem)

    except Exception as e:
        print(f"⚠️  [{channel_name}] Direct EPG fetch error: {e}")
    finally:
        if own_driver and driver:
            try:
                driver.quit()
            except Exception:
                pass

    return ch_elem, programmes
