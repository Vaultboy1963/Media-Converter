# YouTube Media Converter 1.0.6

This build adds the current YouTube JavaScript challenge prerequisites:

- Deno runtime
- `yt-dlp-ejs`
- `yt-dlp[default]`
- Health diagnostics for Deno, yt-dlp, and yt-dlp-ejs
- Better error classification for JavaScript challenge and PO Token failures

Use this application only for media you own, have permission to download, or
that YouTube expressly authorizes for download.

## Build

```bash
docker rm -f youtube-converter-app 2>/dev/null || true
docker build --no-cache --pull -t youtube-converter:1.0.6 .
```

## Run with cookies

```bash
docker run --rm \
  --name youtube-converter-app \
  -p 8080:8080 \
  -e YTDLP_COOKIE_FILE=/run/secrets/youtube-cookies.txt \
  -v "$HOME/.youtube-converter/youtube-cookies.txt:/run/secrets/youtube-cookies.txt" \
  youtube-converter:1.0.6
```

## Verify

```bash
curl http://localhost:8080/health
```

The response should include values similar to:

```json
{
  "app_version": "1.0.6",
  "cookies_configured": true,
  "deno_available": true,
  "deno_version": "deno 2.9.2",
  "ffmpeg": true,
  "yt_dlp_ejs_version": "0.x.x",
  "yt_dlp_version": "2026.7.4"
}
```

If `deno_available` is false or `yt_dlp_ejs_version` is null, the image was not
rebuilt from this package.

## View detailed yt-dlp warnings

```bash
docker logs youtube-converter-app
```

If the log specifically says formats require a PO Token, cookies and Deno are
not sufficient for that YouTube session. PO Token support requires a separate
provider integration and is intentionally not bundled into this basic app.
