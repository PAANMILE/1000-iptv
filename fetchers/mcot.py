import time
from .common import sniff_stream

def fetch(driver, url, channel_name, seen_urls=None):
    blocked = set(seen_urls or [])
    try:
        # ล้าง performance entries เก่าใน Safari เพื่อกันสตรีมจากช่องก่อนหน้า (เช่น GMM25/One31) ปนเข้ามา
        old_entries = driver.execute_script(
            "return performance.getEntriesByType('resource').map(e => e.name).filter(u => u.includes('.m3u8'));"
        ) or []
        blocked.update(old_entries)
        driver.execute_script("performance.clearResourceTimings();")
    except Exception:
        pass
    return sniff_stream(driver, url, channel_name, blocked)
