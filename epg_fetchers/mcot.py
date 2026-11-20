from .common import fetch_from_trueid_epg

def fetch(tvg_id, channel_name, logo_url, driver=None, epg_url=None):
    slug = (epg_url or "").rstrip("/").split("/")[-1] or "9mcot-hd"
    return fetch_from_trueid_epg(slug, tvg_id, channel_name, logo_url)
