from .common import sniff_oned
def fetch(driver, url, channel_name, seen_urls=None):
    return sniff_oned(driver, url, channel_name, seen_urls)
