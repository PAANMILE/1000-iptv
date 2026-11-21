import subprocess
import time

_UA_SET = False

def _ensure_ipad_user_agent():
    global _UA_SET
    if _UA_SET:
        return
    script = '''
    tell application "Safari" to activate
    delay 0.3
    tell application "System Events"
        tell process "Safari"
            try
                set uaMenu to menu 1 of menu item "User Agent" of menu 1 of menu bar item "Develop" of menu bar 1
                repeat with mi in menu items of uaMenu
                    set mName to name of mi as text
                    if mName contains "iPad" then
                        click mi
                        exit repeat
                    end if
                end repeat
            end try
        end tell
    end tell
    '''
    try:
        subprocess.run(["osascript", "-e", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        _UA_SET = True
    except Exception:
        pass

def fetch(driver, url, channel_name, seen_urls=None):
    if driver is None or not url:
        return None
    if seen_urls is None:
        seen_urls = set()

    _ensure_ipad_user_agent()

    try:
        driver.execute_script("performance.clearResourceTimings();")
    except Exception:
        pass

    driver.get(url)
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
