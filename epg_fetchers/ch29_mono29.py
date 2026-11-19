from .common import fetch_from_xml_sources
def fetch(tvg_id, channel_name, logo_url=""):
    return fetch_from_xml_sources(tvg_id, channel_name, logo_url, ["MONO.th", "MONO29.th"])
