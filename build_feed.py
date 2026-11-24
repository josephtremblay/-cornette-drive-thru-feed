#!/usr/bin/env python3
"""Build a full-history RSS feed from the publicly available Omny Studio playlist."""
import html
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import urlencode

import requests

PROGRAM_SLUG = os.getenv("OMNY_PROGRAM_SLUG", "jim-cornette-s-drive-thru")
PLAYLIST_SLUG = os.getenv("OMNY_PLAYLIST_SLUG", "podcast")
OUTFILE = os.getenv("RSS_OUTPUT", "docs/feed.xml")
PAGE_SIZE = int(os.getenv("OMNY_PAGE_SIZE", "100"))
BASE = "https://api.omny.fm"
HEADERS = {"User-Agent": "JimCornetteDriveThruArchiveFeed/1.0 (+personal RSS archive)"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def get_json(url, params=None):
    response = SESSION.get(url, params=params, timeout=45)
    response.raise_for_status()
    return response.json()


def text_value(obj, *keys, default=""):
    for key in keys:
        value = obj.get(key)
        if value is not None and value != "":
            return value
    return default


def main():
    # Omny documents the .json suffix as a convenience route for playlist metadata.
    playlist_url = f"https://omny.fm/shows/{PROGRAM_SLUG}/playlists/{PLAYLIST_SLUG}.json"
    playlist = get_json(playlist_url)

    org_id = text_value(playlist, "OrganizationId", "organizationId")
    playlist_id = text_value(playlist, "Id", "id")
    if not org_id or not playlist_id:
        raise RuntimeError(
            "Omny playlist metadata did not contain OrganizationId and Id. "
            f"Returned fields: {', '.join(playlist.keys())}"
        )

    endpoint = f"{BASE}/orgs/{org_id}/playlists/{playlist_id}/clips"
    cursor = None
    clips = []
    seen_cursors = set()

    # Omny's documented playlist-clips endpoint supports cursor + pageSize.
    while True:
        params = {"pageSize": PAGE_SIZE}
        if cursor:
            params["cursor"] = cursor
        payload = get_json(endpoint, params=params)
        batch = payload.get("Clips") or payload.get("clips") or []
        clips.extend(batch)
        next_cursor = text_value(payload, "Cursor", "cursor")
        if not next_cursor or next_cursor == cursor or next_cursor in seen_cursors:
            break
        seen_cursors.add(next_cursor)
        cursor = next_cursor
        time.sleep(0.15)

    # De-duplicate by immutable Omny clip ID.
    unique = {}
    for clip in clips:
        clip_id = text_value(clip, "Id", "id")
        if clip_id:
            unique[clip_id] = clip
    clips = list(unique.values())

    def published(clip):
        raw = text_value(clip, "PublishedUtc", "publishedUtc")
        if not raw:
            return datetime(1970, 1, 1, tzinfo=timezone.utc)
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return datetime(1970, 1, 1, tzinfo=timezone.utc)

    clips.sort(key=published)  # oldest first for archive-friendly browsing

    channel_title = text_value(playlist, "Title", default="Jim Cornette’s Drive-Thru")
    channel_desc = text_value(
        playlist, "Description", "Summary",
        default="The publicly available historical episode archive for Jim Cornette’s Drive-Thru."
    )
    artwork = text_value(playlist, "ArtworkUrl", "ImageUrl")
    feed_url = os.getenv("PUBLIC_FEED_URL", "https://YOUR-GITHUB-USERNAME.github.io/YOUR-REPOSITORY/feed.xml")
    site_url = f"https://omny.fm/shows/{PROGRAM_SLUG}/playlists/{PLAYLIST_SLUG}"

    ET.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
    ET.register_namespace("atom", "http://www.w3.org/2005/Atom")
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    def add(parent, tag, value):
        el = ET.SubElement(parent, tag)
        el.text = str(value or "")
        return el

    add(channel, "title", channel_title + " — Full Archive")
    add(channel, "link", site_url)
    add(channel, "description", channel_desc + " This independent feed indexes publicly available episodes hosted by Omny Studio.")
    add(channel, "language", text_value(playlist, "Language", default="en-us"))
    add(channel, "lastBuildDate", format_datetime(datetime.now(timezone.utc)))
    add(channel, "generator", "Personal Omny-to-RSS archive generator")
    add(channel, "atom:link", feed_url)
    # Register atom namespace for a standards-compliant self link.
    channel.remove(channel[-1])
    atom = ET.SubElement(channel, "{http://www.w3.org/2005/Atom}link",
                         {"href": feed_url, "rel": "self", "type": "application/rss+xml"})
    if artwork:
        image = ET.SubElement(channel, "image")
        add(image, "url", artwork)
        add(image, "title", channel_title)
        add(image, "link", site_url)

    for clip in clips:
        title = text_value(clip, "Title", default="Untitled episode")
        clip_id = text_value(clip, "Id", "id")
        media = clip.get("MediaUrls") or clip.get("mediaUrls") or {}
        audio_url = text_value(media, "AudioUrl", "audioUrl") or text_value(clip, "AudioUrl", "audioUrl")
        if not audio_url:
            # Do not publish non-audio playlist entries as podcast episodes.
            continue
        item = ET.SubElement(channel, "item")
        add(item, "title", title)
        desc = text_value(clip, "DescriptionHtml", "Description", "Summary")
        description = ET.SubElement(item, "description")
        description.text = desc
        pub = published(clip)
        add(item, "pubDate", format_datetime(pub))
        guid = ET.SubElement(item, "guid", {"isPermaLink": "false"})
        guid.text = clip_id
        enclosure = ET.SubElement(item, "enclosure", {
            "url": audio_url,
            "type": text_value(clip, "AudioMimeType", default="audio/mpeg"),
        })
        size = text_value(clip, "PublishedAudioSizeInBytes", "AudioSizeInBytes")
        if size:
            enclosure.set("length", str(size))
        duration = text_value(clip, "DurationSeconds")
        if duration:
            ET.SubElement(item, "{http://www.itunes.com/dtds/podcast-1.0.dtd}duration").text = str(duration)
        episode_url = text_value(clip, "PublishedUrl", "ShareUrl")
        if episode_url:
            add(item, "link", episode_url)
        image_url = text_value(clip, "ImageUrl")
        if image_url:
            ET.SubElement(item, "{http://www.itunes.com/dtds/podcast-1.0.dtd}image", {"href": image_url})

    ET.indent(rss, space="  ")
    os.makedirs(os.path.dirname(OUTFILE) or ".", exist_ok=True)
    ET.ElementTree(rss).write(OUTFILE, encoding="utf-8", xml_declaration=True)
    print(f"Wrote {OUTFILE}; indexed {len(clips)} unique public playlist clips.")


if __name__ == "__main__":
    main()
