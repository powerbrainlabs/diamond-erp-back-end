FROM python:3.11-slim

WORKDIR /app

# Build deps for Python packages (Pillow, cryptography, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps chromium

# Certificate cards shrink text to ~5-10px to fit. At those sizes Chromium's
# default font hinting (--font-render-hinting=full) quantizes glyph advances
# to whole pixels, and the rounding error is large enough that bold text gets
# one position operator per glyph — "Gross Weight" comes out of the PDF as
# "G r o s s We ig h t". Wrapping the binary applies the fix to every launch
# without the PDF generator having to know about it.
RUN B="$(find /root/.cache/ms-playwright -name chrome-headless-shell -type f | head -1)" \
    && mv "$B" "$B.real" \
    && printf '#!/bin/sh\nexec "$0.real" --font-render-hinting=none "$@"\n' > "$B" \
    && chmod +x "$B"

COPY . .

EXPOSE 8080

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
