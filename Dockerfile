FROM denoland/deno:bin-2.9.2 AS deno

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

COPY --from=deno /deno /usr/local/bin/deno

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && deno --version \
    && python -c "import importlib.metadata as m; print('yt-dlp', m.version('yt-dlp')); print('yt-dlp-ejs', m.version('yt-dlp-ejs'))"

COPY app.py .

EXPOSE 8080

CMD ["sh", "-c", "gunicorn --workers 2 --threads 4 --timeout 900 --bind 0.0.0.0:${PORT} app:app"]
