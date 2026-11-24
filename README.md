# Jim Cornette’s Drive-Thru — Full Archive RSS

This repository builds an independent RSS index of publicly available audio episodes in the Omny Studio playlist for **Jim Cornette’s Drive-Thru**. It uses Omny's documented, read-only Consumer API and retains Omny's original audio URLs; it does not download or rehost audio.

## Important limitation

This feed can include only episodes that Omny exposes through its public Consumer API for this playlist. It cannot restore deleted, private, or otherwise unpublished episodes. The feed is independently generated and is not affiliated with or endorsed by Jim Cornette, Arcadian Vanguard, or Omny Studio.

## Deploy to GitHub Pages

1. Create a new **public** GitHub repository (for example, `cornette-drive-thru-feed`).
2. Upload the contents of this folder to the repository's root. Make sure `.github/workflows/update-feed.yml` is included.
3. In the repository, open **Settings → Pages**.
4. Under **Build and deployment**, choose **Deploy from a branch**; select branch `main` and folder `/docs`; save.
5. Open **Actions → Update full-history podcast feed → Run workflow**. This first run builds `docs/feed.xml`.
6. Wait for the workflow to finish, then open the Pages address:
   `https://YOUR-USERNAME.github.io/YOUR-REPOSITORY/feed.xml`
7. Add that address to Pocket Casts: **Search → + → Add Podcast → By URL**. In Apple Podcasts, use **File → Follow a Show by URL** on Mac, or the equivalent URL-subscription option where available.

The workflow refreshes the feed daily and commits changes to `docs/feed.xml`.

## Local test

```bash
python3 -m pip install -r requirements.txt
python3 build_feed.py
```

The output is `docs/feed.xml`.

## Configuration

The default Omny identifiers are resolved from the public playlist JSON endpoint:
- Program slug: `jim-cornette-s-drive-thru`
- Playlist slug: `podcast`

Optional environment variables:
- `OMNY_PROGRAM_SLUG`
- `OMNY_PLAYLIST_SLUG`
- `OMNY_PAGE_SIZE` (default 100)
- `RSS_OUTPUT` (default `docs/feed.xml`)
- `PUBLIC_FEED_URL`

## Troubleshooting

- If the workflow fails, inspect its log under **Actions**. Omny may change its public API or the playlist metadata route.
- If the resulting feed contains fewer entries than the Omny playlist page's displayed clip count, some clips may be non-audio entries or may not expose an audio URL in the public API response.
- If Pages returns 404, verify that Pages is configured to publish `main` / `docs`, and that the workflow has completed successfully.
- Podcast apps may take time to refresh a newly added feed. If it imports only a partial list, check the app's episode limit / download settings.

## Data and API

Omny documents its Consumer API as read-only and limited to publicly published content. The playlist clips endpoint supports cursor pagination and a `pageSize` parameter. See https://api.omny.fm/ for the current API documentation.
