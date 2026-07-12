# YouTube Media Converter

A self-hosted web application that accepts a YouTube video URL and returns either:

- an **MP4 video** at a selected maximum resolution; or
- an **MP3 audio file** at 192 kbps.

The application is intended for private, authorized use. It runs locally in Docker, uses `yt-dlp` to retrieve media, FFmpeg to merge/remux/extract it, and Deno plus `yt-dlp-ejs` to handle YouTube's current JavaScript challenges.

> [!IMPORTANT]
> Use this application only for media you own, media for which you have permission from the rights holder, or media YouTube expressly authorizes you to download. Do not use it to bypass access controls, DRM, paywalls, private-video permissions, or other restrictions.

## Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project files](#project-files)
- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Generate a YouTube cookie file in Microsoft Edge](#generate-a-youtube-cookie-file-in-microsoft-edge)
- [Install the cookie file](#install-the-cookie-file)
- [Build the Docker image](#build-the-docker-image)
- [Run the application](#run-the-application)
- [Verify the installation](#verify-the-installation)
- [Using the website](#using-the-website)
- [Configuration](#configuration)
- [Container management](#container-management)
- [Updating the application](#updating-the-application)
- [Troubleshooting](#troubleshooting)
- [Security guidance](#security-guidance)
- [Production considerations](#production-considerations)
- [References](#references)

---

## Features

- YouTube URL validation
- MP4 output
- MP3 output at 192 kbps
- Maximum video-quality choices:
  - 1080p
  - 720p
  - 480p
  - 360p
- Best-available video/audio selection
- Preference for H.264/AAC when available
- Fallback to VP9, AV1, WebM, or other available streams
- FFmpeg remuxing to MP4
- FFmpeg audio extraction to MP3
- Deno JavaScript runtime
- `yt-dlp-ejs` challenge scripts
- Optional authenticated YouTube cookie file
- Playlist rejection
- Live/upcoming stream rejection
- Configurable duration limit
- Configurable file-size limit
- Basic in-memory per-IP rate limiting
- Temporary per-request storage
- Automatic cleanup after download delivery
- Browser security headers
- Health-check endpoint
- Clear error classification for common YouTube failures

## Architecture

```text
Browser
   |
   | HTTP request
   v
Flask / Gunicorn
   |
   | validate URL, limits, and authorization confirmation
   v
yt-dlp
   |---- YouTube cookies.txt, when configured
   |---- Deno runtime
   |---- yt-dlp-ejs challenge scripts
   |
   v
FFmpeg
   |---- merge/remux video to MP4
   |---- extract audio to MP3
   v
Temporary file
   |
   | browser download
   v
Automatic cleanup
```

The container includes:

| Component | Version in this build | Purpose |
|---|---:|---|
| Application | 1.0.6 | Web interface and conversion workflow |
| Python | 3.12 | Application runtime |
| Flask | 3.1.3 | Web framework |
| Gunicorn | 23.0.0 | Production WSGI server |
| yt-dlp | 2026.7.4 | YouTube extraction |
| yt-dlp-ejs | Installed through `yt-dlp[default]` | YouTube JavaScript challenge scripts |
| Deno | 2.9.2 | JavaScript challenge runtime |
| FFmpeg | Distribution package | Merge, remux, and audio conversion |

## Project files

```text
youtube_converter_website_v1.0.6/
├── .dockerignore
├── .gitignore
├── Dockerfile
├── LICENSE
├── README.md
├── app.py
└── requirements.txt
```

The HTML, CSS, JavaScript, Flask routes, validation, yt-dlp options, and conversion logic are contained in `app.py`.

## Prerequisites

This guide assumes:

- macOS
- Microsoft Edge
- Docker Desktop for Mac
- a terminal shell such as Terminal or iTerm2
- an authorized YouTube account/session when YouTube requires authentication

Check your Mac processor type:

```bash
uname -m
```

Results:

- `arm64` — Apple silicon
- `x86_64` — Intel

Install the matching Docker Desktop edition from Docker's official website.

### Confirm Docker Desktop is running

Start Docker Desktop:

```bash
open -a Docker
```

Verify the Docker engine:

```bash
docker info
```

A working result includes both `Client` and `Server` sections.

If Docker reports a missing socket such as:

```text
failed to connect to the docker API at unix:///Users/<username>/.docker/run/docker.sock
```

Docker Desktop is not running, has not completed startup, or the Docker context is incorrect.

Check contexts:

```bash
docker context ls
```

Use the Docker Desktop context when present:

```bash
docker context use desktop-linux
```

Clear environment overrides if necessary:

```bash
unset DOCKER_HOST
unset DOCKER_CONTEXT
```

Then retry:

```bash
docker info
```

## Quick start

After Docker Desktop is running and the cookie file has been generated:

```bash
cd ~/Downloads/youtube_converter_website_v1.0.6

docker build --no-cache --pull \
  -t youtube-converter:1.0.6 .

docker run --rm \
  --name youtube-converter-app \
  -p 8080:8080 \
  -e YTDLP_COOKIE_FILE=/run/secrets/youtube-cookies.txt \
  -v "$HOME/.youtube-converter/youtube-cookies.txt:/run/secrets/youtube-cookies.txt" \
  youtube-converter:1.0.6
```

Open:

```text
http://localhost:8080
```

Keep the Terminal window open while the application runs. Press `Control+C` to stop it.

---

# Generate a YouTube cookie file in Microsoft Edge

YouTube may return:

```text
Sign in to confirm you're not a bot
```

The Docker container cannot automatically read the browser profile on your Mac. The application therefore supports a Mozilla/Netscape-format `cookies.txt` file mounted into the container.

> [!CAUTION]
> A cookie export may grant access to the associated YouTube session. Treat it like a password. Never upload it to ChatGPT, email it, publish it, commit it to Git, or include it in a Docker image.

## 1. Install the correct cookie-export extension

Use **Get cookies.txt LOCALLY** from developer **kairi003**.

Official listing:

[Get cookies.txt LOCALLY — Chrome Web Store](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)

Do **not** install the older extension named only **Get cookies.txt**. The yt-dlp documentation notes that the older extension was reported as malware and removed from the Chrome Web Store.

### Open the Chrome Web Store in Edge

In a normal Microsoft Edge window, open:

```text
https://chromewebstore.google.com/
```

If Edge asks whether to allow extensions from other stores, select:

1. **Allow extensions from other stores**
2. **Allow**

Search for:

```text
Get cookies.txt LOCALLY
```

Before installing, confirm:

```text
Developer: kairi003
Extension ID: cclelndahbckbenkjhflpdbgdldlbecc
```

Install the extension.

## 2. Permit the extension in InPrivate mode

Edge disables extensions in InPrivate mode unless each extension is explicitly allowed.

In a normal Edge window, open:

```text
edge://extensions/
```

Then:

1. Find **Get cookies.txt LOCALLY**.
2. Select **Details**.
3. Enable **Allow in InPrivate**.
4. Optionally pin the extension to the toolbar.
5. Close all existing InPrivate windows.

## 3. Create a fresh private YouTube session

1. Open one new Edge InPrivate window.
2. Keep only one InPrivate tab open.
3. Sign in to YouTube.
4. In that same window and same tab, navigate to:

```text
https://www.youtube.com/robots.txt
```

The page will display plain text. That is expected.

YouTube rotates account cookies on open YouTube tabs. The yt-dlp project specifically recommends exporting from a fresh private session, navigating to `robots.txt` in the same tab, exporting the cookies, and then closing the private window permanently.

## 4. Export the cookies

While still on the `robots.txt` page:

1. Open **Get cookies.txt LOCALLY**.
2. Set the export format to **Netscape**.
3. Export cookies for `youtube.com` or the current site/domain.
4. Save the file as:

```text
youtube-cookies.txt
```

Save it initially in your Downloads folder:

```text
~/Downloads/youtube-cookies.txt
```

5. Close the entire InPrivate window immediately.
6. Do not reopen that private session.

Do not use this command to export the private-session cookies:

```bash
yt-dlp --cookies-from-browser edge --cookies cookies.txt
```

The yt-dlp YouTube guidance states that this method does not export cookies from the private/incognito YouTube session described above. Use the browser extension for that workflow.

## 5. Verify the cookie-file format

In Terminal:

```bash
head -1 "$HOME/Downloads/youtube-cookies.txt"
```

The first line must be one of:

```text
# Netscape HTTP Cookie File
```

or:

```text
# HTTP Cookie File
```

Confirm that the file contains YouTube entries without printing the cookie values:

```bash
grep -q 'youtube.com' "$HOME/Downloads/youtube-cookies.txt" \
  && echo "YouTube cookies found" \
  || echo "No YouTube cookies found"
```

On macOS and Linux, the file should use LF line endings.

---

# Install the cookie file

Create a private application directory:

```bash
mkdir -p "$HOME/.youtube-converter"
```

Copy the exported cookie file:

```bash
cp "$HOME/Downloads/youtube-cookies.txt" \
   "$HOME/.youtube-converter/youtube-cookies.txt"
```

Restrict host permissions:

```bash
chmod 600 "$HOME/.youtube-converter/youtube-cookies.txt"
```

Verify:

```bash
ls -l "$HOME/.youtube-converter/youtube-cookies.txt"
head -1 "$HOME/.youtube-converter/youtube-cookies.txt"
```

The working container command mounts this file without `:ro`. yt-dlp may update its cookie jar while processing. The application directory and file permissions limit exposure on the host.

---

# Build the Docker image

Go to the project directory:

```bash
cd ~/Downloads/youtube_converter_website_v1.0.6
```

Confirm that the expected files are present:

```bash
ls
```

Build a fresh image:

```bash
docker build --no-cache --pull \
  -t youtube-converter:1.0.6 .
```

The build output should show:

- Deno version
- yt-dlp version
- yt-dlp-ejs version
- FFmpeg installation

Using `--no-cache` prevents Docker from reusing an older `app.py` or dependency layer.

---

# Run the application

Stop any old container using the same name:

```bash
docker rm -f youtube-converter-app 2>/dev/null || true
```

Run the application:

```bash
docker run --rm \
  --name youtube-converter-app \
  -p 8080:8080 \
  -e YTDLP_COOKIE_FILE=/run/secrets/youtube-cookies.txt \
  -v "$HOME/.youtube-converter/youtube-cookies.txt:/run/secrets/youtube-cookies.txt" \
  youtube-converter:1.0.6
```

Open:

```text
http://localhost:8080
```

## Run without cookies

Some videos may work without authentication:

```bash
docker run --rm \
  --name youtube-converter-app \
  -p 8080:8080 \
  youtube-converter:1.0.6
```

If YouTube requests sign-in or bot confirmation, stop the container and use the cookie-enabled command.

## Run in the background

```bash
docker run -d \
  --name youtube-converter-app \
  --restart unless-stopped \
  -p 8080:8080 \
  -e YTDLP_COOKIE_FILE=/run/secrets/youtube-cookies.txt \
  -v "$HOME/.youtube-converter/youtube-cookies.txt:/run/secrets/youtube-cookies.txt" \
  youtube-converter:1.0.6
```

View logs:

```bash
docker logs -f youtube-converter-app
```

Stop it:

```bash
docker stop youtube-converter-app
```

Remove it:

```bash
docker rm youtube-converter-app
```

---

# Verify the installation

In another Terminal window:

```bash
curl http://localhost:8080/health
```

Expected fields include:

```json
{
  "app_version": "1.0.6",
  "cookies_configured": true,
  "deno_available": true,
  "deno_version": "deno 2.9.2",
  "ffmpeg": true,
  "yt_dlp_ejs_version": "0.x.x",
  "yt_dlp_version": "2026.7.4",
  "max_duration_seconds": 3600,
  "max_filesize_mb": 750
}
```

Interpretation:

| Field | Required value |
|---|---|
| `app_version` | `1.0.6` |
| `cookies_configured` | `true` when using cookies |
| `deno_available` | `true` |
| `deno_version` | Non-null |
| `ffmpeg` | `true` |
| `yt_dlp_ejs_version` | Non-null |
| `yt_dlp_version` | Non-null |

If the page footer does not show **Version 1.0.6**, an older image or container is running.

## Verify the cookie file inside the container

Check that the file exists and is readable:

```bash
docker exec youtube-converter-app \
  sh -c 'ls -l /run/secrets/youtube-cookies.txt &&
         test -r /run/secrets/youtube-cookies.txt &&
         echo "Cookie file is readable"'
```

Check only the header:

```bash
docker exec youtube-converter-app python -c \
'from pathlib import Path; p=Path("/run/secrets/youtube-cookies.txt"); print(p.open(encoding="utf-8-sig").readline().strip())'
```

Do not print the entire cookie file.

---

# Using the website

1. Open `http://localhost:8080`.
2. Paste a single YouTube video URL.
3. Select:
   - **MP4 video**, or
   - **MP3 audio**.
4. For MP4, select the maximum video quality.
5. Confirm that you are authorized to download and convert the content.
6. Select **Convert and download**.
7. Keep the browser page open until the file download begins.

## Supported URL hosts

- `youtube.com`
- `www.youtube.com`
- `m.youtube.com`
- `music.youtube.com`
- `youtu.be`

## Intentionally rejected

- playlists
- multi-video pages
- live streams
- upcoming streams
- non-YouTube hosts
- videos exceeding configured duration or size limits

---

# Configuration

The application reads these environment variables:

| Variable | Default | Description |
|---|---:|---|
| `PORT` | `8080` | Internal HTTP port |
| `YTDLP_COOKIE_FILE` | unset | Cookie-file path inside the container |
| `MAX_DURATION_SECONDS` | `3600` | Maximum accepted video duration |
| `MAX_FILESIZE_MB` | `750` | yt-dlp maximum file-size ceiling |
| `RATE_LIMIT` | `5` | Requests allowed per client in one window |
| `RATE_WINDOW_SECONDS` | `900` | Rate-limit window in seconds |

Example with a 30-minute duration limit and 500 MB size limit:

```bash
docker run --rm \
  --name youtube-converter-app \
  -p 8080:8080 \
  -e YTDLP_COOKIE_FILE=/run/secrets/youtube-cookies.txt \
  -e MAX_DURATION_SECONDS=1800 \
  -e MAX_FILESIZE_MB=500 \
  -e RATE_LIMIT=3 \
  -e RATE_WINDOW_SECONDS=900 \
  -v "$HOME/.youtube-converter/youtube-cookies.txt:/run/secrets/youtube-cookies.txt" \
  youtube-converter:1.0.6
```

The rate limiter is stored in application memory. It resets whenever the container restarts and is not coordinated across multiple containers.

---

# Container management

## Show running containers

```bash
docker ps
```

## Find the container using port 8080

```bash
docker ps --filter publish=8080
```

## Stop the application

```bash
docker stop youtube-converter-app
```

## Force-remove it

```bash
docker rm -f youtube-converter-app
```

## Show application logs

```bash
docker logs youtube-converter-app
```

Follow live logs:

```bash
docker logs -f youtube-converter-app
```

## Show local images

```bash
docker images | grep youtube-converter
```

## Remove an old image

```bash
docker image rm -f youtube-converter:1.0.6
```

## Check what is listening on port 8080

```bash
lsof -nP -iTCP:8080 -sTCP:LISTEN
```

---

# Updating the application

YouTube changes frequently. Keep Docker Desktop and the application dependencies current.

For a new packaged application version:

```bash
docker rm -f youtube-converter-app 2>/dev/null || true

cd /path/to/new/project

docker build --no-cache --pull \
  -t youtube-converter:<new-version> .
```

Run the new tag explicitly:

```bash
docker run --rm \
  --name youtube-converter-app \
  -p 8080:8080 \
  -e YTDLP_COOKIE_FILE=/run/secrets/youtube-cookies.txt \
  -v "$HOME/.youtube-converter/youtube-cookies.txt:/run/secrets/youtube-cookies.txt" \
  youtube-converter:<new-version>
```

Always verify `/health` before testing a conversion.

---

# Troubleshooting

## Docker API socket does not exist

Error:

```text
failed to connect to the docker API at unix:///Users/<username>/.docker/run/docker.sock
```

Resolution:

```bash
open -a Docker
docker info
docker context ls
docker context use desktop-linux
unset DOCKER_HOST
unset DOCKER_CONTEXT
docker info
```

Wait until Docker Desktop reports that the engine is running.

## `com.docker.vmnetd` malware warning

macOS may display:

```text
"com.docker.vmnetd" was not opened because it contains malware
```

Do not use **Open Anyway** for an unknown or old Docker installation.

Recommended recovery:

1. Confirm Docker came from Docker's official website.
2. Quit Docker Desktop and tools that may call Docker.
3. Use Docker Desktop **Troubleshoot → Uninstall**, or run:

   ```bash
   /Applications/Docker.app/Contents/MacOS/uninstall
   ```

4. Move any remaining `/Applications/Docker.app` to Trash.
5. Restart the Mac.
6. Download and install the current Docker Desktop release directly from Docker.
7. Start Docker and verify:

   ```bash
   open -a Docker
   docker info
   ```

Uninstalling Docker Desktop can remove local containers, images, and volumes. Back up anything important first.

## Port 8080 is already in use

Find the current container:

```bash
docker ps --filter publish=8080
```

Stop it:

```bash
docker rm -f youtube-converter-app
```

If a non-Docker process is using the port:

```bash
lsof -nP -iTCP:8080 -sTCP:LISTEN
```

Alternatively, map another host port:

```bash
docker run --rm \
  --name youtube-converter-app \
  -p 8081:8080 \
  -e YTDLP_COOKIE_FILE=/run/secrets/youtube-cookies.txt \
  -v "$HOME/.youtube-converter/youtube-cookies.txt:/run/secrets/youtube-cookies.txt" \
  youtube-converter:1.0.6
```

Then open:

```text
http://localhost:8081
```

## Old application version is still running

Check:

```bash
curl http://localhost:8080/health
```

If `app_version` is not `1.0.6`:

```bash
docker rm -f youtube-converter-app 2>/dev/null || true
docker image rm -f youtube-converter:1.0.6 2>/dev/null || true

docker build --no-cache --pull \
  -t youtube-converter:1.0.6 .
```

Make sure the build command is run from the directory containing the new `app.py` and `Dockerfile`.

## `FFmpegVideoConvertorPP` unexpected keyword error

Examples:

```text
unexpected keyword argument 'preferredformat'
```

or:

```text
unexpected keyword argument 'preferedformat'
```

These errors came from older application builds.

Resolution:

1. Confirm `/health` reports application version `1.0.6`.
2. Delete the old container and image.
3. Rebuild with `--no-cache`.
4. Do not copy an older `app.py` over version 1.0.6.

## Sign in to confirm you are not a bot

Error:

```text
Sign in to confirm you're not a bot
```

Resolution:

1. Generate a fresh private-session cookie file using the Edge instructions above.
2. Close the InPrivate window immediately after export.
3. Install the file at:

   ```text
   ~/.youtube-converter/youtube-cookies.txt
   ```

4. Restart the container with `YTDLP_COOKIE_FILE` and the bind mount.
5. Confirm:

   ```bash
   curl http://localhost:8080/health
   ```

   contains:

   ```json
   "cookies_configured": true
   ```

## Cookie file could not be read

Error:

```text
The configured cookie file could not be read
```

Check the host file:

```bash
ls -l "$HOME/.youtube-converter/youtube-cookies.txt"
head -1 "$HOME/.youtube-converter/youtube-cookies.txt"
```

Reapply permissions:

```bash
chmod 600 "$HOME/.youtube-converter/youtube-cookies.txt"
```

Confirm the Docker run command does not point to the Downloads copy or a misspelled path.

Verify inside the container:

```bash
docker exec youtube-converter-app \
  sh -c 'test -r /run/secrets/youtube-cookies.txt &&
         echo "Cookie file is readable"'
```

The proven working mount does not use `:ro`, because yt-dlp may update the cookie jar.

## Cookie file is not Netscape format

The first line must be:

```text
# Netscape HTTP Cookie File
```

or:

```text
# HTTP Cookie File
```

If it is not, repeat the export and select **Netscape** format.

Do not manually convert a JSON export by renaming it.

## Cookies worked and then stopped

YouTube can rotate or invalidate account cookies.

Generate a new file using a new InPrivate session:

1. Open a new InPrivate window.
2. Log into YouTube.
3. In the same tab, open `https://www.youtube.com/robots.txt`.
4. Export the `youtube.com` cookies in Netscape format.
5. Close the InPrivate window.
6. Replace the installed cookie file.
7. Restart the container.

```bash
cp "$HOME/Downloads/youtube-cookies.txt" \
   "$HOME/.youtube-converter/youtube-cookies.txt"

chmod 600 "$HOME/.youtube-converter/youtube-cookies.txt"

docker rm -f youtube-converter-app
```

Then rerun the normal Docker command.

## Requested format is not available

Error:

```text
Requested format is not available
```

Version 1.0.6 uses flexible selection and should normally fall back to available formats.

Check:

```bash
curl http://localhost:8080/health
docker logs youtube-converter-app
```

Confirm:

- `app_version` is `1.0.6`
- `deno_available` is `true`
- `yt_dlp_ejs_version` is not null
- cookies are current
- the selected video is playable in Edge with the same account and network

Try another quality selection.

## No usable video/audio combination

This often means YouTube's JavaScript challenge was not solved and the extractor saw an incomplete format list.

Confirm:

```bash
curl http://localhost:8080/health
```

Required:

```json
"deno_available": true
```

and a non-null:

```json
"yt_dlp_ejs_version": "..."
```

If either check fails, rebuild from the complete version 1.0.6 package. Replacing only `app.py` is not sufficient because Deno and dependency installation are defined in `Dockerfile` and `requirements.txt`.

## PO Token required

Some YouTube clients or formats may require a Proof of Origin token.

Check logs:

```bash
docker logs youtube-converter-app
```

If the log explicitly says a PO Token is required, cookies, Deno, and EJS may not be sufficient for that request. This basic application does not bundle a PO Token provider. Adding one requires a separate provider integration and additional security review.

## Video works in Edge but not in the app

Check:

- the Edge session and Docker host use the same public network/IP
- the cookie export is fresh
- the video is not private, members-only, paid, age-restricted beyond the account's permissions, or region-restricted
- the account can play the video normally in Edge
- the application logs do not show rate limiting or token requirements

View logs:

```bash
docker logs -f youtube-converter-app
```

## Conversion is slow

Conversion speed depends on:

- video duration
- selected resolution
- available YouTube codecs
- whether FFmpeg only remuxes or must perform more work
- network throughput
- YouTube throttling
- Mac CPU and storage performance

Leave the browser page and Terminal process open until the browser download begins.

## Large download fails

The default file-size ceiling is 750 MB.

Increase it:

```bash
-e MAX_FILESIZE_MB=1500
```

Also ensure Docker Desktop has sufficient disk space.

## Rate limit reached

Default:

- 5 conversions
- per client IP
- per 900 seconds

Either wait for the window to reset, restart the local container, or adjust:

```bash
-e RATE_LIMIT=10
-e RATE_WINDOW_SECONDS=900
```

Do not use high rates against YouTube. Excessive requests can lead to account or IP restrictions.

---

# Security guidance

## Cookie file

The cookie file may provide access to the YouTube account session.

- Never commit it to Git.
- Never copy it into the Docker image.
- Never paste its contents into an issue or chat.
- Never expose it through the web application.
- Store it outside the project directory.
- Restrict permissions with `chmod 600`.
- Delete and regenerate it if exposed.

The included `.gitignore` excludes common cookie filenames, but that is not a substitute for careful handling.

## Network exposure

The application is designed for local use.

The `-p 8080:8080` mapping can make the application reachable from other devices depending on host firewall and Docker networking settings. Do not expose it to the public internet without:

- authentication
- HTTPS
- a reverse proxy
- persistent/distributed rate limiting
- upload/download bandwidth controls
- job isolation
- malware scanning as appropriate
- observability and audit logging
- an abuse-reporting process
- a copyright and acceptable-use policy

For stricter localhost-only binding:

```bash
docker run --rm \
  --name youtube-converter-app \
  -p 127.0.0.1:8080:8080 \
  -e YTDLP_COOKIE_FILE=/run/secrets/youtube-cookies.txt \
  -v "$HOME/.youtube-converter/youtube-cookies.txt:/run/secrets/youtube-cookies.txt" \
  youtube-converter:1.0.6
```

## Temporary files

Each conversion uses a separate temporary directory. The application schedules deletion after the response closes and also removes the directory when a conversion fails.

Abnormal process termination can leave temporary data inside the disposable container. Removing the container removes its writable layer.

## Browser security headers

The application sets headers including:

- `X-Content-Type-Options`
- `Referrer-Policy`
- `X-Frame-Options`
- `Permissions-Policy`
- `Content-Security-Policy`
- `Cache-Control: no-store` for downloads

## Account risk

Automated access may cause YouTube to invalidate cookies, challenge the session, restrict the account, or restrict the source IP. Use low request volume and consider a dedicated account with no sensitive data.

---

# Production considerations

The current design is suitable for light, private use.

Before using it for multiple users or significant traffic, add:

- user authentication
- authorization and quotas
- a persistent rate limiter such as Redis
- a background job queue such as RQ or Celery
- isolated conversion workers
- object storage
- signed, expiring download URLs
- configurable retention
- reverse-proxy timeouts
- request-size and bandwidth controls
- structured logs and metrics
- centralized error tracking
- secrets management
- automated dependency scanning
- container image scanning
- legal review
- an acceptable-use policy
- a takedown and abuse process

The current HTTP request remains open while yt-dlp and FFmpeg work. A queue-based asynchronous architecture is preferable at scale.

---

# References

- [yt-dlp FAQ — passing cookies](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp)
- [yt-dlp YouTube extractor guidance — exporting YouTube cookies](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies)
- [yt-dlp EJS setup guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS)
- [yt-dlp project](https://github.com/yt-dlp/yt-dlp)
- [Get cookies.txt LOCALLY — Chrome Web Store](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)
- [Get cookies.txt LOCALLY — source code](https://github.com/kairi003/Get-cookies.txt-LOCALLY)
- [Docker Desktop installation on Mac](https://docs.docker.com/desktop/setup/install/mac-install/)
- [Docker Desktop uninstall instructions](https://docs.docker.com/desktop/uninstall/)
- [Docker bind mounts](https://docs.docker.com/engine/storage/bind-mounts/)
- [Docker Desktop troubleshooting](https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/)

---

## License

See `LICENSE`.

## Version

Application version: **1.0.6**

Documentation updated: **July 2026**
