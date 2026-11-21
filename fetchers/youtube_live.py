import re
import time

FALLBACK_HANDLES = {
    "OxQQsIvJTTU": "https://www.youtube.com/@KBSWorldTV/live",
    "oPonPGALYaU": "https://www.youtube.com/@MrBean/live",
    "PU4emHQmC2o": "https://www.youtube.com/@SpongeBobOfficial/live",
}

def _to_mobile_url(url):
    return url.replace("://www.youtube.com", "://m.youtube.com")

def _extract_from_safari(driver, target_url, seen_urls, max_wait=10.0):
    mobile_url = _to_mobile_url(target_url)
    try:
        driver.execute_script("performance.clearResourceTimings();")
    except Exception:
        pass

    driver.get(mobile_url)
    elapsed = 0.0
    while elapsed < max_wait:
        time.sleep(0.5)
        elapsed += 0.5
        try:
            # 1) ตรวจหา .m3u8 จาก Network Resource (m.youtube.com บน Safari จะโหลด HLS .m3u8 ตรง ๆ)
            candidates = driver.execute_script("""
                return performance.getEntriesByType('resource')
                    .map(r => r.name)
                    .filter(u => u.includes('.m3u8'));
            """) or []
            for c in candidates:
                if c not in seen_urls and "googlevideo.com" in c:
                    return c

            # 2) ตรวจหา hlsManifestUrl จากซอร์สโค้ดหน้าเว็บหรือ ytInitialPlayerResponse
            hls = driver.execute_script("""
                try {
                    if (window.ytInitialPlayerResponse &&
                        ytInitialPlayerResponse.streamingData &&
                        ytInitialPlayerResponse.streamingData.hlsManifestUrl) {
                        return ytInitialPlayerResponse.streamingData.hlsManifestUrl;
                    }
                } catch (e) {}
                const html = document.documentElement.innerHTML || "";
                const m = html.match(/https?:\\\\?\/\\\\?\/manifest\\.googlevideo\\.com\\\\?\/api\\\\?\/manifest\\\\?\/hls_variant[^"'\\s<>]+\\.m3u8[^"'\\s<>]*/);
                return m ? m[0] : null;
            """)
            if hls:
                clean_url = hls.replace("\\u0026", "&").replace("\\/", "/")
                if clean_url not in seen_urls:
                    return clean_url
        except Exception:
            pass
    return None

def fetch(driver, url, channel_name, seen_urls=None):
    if driver is None or not url:
        return None
    if seen_urls is None:
        seen_urls = set()

    candidates = [url]
    for vid, handle_url in FALLBACK_HANDLES.items():
        if vid in url and handle_url not in candidates:
            candidates.append(handle_url)

    for target in candidates:
        m3u8 = _extract_from_safari(driver, target, seen_urls)
        if m3u8:
            return m3u8
    return None
