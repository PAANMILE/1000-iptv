import gzip
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from .common import USER_AGENT, build_channel_element

DEFAULT_XML_URL = "https://epgshare01.online/epgshare01/epg_ripper_TH1.xml.gz"

def fetch(tvg_id, channel_name, logo_url, driver=None, epg_url=None):
    ch_elem = build_channel_element(tvg_id, channel_name, logo_url)
    programmes = []
    target_url = (epg_url or DEFAULT_XML_URL).strip()
    valid_ids = {tvg_id, "MONO.th", "MONO29.th", "Mono29.th"}

    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(target_url, headers={"User-Agent": USER_AGENT})
        raw_bytes = urllib.request.urlopen(req, timeout=25, context=ctx).read()
        if target_url.endswith(".gz") or raw_bytes[:2] == b"\x1f\x8b":
            xml_bytes = gzip.decompress(raw_bytes)
        else:
            xml_bytes = raw_bytes

        root = ET.fromstring(xml_bytes)
        for prog in root.findall("programme"):
            if prog.attrib.get("channel") in valid_ids:
                new_p = ET.Element("programme", {
                    "start": prog.attrib.get("start", ""),
                    "stop": prog.attrib.get("stop", ""),
                    "channel": tvg_id
                })
                for child in prog:
                    new_p.append(child)
                programmes.append(new_p)
    except Exception as e:
        print(f"⚠️  [{channel_name}] XML EPG fetch error: {e}")

    return ch_elem, programmes
