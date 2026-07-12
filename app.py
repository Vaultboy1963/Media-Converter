from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
import time
from collections import defaultdict, deque
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from urllib.parse import urlparse

import yt_dlp
from flask import Flask, Response, jsonify, render_template_string, request, send_file
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config.update(
    MAX_DURATION_SECONDS=int(os.getenv("MAX_DURATION_SECONDS", "3600")),
    MAX_FILESIZE_MB=int(os.getenv("MAX_FILESIZE_MB", "750")),
    RATE_LIMIT=int(os.getenv("RATE_LIMIT", "5")),
    RATE_WINDOW_SECONDS=int(os.getenv("RATE_WINDOW_SECONDS", "900")),
)

ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}

ALLOWED_FORMATS = {"mp4", "mp3"}
ALLOWED_QUALITIES = {"1080", "720", "480", "360"}

APP_VERSION = "1.0.6"

_rate_lock = threading.Lock()
_rate_events: dict[str, deque[float]] = defaultdict(deque)


PAGE = r"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>YouTube Media Converter</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #070b15;
      --panel: rgba(18, 25, 43, .88);
      --panel-2: #111a2d;
      --text: #f5f7ff;
      --muted: #aeb9cf;
      --line: rgba(255,255,255,.12);
      --accent: #7c5cff;
      --accent-2: #25c2a0;
      --danger: #ff6b7a;
      --shadow: 0 28px 80px rgba(0,0,0,.42);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 15% 15%, rgba(124,92,255,.22), transparent 34rem),
        radial-gradient(circle at 85% 75%, rgba(37,194,160,.16), transparent 30rem),
        var(--bg);
    }

    .shell {
      width: min(960px, calc(100% - 32px));
      margin: 0 auto;
      padding: 56px 0;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 28px;
      font-weight: 800;
      letter-spacing: -.02em;
    }

    .logo {
      width: 42px;
      height: 42px;
      display: grid;
      place-items: center;
      border-radius: 14px;
      background: linear-gradient(135deg, var(--accent), #a590ff);
      box-shadow: 0 10px 30px rgba(124,92,255,.34);
    }

    .panel {
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 28px;
      background: var(--panel);
      backdrop-filter: blur(22px);
      box-shadow: var(--shadow);
    }

    .hero {
      padding: clamp(30px, 6vw, 64px);
      border-bottom: 1px solid var(--line);
    }

    .eyebrow {
      display: inline-flex;
      gap: 8px;
      align-items: center;
      padding: 7px 11px;
      border: 1px solid rgba(124,92,255,.32);
      border-radius: 999px;
      background: rgba(124,92,255,.1);
      color: #cfc6ff;
      font-size: 13px;
      font-weight: 700;
    }

    h1 {
      max-width: 760px;
      margin: 18px 0 14px;
      font-size: clamp(36px, 6vw, 68px);
      line-height: .98;
      letter-spacing: -.055em;
    }

    .lead {
      max-width: 680px;
      margin: 0;
      color: var(--muted);
      font-size: clamp(17px, 2.4vw, 20px);
      line-height: 1.6;
    }

    form {
      display: grid;
      gap: 22px;
      padding: clamp(26px, 5vw, 52px);
    }

    label.title {
      display: block;
      margin-bottom: 9px;
      font-size: 14px;
      font-weight: 760;
    }

    input[type="url"], select {
      width: 100%;
      min-height: 54px;
      padding: 0 16px;
      color: var(--text);
      border: 1px solid var(--line);
      border-radius: 15px;
      outline: none;
      background: var(--panel-2);
      font: inherit;
      transition: border-color .2s, box-shadow .2s;
    }

    input[type="url"]:focus, select:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 4px rgba(124,92,255,.16);
    }

    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }

    .check {
      display: grid;
      grid-template-columns: 20px 1fr;
      gap: 11px;
      align-items: start;
      padding: 16px;
      border: 1px solid var(--line);
      border-radius: 15px;
      background: rgba(255,255,255,.025);
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }

    .check input {
      width: 18px;
      height: 18px;
      margin: 1px 0 0;
      accent-color: var(--accent);
    }

    button {
      min-height: 58px;
      border: 0;
      border-radius: 16px;
      color: white;
      background: linear-gradient(135deg, var(--accent), #5f8dff);
      box-shadow: 0 16px 34px rgba(93,97,255,.28);
      font: inherit;
      font-weight: 800;
      cursor: pointer;
      transition: transform .16s ease, filter .16s ease;
    }

    button:hover { transform: translateY(-2px); filter: brightness(1.07); }
    button:disabled { cursor: wait; opacity: .72; transform: none; }

    .status {
      display: none;
      align-items: center;
      gap: 12px;
      color: var(--muted);
      font-size: 14px;
    }

    .status.show { display: flex; }

    .spinner {
      width: 21px;
      height: 21px;
      flex: 0 0 auto;
      border: 3px solid rgba(255,255,255,.15);
      border-top-color: var(--accent-2);
      border-radius: 50%;
      animation: spin .75s linear infinite;
    }

    .error {
      margin: 0 clamp(26px, 5vw, 52px) 28px;
      padding: 14px 16px;
      border: 1px solid rgba(255,107,122,.35);
      border-radius: 14px;
      color: #ffd4d9;
      background: rgba(255,107,122,.09);
      line-height: 1.45;
    }

    .notes {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1px;
      background: var(--line);
      border-top: 1px solid var(--line);
    }

    .note {
      padding: 22px;
      background: rgba(10,15,27,.92);
    }

    .note strong { display: block; margin-bottom: 6px; }
    .note span { color: var(--muted); font-size: 13px; line-height: 1.45; }

    footer {
      padding-top: 20px;
      text-align: center;
      color: #7f8ba2;
      font-size: 12px;
    }

    @keyframes spin { to { transform: rotate(360deg); } }

    @media (max-width: 700px) {
      .shell { padding: 28px 0; }
      .grid, .notes { grid-template-columns: 1fr; }
      .notes { gap: 0; }
      .note + .note { border-top: 1px solid var(--line); }
    }
  </style>
</head>
<body>
  <main class="shell">
    <div class="brand">
      <div class="logo" aria-hidden="true">▶</div>
      <span>Media Converter</span>
    </div>

    <section class="panel">
      <header class="hero">
        <div class="eyebrow">Self-hosted conversion tool</div>
        <h1>Convert an authorized YouTube video.</h1>
        <p class="lead">Paste a YouTube link, choose MP4 video or MP3 audio, and receive the converted file directly in your browser.</p>
      </header>

      <form id="converter" method="post" action="/convert">
        <div>
          <label class="title" for="url">YouTube URL</label>
          <input id="url" name="url" type="url" required autocomplete="off"
                 placeholder="https://www.youtube.com/watch?v=..." value="{{ submitted_url }}">
        </div>

        <div class="grid">
          <div>
            <label class="title" for="format">Output format</label>
            <select id="format" name="format">
              <option value="mp4">MP4 video</option>
              <option value="mp3">MP3 audio</option>
            </select>
          </div>
          <div id="quality-wrap">
            <label class="title" for="quality">Maximum video quality</label>
            <select id="quality" name="quality">
              <option value="1080">1080p</option>
              <option value="720" selected>720p</option>
              <option value="480">480p</option>
              <option value="360">360p</option>
            </select>
          </div>
        </div>

        <label class="check">
          <input type="checkbox" name="rights_confirmed" value="yes" required>
          <span>I own this content, have the rights holder's permission, or YouTube expressly provides a download right for it.</span>
        </label>

        <button id="submit" type="submit">Convert and download</button>

        <div id="status" class="status" role="status" aria-live="polite">
          <div class="spinner" aria-hidden="true"></div>
          <span>Downloading and converting. Keep this page open until your browser starts the file download.</span>
        </div>
      </form>

      {% if error %}
      <div class="error" role="alert">{{ error }}</div>
      {% endif %}

      <div class="notes">
        <div class="note"><strong>Single videos only</strong><span>Playlists and live streams are intentionally rejected.</span></div>
        <div class="note"><strong>Private by design</strong><span>Files are stored temporarily and removed after delivery.</span></div>
        <div class="note"><strong>YouTube challenge support</strong><span>Deno and yt-dlp-ejs are included to solve current JavaScript player challenges.</span></div>
      </div>
    </section>

    <footer>Version {{ app_version }} · Use only for content you are legally authorized to download and convert.</footer>
  </main>

  <script>
    const form = document.getElementById("converter");
    const format = document.getElementById("format");
    const qualityWrap = document.getElementById("quality-wrap");
    const button = document.getElementById("submit");
    const status = document.getElementById("status");

    function syncFormat() {
      qualityWrap.style.display = format.value === "mp3" ? "none" : "block";
    }

    format.addEventListener("change", syncFormat);
    syncFormat();

    form.addEventListener("submit", () => {
      button.disabled = true;
      button.textContent = "Processing…";
      status.classList.add("show");

      // Re-enable eventually so a browser/network error does not permanently lock the form.
      setTimeout(() => {
        button.disabled = false;
        button.textContent = "Convert and download";
        status.classList.remove("show");
      }, 15 * 60 * 1000);
    });
  </script>
</body>
</html>
"""



class YTDLPLogCapture:
    """Capture yt-dlp warnings/errors for a clearer browser message."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def _add(self, level: str, message: object) -> None:
        text = str(message).strip()
        if text:
            self.messages.append(f"{level}: {text}")

    def debug(self, message: object) -> None:
        # yt-dlp may route normal output through debug; keep it for diagnostics.
        self._add("debug", message)

    def info(self, message: object) -> None:
        self._add("info", message)

    def warning(self, message: object) -> None:
        self._add("warning", message)

    def error(self, message: object) -> None:
        self._add("error", message)

    def combined(self) -> str:
        return "\n".join(self.messages)


def installed_package_version(name: str) -> str | None:
    try:
        return package_version(name)
    except PackageNotFoundError:
        return None


def executable_version(executable: str) -> str | None:
    path = shutil.which(executable)
    if not path:
        return None
    try:
        completed = subprocess.run(
            [path, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    first_line = (completed.stdout or completed.stderr).splitlines()
    return first_line[0].strip() if first_line else None


def client_key() -> str:
    # Only trust request.remote_addr unless a trusted reverse proxy is configured.
    return request.remote_addr or "unknown"


def rate_limit_ok(key: str) -> bool:
    now = time.monotonic()
    window = app.config["RATE_WINDOW_SECONDS"]
    limit = app.config["RATE_LIMIT"]

    with _rate_lock:
        events = _rate_events[key]
        while events and now - events[0] > window:
            events.popleft()
        if len(events) >= limit:
            return False
        events.append(now)
        return True


def valid_youtube_url(value: str) -> bool:
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return False

    return (
        parsed.scheme in {"http", "https"}
        and (parsed.hostname or "").lower() in ALLOWED_HOSTS
        and bool(parsed.path)
        and parsed.username is None
        and parsed.password is None
    )


def media_filter(info: dict, *, incomplete: bool) -> str | None:
    if info.get("is_live") or info.get("live_status") in {"is_live", "is_upcoming"}:
        return "Live and upcoming streams are not supported."

    duration = info.get("duration")
    max_duration = app.config["MAX_DURATION_SECONDS"]
    if duration and duration > max_duration:
        minutes = max_duration // 60
        return f"Video exceeds the configured {minutes}-minute duration limit."

    # Reject playlist/channel extraction even if an unusual URL bypasses normal URL shape checks.
    if info.get("_type") in {"playlist", "multi_video"}:
        return "Playlists and multi-video pages are not supported."

    return None


def find_output_file(job_dir: Path, extension: str) -> Path:
    candidates = [
        path for path in job_dir.iterdir()
        if path.is_file()
        and path.suffix.lower() == f".{extension}"
        and not path.name.endswith((".part", ".ytdl"))
    ]
    if not candidates:
        raise RuntimeError(f"The conversion completed but no {extension.upper()} output was found.")
    return max(candidates, key=lambda path: path.stat().st_size)



def configured_cookie_file() -> str | None:
    """Return a validated yt-dlp cookie file path, when configured."""
    configured = os.getenv("YTDLP_COOKIE_FILE", "").strip()
    if not configured:
        return None

    cookie_path = Path(configured)
    if not cookie_path.is_file():
        raise RuntimeError(
            "YTDLP_COOKIE_FILE is configured, but the cookie file is missing "
            "or is not readable inside the container."
        )

    try:
        with cookie_path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            first_line = handle.readline().strip()
    except OSError as exc:
        raise RuntimeError("The configured cookie file could not be read.") from exc

    if first_line not in {"# HTTP Cookie File", "# Netscape HTTP Cookie File"}:
        raise RuntimeError(
            "The configured cookie file is not in Mozilla/Netscape cookies.txt format."
        )

    return str(cookie_path)


def build_options(
    job_dir: Path,
    output_format: str,
    quality: str,
    logger: YTDLPLogCapture,
) -> dict:
    max_bytes = app.config["MAX_FILESIZE_MB"] * 1024 * 1024
    output_template = str(job_dir / "%(title).160B-%(id)s.%(ext)s")

    common = {
        "outtmpl": output_template,
        "noplaylist": True,
        "playlistend": 1,
        "match_filter": media_filter,
        "max_filesize": max_bytes,
        "restrictfilenames": True,
        "windowsfilenames": True,
        "cachedir": False,
        "quiet": True,
        "no_warnings": True,
        "retries": 3,
        "fragment_retries": 3,
        "socket_timeout": 30,
        "concurrent_fragment_downloads": 4,
        "overwrites": True,
        "logger": logger,
        # yt-dlp uses Deno by default, but the explicit path makes container
        # diagnostics deterministic and avoids PATH differences.
        "js_runtimes": {
            "deno": {"path": shutil.which("deno") or "/usr/local/bin/deno"},
        },
    }

    cookie_file = configured_cookie_file()
    if cookie_file:
        common["cookiefile"] = cookie_file

    if output_format == "mp3":
        return {
            **common,
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }

    # Do not hard-require MP4/H.264 streams. Some YouTube videos expose only
    # VP9/AV1/WebM or otherwise unusual format combinations. Select the best
    # available video/audio at or below the requested height, prefer broadly
    # compatible H.264/AAC streams when they exist, then remux to MP4.
    format_selector = (
        f"bv*[height<=?{quality}]+ba/"
        f"b[height<=?{quality}]/"
        f"b"
    )

    return {
        **common,
        "format": format_selector,
        "format_sort": [
            "vcodec:h264",
            "lang",
            "quality",
            f"res:{quality}",
            "fps",
            "hdr:12",
            "acodec:aac",
        ],
        "merge_output_format": "mp4",
        "postprocessors": [{
            "key": "FFmpegVideoRemuxer",
            # yt-dlp's public postprocessor API intentionally uses this
            # historical spelling.
            "preferedformat": "mp4",
        }],
    }


@app.after_request
def security_headers(response: Response) -> Response:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
    )
    return response


@app.get("/")
def index():
    return render_template_string(PAGE, error=None, submitted_url="", app_version=APP_VERSION)


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "app_version": APP_VERSION,
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "deno_available": bool(shutil.which("deno")),
        "deno_version": executable_version("deno"),
        "yt_dlp_version": installed_package_version("yt-dlp"),
        "yt_dlp_ejs_version": installed_package_version("yt-dlp-ejs"),
        "cookies_configured": bool(
            os.getenv("YTDLP_COOKIE_FILE", "").strip()
            and Path(os.getenv("YTDLP_COOKIE_FILE", "")).is_file()
        ),
        "max_duration_seconds": app.config["MAX_DURATION_SECONDS"],
        "max_filesize_mb": app.config["MAX_FILESIZE_MB"],
    })


