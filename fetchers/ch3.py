from .common import sniff_stream
def fetch(driver, url, channel_name, seen_urls=None):
    return sniff_stream(driver, url, channel_name, seen_urls)
