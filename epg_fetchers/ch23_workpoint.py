from .common import fetch_from_trueid_epg
def fetch(tvg_id, channel_name, logo_url="", epg_url=None):
    return fetch_from_trueid_epg("workpointtv", tvg_id, channel_name, logo_url)
