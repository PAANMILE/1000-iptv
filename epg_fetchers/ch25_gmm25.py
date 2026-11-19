from .common import fetch_from_oned_epg
def fetch(tvg_id, channel_name, logo_url=""):
    return fetch_from_oned_epg("https://www.oned.net/live-tv/gmm25", tvg_id, channel_name, logo_url)
