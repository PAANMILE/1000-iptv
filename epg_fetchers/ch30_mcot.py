from .common import fetch_from_trueid_epg, fetch_from_xml_sources

def fetch(tvg_id, channel_name, logo_url, driver=None, epg_url=None):
    ch_elem, progs = fetch_from_trueid_epg("9mcot-hd", tvg_id, channel_name, logo_url, epg_url=epg_url)
    if not progs:
        return fetch_from_xml_sources(tvg_id, channel_name, logo_url, ["MCOT.HD.th"])
    return ch_elem, progs
