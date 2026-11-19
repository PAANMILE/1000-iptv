from .common import fetch_from_trueid_epg

def fetch(tvg_id, channel_name, logo_url, driver=None, epg_url=None):
    ch_elem, progs = fetch_from_trueid_epg("9mcot-hd", tvg_id, channel_name, logo_url, epg_url=epg_url)
    return ch_elem, progs
