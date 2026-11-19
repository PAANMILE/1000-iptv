import copy
import gzip
import json
import re
import ssl
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from selenium import webdriver

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15"

DEFAULT_SOURCES = [
    "https://epgshare01.online/epgshare01/epg_ripper_TH1.xml.gz",
    "https://iptv-epg.org/files/epg-th.xml",
]

_XML_CACHE = {}

def get_xml_root(url):
    if url in _XML_CACHE:
        return _XML_CACHE[url]
    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        raw = urllib.request.urlopen(req, timeout=25, context=ctx).read()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        root = ET.fromstring(raw)
        _XML_CACHE[url] = root
        return root
    except Exception as e:
        print(f"⚠️  [EPG Source] Failed to load {url}: {e}")
        _XML_CACHE[url] = None
        return None

def build_channel_element(tvg_id, channel_name, logo_url=""):
    ch_elem = ET.Element("channel", {"id": tvg_id})
    dn = ET.SubElement(ch_elem, "display-name", {"lang": "th"})
    dn.text = channel_name
    if logo_url:
        ET.SubElement(ch_elem, "icon", {"src": logo_url})
    return ch_elem

def fetch_from_xml_sources(tvg_id, channel_name, logo_url="", candidate_ids=None, sources=None):
    if sources is None:
        sources = DEFAULT_SOURCES
    if candidate_ids is None:
        candidate_ids = [tvg_id]
    elif tvg_id not in candidate_ids:
        candidate_ids = [tvg_id] + list(candidate_ids)

    candidate_set = set(candidate_ids)
    ch_elem = None
    programmes = []

    for url in sources:
        root = get_xml_root(url)
        if root is None:
            continue

        matched_src_id = None
        for ch in root.findall("channel"):
            cid = ch.get("id", "")
            if cid in candidate_set:
                matched_src_id = cid
                ch_elem = copy.deepcopy(ch)
                ch_elem.set("id", tvg_id)
                break

        if matched_src_id:
            for prog in root.findall("programme"):
                if prog.get("channel") == matched_src_id:
                    p_copy = copy.deepcopy(prog)
                    p_copy.set("channel", tvg_id)
                    programmes.append(p_copy)
            if programmes:
                break

    if ch_elem is None:
        ch_elem = build_channel_element(tvg_id, channel_name, logo_url)

    return ch_elem, programmes

def _to_xmltv_time(iso_str, tz_th):
    if not iso_str:
        return ""
    try:
        clean_str = re.sub(r"\.\d+Z$", "Z", iso_str).replace("Z", "+0000")
        dt_utc = datetime.strptime(clean_str, "%Y-%m-%dT%H:%M:%S%z")
        return dt_utc.astimezone(tz_th).strftime("%Y%m%d%H%M%S +0700")
    except Exception:
        return ""

import os, json, time
_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "epg_cache")

