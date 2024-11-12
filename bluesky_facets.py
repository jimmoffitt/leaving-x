# bluesky_facets.py
import re
import requests
from typing import List, Dict

def parse_mentions(text: str) -> List[Dict]:
    spans = []
    mention_regex = rb"[$|\W](@([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)"
    text_bytes = text.encode("UTF-8")
    for m in re.finditer(mention_regex, text_bytes):
        spans.append({
            "start": m.start(1),
            "end": m.end(1),
            "handle": m.group(1)[1:].decode("UTF-8")
        })
    return spans

def parse_urls(text: str) -> List[Dict]:
    spans = []
    url_regex = rb"[$|\W](https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*[-a-zA-Z0-9@%_\+~#//=])?)"
    text_bytes = text.encode("UTF-8")
    for m in re.finditer(url_regex, text_bytes):
        spans.append({
            "start": m.start(1),
            "end": m.end(1),
            "url": m.group(1).decode("UTF-8"),
        })
    return spans

def parse_facets(text: str, pds_url: str) -> List[Dict]:
    facets = []
    for mention in parse_mentions(text):
        resp = requests.get(
            pds_url + "/xrpc/com.atproto.identity.resolveHandle",
            params={"handle": mention["handle"]},
        )
        if resp.status_code == 400:
            continue
        did = resp.json().get("did")
        facets.append({
            "index": {
                "byteStart": mention["start"],
                "byteEnd": mention["end"],
            },
            "features": [{"$type": "app.bsky.richtext.facet#mention", "did": did}],
        })
    for url in parse_urls(text):
        facets.append({
            "index": {
                "byteStart": url["start"],
                "byteEnd": url["end"],
            },
            "features": [
                {
                    "$type": "app.bsky.richtext.facet#link",
                    "uri": url["url"],
                }
            ],
        })
    return facets
