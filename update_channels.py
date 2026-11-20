import os
import shutil
import sys
import time
import fetch_streams
import fetch_epg

def main():
    start_time = time.time()
    force_update = "--force" in sys.argv
    if force_update:
        cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "epg_cache")
        shutil.rmtree(cache_dir, ignore_errors=True)
        os.makedirs(cache_dir, exist_ok=True)
    driver = None
    try:
        driver = fetch_streams.run(force_update=force_update, driver=driver)
        print("")
        driver = fetch_epg.run(force_update=force_update, driver=driver)
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
    elapsed = time.time() - start_time
    print(f"\n⏱️  Total execution time: {elapsed:.1f} seconds")

if __name__ == "__main__":
    main()
