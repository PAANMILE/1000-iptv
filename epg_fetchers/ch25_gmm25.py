from .common import fetch_from_gmm25_api
def fetch(tvg_id, channel_name, logo_url=""):
    return fetch_from_gmm25_api(tvg_id, channel_name, logo_url)
