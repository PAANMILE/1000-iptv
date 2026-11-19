import sys
import time
import fetch_streams
import fetch_epg

def main():
    start_time = time.time()
    force_update = "--force" in sys.argv
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