@app.post("/convert")
def convert():
    submitted_url = request.form.get("url", "").strip()
    output_format = request.form.get("format", "mp4").lower()
    quality = request.form.get("quality", "720")
    rights_confirmed = request.form.get("rights_confirmed") == "yes"

    def fail(message: str, status: int = 400):
        return render_template_string(
            PAGE,
            error=message,
            submitted_url=submitted_url,
            app_version=APP_VERSION,
        ), status

    if not rights_confirmed:
        return fail("You must confirm that you are authorized to download and convert the content.")

    if not valid_youtube_url(submitted_url):
        return fail("Enter a valid youtube.com or youtu.be video URL.")

    if output_format not in ALLOWED_FORMATS:
        return fail("Unsupported output format.")

    if quality not in ALLOWED_QUALITIES:
        return fail("Unsupported video quality.")

    if not rate_limit_ok(client_key()):
        return fail("Conversion rate limit reached. Try again after the rate-limit window resets.", 429)

    if not shutil.which("ffmpeg"):
        return fail("FFmpeg is not installed on the server. Install it before converting media.", 503)

    job_dir = Path(tempfile.mkdtemp(prefix="ytconv-"))

    capture = YTDLPLogCapture()

    try:
        options = build_options(job_dir, output_format, quality, capture)
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.extract_info(submitted_url, download=True)

        output_file = find_output_file(job_dir, output_format)
        download_name = secure_filename(output_file.name) or f"converted.{output_format}"

        response = send_file(
            output_file,
            as_attachment=True,
            download_name=download_name,
            conditional=True,
            max_age=0,
        )
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.call_on_close(lambda: shutil.rmtree(job_dir, ignore_errors=True))
        return response

    except yt_dlp.utils.DownloadError as exc:
        shutil.rmtree(job_dir, ignore_errors=True)
        if capture.messages:
            app.logger.warning("yt-dlp diagnostics:\n%s", capture.combined())
        detail = str(exc).replace("ERROR:", "").strip()
        # Avoid exposing excessively long internal extractor diagnostics.
        if len(detail) > 500:
            detail = detail[:497] + "..."

        if "Sign in to confirm you" in detail and "not a bot" in detail:
            return fail(
                "YouTube requested an authenticated session. Export a fresh "
                "YouTube cookies.txt file, mount it into the container, and set "
                "YTDLP_COOKIE_FILE to the mounted path.",
                422,
            )

        if "Requested format is not available" in detail:
            diagnostics = capture.combined().lower()

            if (
                "challenge solving failed" in diagnostics
                or "javascript runtime" in diagnostics
                or "only images are available" in diagnostics
            ):
                return fail(
                    "YouTube's JavaScript challenge could not be solved. "
                    "Rebuild with version 1.0.6 or later and verify that the "
                    "/health endpoint reports deno_available=true and a "
                    "yt_dlp_ejs_version.",
                    422,
                )

            if "po token" in diagnostics or "missing_pot" in diagnostics:
                return fail(
                    "YouTube withheld the playable formats because this "
                    "session requires a PO Token. The basic cookie-only setup "
                    "is not sufficient for this video/session.",
                    422,
                )

            return fail(
                "No playable formats were returned for this session. Verify "
                "Deno and yt-dlp-ejs in /health, then refresh the cookie file. "
                "The container log contains yt-dlp's detailed warnings.",
                422,
            )

        return fail(f"Conversion failed: {detail}", 422)

    except Exception as exc:
        shutil.rmtree(job_dir, ignore_errors=True)
        app.logger.exception("Unexpected conversion failure")
        return fail(f"Conversion failed: {str(exc)[:300]}", 500)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
