import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from .common import build_channel_element

def fetch(tvg_id, channel_name, logo_url="", epg_url=None):
    ch_elem = build_channel_element(tvg_id, channel_name, logo_url)
    tz_th = timezone(timedelta(hours=7))
    today_base = datetime.now(tz_th).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_base = today_base + timedelta(days=1)

    p_elem = ET.Element("programme", {
        "start": today_base.strftime("%Y%m%d%H%M%S +0700"),
        "stop": tomorrow_base.strftime("%Y%m%d%H%M%S +0700"),
        "channel": tvg_id
    })
    t_elem = ET.SubElement(p_elem, "title", {"lang": "en"})
    t_elem.text = "Private Boardcast"

    sub_elem = ET.SubElement(p_elem, "sub-title", {"lang": "en"})
    sub_elem.text = "Content warning SEXUAL and NUDITY"

    d_elem = ET.SubElement(p_elem, "desc", {"lang": "en"})
    d_elem.text = "Content warning SEXUAL and NUDITY\n\nThe author flagged this channel as showing sensitive content."

    return ch_elem, [p_elem]
