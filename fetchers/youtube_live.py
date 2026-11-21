import re
import time

def fetch(driver, url, channel_name, seen_urls=None):
    if driver is None or not url:
        return None
    if seen_urls is None:
        seen_urls = set()

    mobile_url = url.replace("://www.youtube.com", "://m.youtube.com")
    try:
        driver.execute_script("performance.clearResourceTimings();")
    except Exception:
        pass

    driver.get(mobile_url)
    for _ in range(16):
        time.sleep(0.5)
        try:
            m3u8 = driver.execute_script("""
                const res = performance.getEntriesByType('resource')
                    .map(r => r.name)
                    .find(u => u.includes('googlevideo.com') && u.includes('.m3u8'));
                if (res) return res;
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
            if m3u8:
                clean = m3u8.replace("\\u0026", "&").replace("\\/", "/")
                if clean not in seen_urls:
                    return clean
        except Exception:
            pass
    return None
