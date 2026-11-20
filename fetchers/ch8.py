from .common import sniff_trueid
def fetch(driver, url, channel_name, seen_urls=None):
    return sniff_trueid(driver, url, channel_name, seen_urls)