def _load_epg_cache(cache_key, tvg_id, channel_name, logo_url, max_age=21600):
    path = os.path.join(_CACHE_DIR, f"{cache_key}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        if time.time() - payload.get("fetched_at", 0) > max_age:
            return None
        ch_elem = build_channel_element(tvg_id, channel_name, logo_url)
        progs = []
        tz_th = timezone(timedelta(hours=7))
        for item in payload.get("programmes", []):
            dt_s = datetime.fromisoformat(item["start"].replace("Z", "+00:00")).astimezone(tz_th)
            dt_e = datetime.fromisoformat(item["stop"].replace("Z", "+00:00")).astimezone(tz_th)
            p_elem = ET.Element("programme", {
                "start": dt_s.strftime("%Y%m%d%H%M%S +0700"),
                "stop": dt_e.strftime("%Y%m%d%H%M%S +0700"),
                "channel": tvg_id
            })
            t_elem = ET.SubElement(p_elem, "title", {"lang": "th"})
            t_elem.text = item["title"]
            if item.get("desc"):
                d_elem = ET.SubElement(p_elem, "desc", {"lang": "th"})
                d_elem.text = item["desc"]
            progs.append(p_elem)
        if progs:
            return ch_elem, progs
    except Exception:
        pass
    return None

def fetch_from_trueid_epg(slug, tvg_id, channel_name, logo_url=""):
    cached = _load_epg_cache(f"trueid_{slug}", tvg_id, channel_name, logo_url)
    if cached:
        return cached
    ch_elem = build_channel_element(tvg_id, channel_name, logo_url)
    programmes = []
    tz_th = timezone(timedelta(hours=7))
    url = f"https://tv.trueid.net/th-th/live/{slug}"

    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "th-TH,th;q=0.9"}
        )
        html = urllib.request.urlopen(req, timeout=20, context=ctx).read().decode("utf-8", errors="ignore")
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
        if m:
            data = json.loads(m.group(1))
            epg_list = data.get("props", {}).get("pageProps", {}).get("epgList", [])
            for item in epg_list:
                start = _to_xmltv_time(item.get("start_date", ""), tz_th)
                stop = _to_xmltv_time(item.get("end_date", ""), tz_th)
                title = (item.get("title") or "").strip()
                detail = (item.get("detail") or "").strip()

                if start and stop and title:
                    p_elem = ET.Element("programme", {"start": start, "stop": stop, "channel": tvg_id})
                    t_elem = ET.SubElement(p_elem, "title", {"lang": "th"})
                    t_elem.text = title
                    if detail:
                        d_elem = ET.SubElement(p_elem, "desc", {"lang": "th"})
                        d_elem.text = detail
                    programmes.append(p_elem)
    except Exception as e:
        print(f"⚠️  [{channel_name}] TrueID EPG fetch error: {e}")

    return ch_elem, programmes

def _parse_px(style_str, prop):
    m = re.search(rf"{prop}\s*:\s*([0-9.]+)px", style_str or "")
    return float(m.group(1)) if m else None

def _clean_oned_title(raw_text):
    lines = [l.strip() for l in (raw_text or "").splitlines() if l.strip()]
    badges = {"สด", "รายการถัดไป", "LIVE", "NEXT"}
    filtered = [l for l in lines if l not in badges]
    return " ".join(filtered).strip()

def fetch_from_oned_epg(url, tvg_id, channel_name, logo_url=""):
    slug = url.rstrip("/").split("/")[-1]
    cached = _load_epg_cache(f"oned_{slug}", tvg_id, channel_name, logo_url)
    if cached:
        return cached
    ch_elem = build_channel_element(tvg_id, channel_name, logo_url)
    programmes = []
    tz_th = timezone(timedelta(hours=7))
    today_base = datetime.now(tz_th).replace(hour=0, minute=0, second=0, microsecond=0)

    driver = None
    try:
        driver = webdriver.Safari()
        driver.get(url)
        time.sleep(5)

        items = driver.execute_script("""
            const rows = Array.from(document.querySelectorAll("div, ul")).filter(el => {
                if (el.children.length < 8) return false;
                const styled = Array.from(el.children).filter(c => {
                    const st = c.getAttribute("style") || "";
                    return st.includes("left:") && st.includes("width:");
                });
                return styled.length >= 8;
            });
            if (!rows.length) return [];
            return Array.from(rows[0].children).map(c => ({
                text: c.innerText || "",
                style: c.getAttribute("style") || ""
            }));
        """)

        px_per_min = 800.0 / 210.0

        for item in items:
            left_px = _parse_px(item.get("style"), "left")
            width_px = _parse_px(item.get("style"), "width")
            title = _clean_oned_title(item.get("text"))
            if left_px is None or not width_px or width_px <= 0 or not title:
                continue

            start_min = int(round(left_px / px_per_min))
            dur_min = int(round(width_px / px_per_min))
            if dur_min <= 0:
                continue

            dt_start = today_base + timedelta(minutes=start_min)
            dt_stop = dt_start + timedelta(minutes=dur_min)

            p_elem = ET.Element("programme", {
                "start": dt_start.strftime("%Y%m%d%H%M%S +0700"),
                "stop": dt_stop.strftime("%Y%m%d%H%M%S +0700"),
                "channel": tvg_id
            })
            t_elem = ET.SubElement(p_elem, "title", {"lang": "th"})
            t_elem.text = title
            programmes.append(p_elem)

    except Exception as e:
        print(f"⚠️  [{channel_name}] oneD EPG fetch error: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    return ch_elem, programmes
