import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
CHANNELS_FILE = BASE_DIR / "channels.json"
OUTPUT_FILE = BASE_DIR / "true_tv.m3u"

# 1. โหมดทดสอบในเครื่อง (Local LAN)
# BASE_LOGO_URL = "http://192.168.1.10:8080/logos"

# 2. โหมด GitHub (เมื่อพร้อมอัปขึ้น GitHub ให้เอา # ด้านหน้าบรรทัดล่างออก และใส่ # หน้าบรรทัดบนแทน)
BASE_LOGO_URL = "https://raw.githubusercontent.com/PAANMILE/true-iptv/main/logos"

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REFERER = "https://tv.trueid.net/"

def fetch_m3u8_url(context, target_url, channel_name):
    page = context.new_page()
    found_url = None

    def handle_request(request):
        nonlocal found_url
        url = request.url
        if "playlist.m3u8" in url and "appid=trueid" in url and not found_url:
            found_url = url

    page.on("request", handle_request)

    try:
        print(f"⏳ กำลังดึงลิงก์: {channel_name} ...")
        page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
        
        start_time = time.time()
        while not found_url and (time.time() - start_time) < 15:
            page.wait_for_timeout(500)
            
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดที่ช่อง {channel_name}: {e}")
    finally:
        page.close()

    return found_url

def main():
    if not CHANNELS_FILE.exists():
        print("❌ ไม่พบไฟล์ channels.json")
        return

    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        channels = json.load(f)

    m3u_lines = [
        '#EXTM3U url-tvg="https://raw.githubusercontent.com/PAANMILE/my-iptv/main/my_epg.xml"'
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT)

        for ch in channels:
            stream_url = fetch_m3u8_url(context, ch["url"], ch["name"])
            if stream_url:
                print(f"✅ สำเร็จ: {ch['name']}")
                logo_file = ch.get("logo", "")
                logo_url = f"{BASE_LOGO_URL}/{logo_file}" if logo_file else ""
                
                extinf = (
                    f'#EXTINF:-1 tvg-chno="{ch.get("chno", "")}" '
                    f'tvg-id="{ch.get("tvg_id", "")}" '
                    f'tvg-name="{ch["name"]}" '
                    f'tvg-logo="{logo_url}" '
                    f'group-title="{ch.get("group", "TrueID")}",{ch["name"]}'
                )
                m3u_lines.append(extinf)
                m3u_lines.append(f"#EXTVLCOPT:http-user-agent={USER_AGENT}")
                m3u_lines.append(f"#EXTVLCOPT:http-referrer={REFERER}")
                m3u_lines.append(stream_url)
            else:
                print(f"⚠️ ไม่พบลิงก์สตรีมสำหรับ: {ch['name']}")

        browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(m3u_lines) + "\n")

    print(f"\n🎉 บันทึกไฟล์เรียบร้อยที่: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
