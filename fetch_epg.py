import importlib
import inspect
import json
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.safari.options import Options

BASE_DIR = Path(__file__).resolve().parent
CHANNELS_FILE = BASE_DIR / "channels.json"
OUTPUT_EPG = BASE_DIR / "1000epg.xml"
BASE_LOGO_URL = "https://raw.githubusercontent.com/PAANMILE/1000-iptv/main/logos"
EPG_MAX_AGE_SECONDS = 6 * 3600  # 6 hours

THAI_ZERO_WIDTH = set("\u0e31\u0e34\u0e35\u0e36\u0e37\u0e38\u0e39\u0e3a\u0e47\u0e48\u0e49\u0e4a\u0e4b\u0e4c\u0e4d\u0e4e")

def pad_display(text, width=26):
    vis_len = sum(0 if (unicodedata.combining(c) or c in THAI_ZERO_WIDTH) else 1 for c in text)
    return text + " " * max(0, width - vis_len)

def is_epg_fresh():
    if not OUTPUT_EPG.exists() or OUTPUT_EPG.stat().st_size < 500:
        return False
    age = time.time() - OUTPUT_EPG.stat().st_mtime
    return age < EPG_MAX_AGE_SECONDS

def _fetch_single_http_channel(idx, ch):
    name = ch["name"]
    tvg_id = ch.get("tvg_id", "")
    fetcher_name = ch.get("epg_fetcher")
    logo_file = ch.get("logo", "")
    logo_url = f"{BASE_LOGO_URL}/{logo_file}" if logo_file else ""
    module = importlib.import_module(f"epg_fetchers.{fetcher_name}")
    ch_elem, progs = module.fetch(tvg_id, name, logo_url)
    return idx, ch_elem, progs

def run(force_update=False, driver=None):
    if not CHANNELS_FILE.exists():
        print("❌ Error: channels.json not found")
        return driver

    if not force_update and is_epg_fresh():
        mins_ago = int((time.time() - OUTPUT_EPG.stat().st_mtime) // 60)
        print(f"⚡ EPG is up-to-date (updated {mins_ago} mins ago). Skipping EPG download!")
        return driver

    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        channels = json.load(f)

    print("📅 Fetching EPG schedules (Parallel 6 threads + Shared Safari)...")
    http_tasks = []
    safari_tasks = []

    for idx, ch in enumerate(channels):
        name = ch["name"]
        tvg_id = ch.get("tvg_id", "")
        fetcher_name = ch.get("epg_fetcher")
        if not fetcher_name or not tvg_id:
            print(f"⚠️  [SKIP]   {pad_display(name)} -> Missing tvg_id or epg_fetcher")
            continue
        module = importlib.import_module(f"epg_fetchers.{fetcher_name}")
        sig = inspect.signature(module.fetch)
        if "driver" in sig.parameters:
            safari_tasks.append((idx, ch, module))
        else:
            http_tasks.append((idx, ch))

    results_by_idx = {}

    # 1. รันช่อง API / HTML / Cache พร้อมกัน 6 threads
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_map = {executor.submit(_fetch_single_http_channel, idx, ch): (idx, ch) for idx, ch in http_tasks}
        for fut in as_completed(future_map):
            idx, ch = future_map[fut]
            name = ch["name"]
            tvg_id = ch.get("tvg_id", "")
            try:
                _, ch_elem, progs = fut.result()
                results_by_idx[idx] = (ch_elem, progs)
                if progs:
                    print(f"🟢 [LOADED] {pad_display(name)} -> {len(progs)} programme(s) ({tvg_id})")
                else:
                    print(f"🟡 [EMPTY]  {pad_display(name)} -> No schedule found ({tvg_id})")
            except Exception as e:
                print(f"❌ [ERROR]  {pad_display(name)} -> {e}")

    # 2. รันช่องที่ต้องใช้ Safari โดยยืมใช้ driver ตัวเดียวกัน
    own_driver = False
    if safari_tasks:
        if driver is None:
            driver = webdriver.Safari(options=Options())
            own_driver = True
        try:
            for idx, ch, module in safari_tasks:
                name = ch["name"]
                tvg_id = ch.get("tvg_id", "")
                logo_file = ch.get("logo", "")
                logo_url = f"{BASE_LOGO_URL}/{logo_file}" if logo_file else ""
                try:
                    ch_elem, progs = module.fetch(tvg_id, name, logo_url, driver=driver)
                    results_by_idx[idx] = (ch_elem, progs)
                    if progs:
                        print(f"🟢 [LOADED] {pad_display(name)} -> {len(progs)} programme(s) ({tvg_id})")
                    else:
                        print(f"🟡 [EMPTY]  {pad_display(name)} -> No schedule found ({tvg_id})")
                except Exception as e:
                    print(f"❌ [ERROR]  {pad_display(name)} -> {e}")
        finally:
            if own_driver and driver:
                driver.quit()
                driver = None

    out_root = ET.Element("tv", {"generator-info-name": "1000-iptv-EPG"})
    all_programmes = []
    channels_with_epg = 0

    for idx in sorted(results_by_idx.keys()):
        ch_elem, progs = results_by_idx[idx]
        if ch_elem is not None:
            out_root.append(ch_elem)
        if progs:
            all_programmes.extend(progs)
            channels_with_epg += 1

    for p in all_programmes:
        out_root.append(p)

    tree = ET.ElementTree(out_root)
    ET.indent(tree, space="  ")
    tree.write(OUTPUT_EPG, encoding="utf-8", xml_declaration=True)

    print(f"\n🎉 Saved EPG to: {OUTPUT_EPG} ({channels_with_epg}/{len(channels)} channels with schedules, {len(all_programmes)} total programmes)")
    return driver

def main():
    run(force_update="--force" in sys.argv, driver=None)

if __name__ == "__main__":
    main()
