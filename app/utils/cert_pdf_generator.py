"""
Certificate PDF generator using Playwright (Chromium).
Renders the same HTML/CSS as the React frontend for pixel-perfect output.
"""
import asyncio
import base64
import io
import shutil
import httpx
import segno
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from ..core.config import settings
from ..core.minio_client import minio_client

ASSETS_DIR = Path(__file__).parent.parent / "assets"

# Images are staged as real files next to the HTML and referenced by relative
# name, rather than inlined as base64 data URIs. Base64 costs 33% on the wire
# and, worse, these two card assets are identical on every card — inlining put
# ~200KB of duplicated text into each of the 10 cards on a page. As files,
# Chromium fetches and decodes each exactly once and caches it.
GAC_HEADER_SRC = "gac-header.png"
BG_PARTICLES_SRC = "bg-particles.png"
STATIC_ASSETS = {
    GAC_HEADER_SRC: ASSETS_DIR / "gac_card_first_image.png",
    BG_PARTICLES_SRC: ASSETS_DIR / "BG-particles1.png",
}

def _build_font_face_css() -> str:
    # Embedded as data URIs. This originally worked around file:// fonts
    # failing to load when the page came from page.set_content() rather than
    # a file:// navigation; the render now navigates to a staged file, so
    # they could be plain files too. Kept inline because all four weights
    # come to ~41KB of base64 total, once per document — unlike the images,
    # which were being duplicated per card and are now staged as files.
    #
    # WOFF2, not TTF: switching to data-URI TTF fixed loading but introduced
    # a *worse* bug — pdftotext on the generated PDF showed bold text
    # scrambled with stray spaces mid-word ("Gross Weight" -> "G r o s s
    # We ig h t"), regular weight mostly unaffected. Chromium's PDF export
    # mis-subsets/positions glyphs for the base64 TTF specifically (own
    # test: identical bold text rendered correctly once switched to the
    # bundled woff2 files instead — same content, only the embedded format
    # differed).
    fonts_dir = ASSETS_DIR / "fonts"
    css = ""
    for weight, filename in [(400, "Poppins-400.woff2"), (500, "Poppins-500.woff2"), (600, "Poppins-600.woff2"), (700, "Poppins-700.woff2")]:
        font_path = fonts_dir / filename
        if font_path.exists():
            with open(font_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            css += f"@font-face {{font-family:'Poppins';font-style:normal;font-weight:{weight};src:url('data:font/woff2;base64,{b64}') format('woff2');}}\n"
    return css


def _is_square_image(content: bytes) -> bool:
    """Return True if the image aspect ratio is close to 1:1 (0.85–1.15).

    Note: this previously hand-parsed PNG/JPEG headers with `struct`, which
    was never imported — every call raised NameError into the bare except and
    returned False, so the `.square` photo class has never actually applied.
    Pillow is already a dependency here (see _downscale_for_pdf) and reads the
    dimensions of any format we accept.
    """
    try:
        from PIL import Image

        with Image.open(io.BytesIO(content)) as img:
            w, h = img.size
        ratio = w / h if h else 1
        return 0.85 <= ratio <= 1.15
    except Exception:
        return False


POPPINS_FONT_CSS = _build_font_face_css()


def _certificate_public_url(cert_uuid: str) -> str:
    frontend_base = (settings.FRONTEND_URL or "http://localhost:5173").rstrip("/")
    return f"{frontend_base}/certificate/{cert_uuid}"


def _qr_key(cert_uuid: str) -> str:
    """Map key under which a cert's QR image is staged."""
    return f"qr:{cert_uuid}"


def _qr_png(cert_uuid: str) -> bytes:
    """Render the certificate's QR code locally.

    These used to come from api.qrserver.com — one external HTTPS round-trip
    per certificate, every render, for an image that is a pure function of the
    certificate URL. On a bulk download that is N sequential-ish network calls
    before Chromium even starts, and any that failed fell through to putting
    the remote URL straight into the <img>, so the render itself then blocked
    on qrserver.com while waiting for networkidle. Generating locally takes
    ~5ms per code and removes the external dependency from the render path.
    """
    buf = io.BytesIO()
    segno.make(_certificate_public_url(cert_uuid), error='m').save(
        buf, kind='png', scale=4, border=1
    )
    return buf.getvalue()

CERTIFICATE_FIELD_CONFIG = {
    'single_diamond': ['gross_weight', 'diamond_weight', 'cut', 'clarity', 'color', 'conclusion', 'comment'],
    'loose_diamond': ['dimension', 'weight', 'shape', 'clarity', 'color', 'sg_ri_hardness', 'microscopic_obs', 'conclusion', 'comment'],
    'loose_stone': ['dimension', 'color', 'weight', 'shape', 'sg_ri_hardness', 'sg', 'hardness', 'microscopic_obs', 'conclusion', 'comment'],
    'single_mounded': ['gross_weight', 'stone_weight', 'shape', 'sg', 'hardness', 'microscopic_obs', 'conclusion', 'comment'],
    'double_mounded': ['gross_weight', 'primary_stone_weight', 'secondary_stone_weight', 'shape', 'ri', 'hardness', 'cut', 'clarity', 'colour', 'microscopic_obs', 'conclusion'],
    'navaratna': ['gross_weight', 'diamond_weight', 'cut', 'color', 'clarity', 'conclusion', 'comment'],
}
BOLD_FIELDS = {'gross_weight', 'diamond_weight', 'weight', 'stone_weight', 'gemstone_weight', 'primary_stone_weight', 'secondary_stone_weight', 'conclusion'}
GEMSTONE_CERTIFICATE_GROUPS = {'loose_stone', 'single_mounded', 'double_mounded'}
NO_DESCRIPTION_GROUPS = {'loose_stone', 'loose_diamond'}


def _normalize_display_text(value: Any) -> str:
    if value is None:
        return ""

    import re

    text = str(value)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def _format_value(value, field_type):
    if value is None or value == '':
        return ''
    if field_type == 'composite':
        if isinstance(value, dict):
            parts = [str(v) for v in value.values() if v not in (None, '')]
            return 'x'.join(parts)
        if isinstance(value, str):
            import re
            parts = [v.strip() for v in re.split(r'[\s,]+', value) if v.strip()]
            return 'x'.join(parts)
    if isinstance(value, list):
        return _normalize_display_text(', '.join(str(v) for v in value))
    if isinstance(value, dict):
        return _normalize_display_text(str(value))
    return _normalize_display_text(value)


def _esc(s: str) -> str:
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def _estimate_text_lines(value: Any, chars_per_line: int, min_lines: int = 1, max_lines: int = 4) -> int:
    text = str(value or '').strip()
    if not text:
        return 0

    line_count = 0
    for part in text.splitlines() or ['']:
        segment = part.strip()
        if not segment:
            line_count += 1
            continue
        line_count += max(1, (len(segment) + chars_per_line - 1) // chars_per_line)

    return max(min_lines, min(line_count, max_lines))


def _downscale_for_pdf(content: bytes, content_type: str) -> tuple[bytes, str]:
    """Shrink an image before it gets base64-embedded and rasterized by
    Chromium for print. Certificate photos come straight from camera/phone
    uploads (multi-MB, thousands of pixels wide) — full resolution is
    pointless for a card-sized print photo, and decoding+rasterizing that
    many full-size images at once is exactly what was pushing a single
    8-cert batch to ~500MiB (confirmed via docker stats). Falls back to the
    original bytes untouched on any failure (e.g. SVGs, corrupt data).
    """
    try:
        from io import BytesIO
        from PIL import Image

        img = Image.open(BytesIO(content))
        img.load()
        # The card photo prints ~2cm wide, i.e. ~240px at 300dpi. 900px was
        # ~14x the pixels ever rendered, and Chromium holds every image
        # decoded (900x900 RGBA is ~3.2MB each) while laying out a page.
        max_dim = 400
        if img.width > max_dim or img.height > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        out = BytesIO()
        img.save(out, format="JPEG", quality=78, optimize=True)
        return out.getvalue(), "image/jpeg"
    except Exception:
        return content, content_type


async def _fetch_bytes(url: str) -> Optional[Tuple[bytes, str]]:
    """Fetch an image URL and return (content, content_type), or None on failure.

    Last-resort fallback for signed URLs that point back at this backend's own
    public domain — which containers generally can't reach via hairpin NAT, so
    that path is expected to fail. Kept short (vs. the old 3×30s = 90s worst
    case) so a bulk PDF request never stalls long on it.
    """
    if not url:
        return None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=True, verify=False) as client:
                r = await client.get(url)
                if r.status_code != 200:
                    continue
                content_type = r.headers.get('content-type', 'image/jpeg').split(';')[0].strip()
                return _downscale_for_pdf(r.content, content_type)
        except Exception:
            pass
    return None


def _storage_ref_to_bytes(storage_ref: str) -> Optional[Tuple[bytes, str]]:
    """Read an object like 'bucket/object' from storage as (content, content_type)."""
    if not storage_ref or "/" not in storage_ref:
        return None
    try:
        bucket, object_name = storage_ref.split("/", 1)
        response = minio_client.get_object(bucket, object_name)
        content = response.read()
        content_type = response.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        # Always a real cert/client photo, so lossy-shrinking it to print size
        # is safe.
        return _downscale_for_pdf(content, content_type)
    except Exception:
        return None


async def _prefetch_images(certs: List[Dict[str, Any]], out_dir: Path) -> Dict[str, str]:
    """Stage every image this batch needs into out_dir, keyed by source.

    Returns a source→filename map, so render functions never block on I/O
    per-cert and the HTML carries short relative names instead of megabytes of
    base64. Sources:
    - storage refs ('bucket/key', e.g. cert['photo_url']) — read directly
      from R2, which is what actually works reliably (the signed HTTP URLs
      point back at this same backend's own public domain, which containers
      generally can't hairpin back to themselves through, so that path is
      kept only as a last-resort fallback for callers that lack a ref).
    - signed URLs (photo_signed_url etc.) — fetched over HTTP.
    - QR codes — generated locally, see _qr_png.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, source in STATIC_ASSETS.items():
        shutil.copyfile(source, out_dir / name)

    def _write(index: int, content: bytes, content_type: str) -> str:
        ext = 'png' if 'png' in content_type else 'jpg'
        name = f"img{index}.{ext}"
        (out_dir / name).write_bytes(content)
        return name

    storage_refs = set()
    urls = set()
    for cert in certs:
        for key in ('photo_url', 'brand_logo_url', 'rear_brand_logo_url'):
            ref = cert.get(key)
            if ref:
                storage_refs.add(ref)
        for key in ('photo_signed_url', 'brand_logo_signed_url', 'rear_brand_logo_signed_url'):
            url = cert.get(key)
            if url:
                urls.add(url)

    storage_refs = sorted(storage_refs)
    urls = sorted(urls)
    storage_results = await asyncio.gather(
        *[asyncio.to_thread(_storage_ref_to_bytes, ref) for ref in storage_refs]
    )
    url_results = await asyncio.gather(*[_fetch_bytes(url) for url in urls])

    img_map: Dict[str, str] = {}
    photo_content: Dict[str, bytes] = {}
    counter = 0
    for ref, result in zip(storage_refs, storage_results):
        if not result:
            continue
        content, content_type = result
        img_map[ref] = _write(counter, content, content_type)
        photo_content[ref] = content
        counter += 1
    # Only fall back to the (possibly-hairpinned, slower) HTTP fetch for a
    # signed URL if nothing already resolved it via the direct storage ref.
    for url, result in zip(urls, url_results):
        if not result or url in img_map:
            continue
        content, content_type = result
        img_map[url] = _write(counter, content, content_type)
        photo_content[url] = content
        counter += 1

    for cert in certs:
        cert_uuid = cert.get('uuid')
        if cert_uuid:
            name = f"qr-{counter}.png"
            (out_dir / name).write_bytes(_qr_png(cert_uuid))
            img_map[_qr_key(cert_uuid)] = name
            counter += 1
        # Squareness drives a CSS class; decide it here while the bytes are in
        # hand rather than re-reading the staged file during rendering.
        photo_ref = cert.get('photo_url') or cert.get('photo_signed_url') or ''
        cert['_photo_is_square'] = _is_square_image(photo_content.get(photo_ref, b''))

    return img_map


def _render_card_front(cert: Dict[str, Any], img_map: Dict[str, str] = {}) -> str:
    fields = cert.get('fields') or {}
    schema = cert.get('schema') or {}
    cert_type = cert.get('type', '')
    group = schema.get('group', '')

    photo_url = (
        img_map.get(cert.get('photo_url') or '')
        or img_map.get(cert.get('photo_signed_url') or '')
        or ''
    )
    brand_logo_url = (
        img_map.get(cert.get('brand_logo_url') or '')
        or img_map.get(cert.get('brand_logo_signed_url') or '')
        or ''
    )
    qr_url = img_map.get(_qr_key(cert['uuid']), '') if cert.get('uuid') else ''
    cert_number = _esc(_normalize_display_text(cert.get('certificate_number') or ''))
    description = ''
    if group not in NO_DESCRIPTION_GROUPS:
        description = _esc(_normalize_display_text(cert.get('generated_description') or fields.get('description') or ''))

    # Header images
    brand_logo_html = ''
    if brand_logo_url:
        brand_logo_html = f'<img src="{_esc(brand_logo_url)}" class="brand-logo" alt="Logo">'
    qr_html = ''
    if qr_url:
        qr_html = f'<img src="{_esc(qr_url)}" class="qr-code" alt="QR">'

    # Photo
    NO_IMAGE_SVG = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='70' height='70'%3E%3Crect fill='%23eeeeee' width='70' height='70'/%3E%3Ctext fill='%23aaaaaa' font-family='sans-serif' font-size='8' text-anchor='middle' x='35' y='38'%3ENo Image%3C/text%3E%3C/svg%3E"
    _photo_src = _esc(photo_url) if photo_url else NO_IMAGE_SVG
    _photo_class = "cert-photo square" if photo_url and cert.get('_photo_is_square') else "cert-photo"
    photo_html = f'''<div class="cert-photo-frame">
  <img src="{_photo_src}" class="{_photo_class}" alt="Photo">
  <span class="approx-label">Approx Photo</span>
</div>'''

    # Build field rows
    rows_html = ''
    visual_row_count = 0

    if cert_type == 'custom':
        if description:
            visual_row_count += _estimate_text_lines(description, chars_per_line=42, min_lines=1, max_lines=3)
            description_bold_style = 'font-weight:bold;' if fields.get('description_bold') else ''
            rows_html += f'''<div class="field-row full-width">
                <span class="label" style="{description_bold_style}">Description</span><span class="sep">:</span>
                <span class="value desc-value" style="{description_bold_style}">{description}</span></div>'''
        visual_row_count += _estimate_text_lines(cert_number, chars_per_line=24)
        rows_html += f'''<div class="field-row">
            <span class="label">Certificate No</span><span class="sep">:</span>
            <span class="value">{cert_number}</span></div>'''
        for cf in (fields.get('custom_fields') or []):
            if cf.get('key') or cf.get('value'):
                custom_value = _esc(_normalize_display_text(cf.get("value", "")))
                custom_bold_style = 'font-weight:bold;' if cf.get('bold') else ''
                visual_row_count += _estimate_text_lines(custom_value, chars_per_line=24, min_lines=1, max_lines=3)
                rows_html += f'''<div class="field-row">
                    <span class="label" style="{custom_bold_style}">{_esc(_normalize_display_text(cf.get("key", "")))}</span><span class="sep">:</span>
                    <span class="value" style="{custom_bold_style}">{custom_value}</span></div>'''
    else:
        allowed = CERTIFICATE_FIELD_CONFIG.get(group, [])
        schema_fields = schema.get('fields') or []

        # Double mounded: swap sg/ri/hardness ↔ cut/clarity/colour based on primary gemstone
        if group == 'double_mounded':
            primary_gemstone = (fields.get('primary_gemstone') or '').strip().lower()
            if primary_gemstone == 'natural diamond':
                allowed = [f for f in allowed if f not in ('sg', 'ri', 'hardness')]
            else:
                allowed = [f for f in allowed if f not in ('cut', 'clarity', 'colour')]

        if description:
            visual_row_count += _estimate_text_lines(description, chars_per_line=42, min_lines=1, max_lines=3)
            rows_html += f'''<div class="field-row full-width">
                <span class="label">Description</span><span class="sep">:</span>
                <span class="value desc-value">{description}</span></div>'''

        visual_row_count += _estimate_text_lines(cert_number, chars_per_line=24)
        rows_html += f'''<div class="field-row">
            <span class="label">Certificate No</span><span class="sep">:</span>
            <span class="value">{cert_number}</span></div>'''

        field_order = {name: i for i, name in enumerate(allowed)}
        sorted_fields = sorted(
            [f for f in schema_fields if f.get('field_name') in allowed],
            key=lambda f: field_order.get(f.get('field_name', ''), 999)
        )

        # Apply conditional_logic (e.g. double_mounded: cut/clarity/colour vs sg/ri/hardness)
        def _passes_conditional(field_def):
            cl = field_def.get('conditional_logic')
            if not cl or not cl.get('show_if_field'):
                return True
            dep_val = str(fields.get(cl['show_if_field'], '') or '').strip().lower()
            if 'show_if_not_value' in cl:
                return dep_val != str(cl['show_if_not_value']).strip().lower()
            if 'show_if_value' in cl:
                return dep_val == str(cl['show_if_value']).strip().lower()
            return True

        sorted_fields = [f for f in sorted_fields if _passes_conditional(f)]

        for field in sorted_fields:
            fname = field.get('field_name', '')
            raw = fields.get(fname)
            if group == 'navaratna' and fname == 'conclusion':
                raw = raw or 'Natural Diamond'
            elif raw is None or raw == '':
                continue

            label = _normalize_display_text(field.get('label', fname))
            # Replace stone weight label with gemstone name
            import re
            m = re.match(r'^(.+)_stone_w', fname)
            if m:
                gem_name = fields.get(f'{m.group(1)}_gemstone')
                if gem_name:
                    clean_gem = re.sub(r'^natural\s+', '', gem_name, flags=re.IGNORECASE)
                    label = _normalize_display_text(f'{clean_gem} Weight')

            # sg_ri_hardness composite: render as 3 separate rows
            if fname == 'sg_ri_hardness' and isinstance(raw, dict):
                for sub_key, sub_label in (('sg', 'SG'), ('hardness', 'Hardness')):
                    sub_val = raw.get(sub_key, '')
                    if not sub_val:
                        continue
                    visual_row_count += 1
                    rows_html += f'''<div class="field-row">
                        <span class="label">{_esc(sub_label)}</span><span class="sep">:</span>
                        <span class="value">{_esc(str(sub_val))}</span></div>'''
                continue

            if field.get('field_type') == 'custom' and isinstance(raw, dict):
                label = _normalize_display_text(raw.get('custom_label', label))
                display = _esc(_normalize_display_text(raw.get('custom_value', '')))
            else:
                display = _esc(_format_value(raw, field.get('field_type', '')))
                unit = field.get('unit', '')
                if unit and fname != 'hardness':
                    if unit.lower() in ('cts', 'ct'):
                        unit = 'ct' if (float(display) if display.replace('.', '', 1).isdigit() else 1) < 1 else 'cts'
                    display = f'{display} {unit}'
            label = _esc(label)

            is_comment = fname in ('comment', 'comments', 'microscopic_obs')
            is_full = is_comment or field.get('field_type') in ('textarea', 'custom') or fname in ('description',)
            is_bold = fname in BOLD_FIELDS
            bold_style = 'font-weight:bold;' if is_bold else ''
            capitalize = 'text-transform:capitalize;' if fname == 'conclusion' else ''
            row_class = 'field-row full-width comment-row' if is_comment else ('field-row full-width' if is_full else 'field-row')
            val_class = 'value comment-value' if is_comment else ('value desc-value' if is_full else 'value')
            chars_per_line = 42 if is_full else 24
            max_lines = 1 if is_comment else (3 if fname == 'conclusion' else 2)
            visual_row_count += _estimate_text_lines(display, chars_per_line=chars_per_line, min_lines=1, max_lines=max_lines)

            comment_font_style = ''

            rows_html += f'''<div class="{row_class}">
                <span class="label" style="{bold_style}">{label}</span><span class="sep">:</span>
                <span class="{val_class}" style="{bold_style}{capitalize}{comment_font_style}">{display}</span></div>'''

    # Density: estimate visual lines so wrapped values affect PDF fitting.
    row_count = max(visual_row_count, rows_html.count('field-row'))
    density_style = 'font-size:0.62em;line-height:10.8px;'

    return f'''
<div class="cert-card" data-cert-uuid="{_esc(cert.get('uuid',''))}" data-row-count="{row_count}">
  <header class="card-header">
    <img src="{GAC_HEADER_SRC}" class="gac-header-img" alt="GAC">
    <div class="header-right">
      {brand_logo_html}
      {qr_html}
    </div>
  </header>
  {photo_html}
  <div class="card-body">
    <div class="cert-title">CERTIFICATE OF AUTHENTICITY</div>
    <div class="cert-details">
      <div class="bg-particles">
        <img src="{BG_PARTICLES_SRC}" alt="">
      </div>
      <div class="fields-area" style="{density_style}">
        {rows_html}
      </div>
    </div>
    <div class="card-footer">For further information visit <b>www.thegac.in</b></div>
  </div>
</div>'''


def _render_card_back(cert: Dict[str, Any], img_map: Dict[str, str] = {}) -> str:
    rear_logo_url = cert.get('rear_brand_logo_signed_url') or cert.get('brand_logo_signed_url') or ''
    rear_logo = (
        img_map.get(cert.get('rear_brand_logo_url') or '')
        or img_map.get(cert.get('brand_logo_url') or '')
        or img_map.get(rear_logo_url)
        or ''
    )
    img_html = f'<img src="{_esc(rear_logo)}" class="back-logo" alt="Logo">' if rear_logo else ''
    return f'''
<div class="cert-card back-card" data-cert-uuid="{_esc(cert.get('uuid',''))}">
  <div class="back-media">
    {img_html}
  </div>
</div>'''


CSS = POPPINS_FONT_CSS + """

@page {
  size: A4;
  margin: 0;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Poppins', sans-serif;
  background: white;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
  /* Card text renders as small as ~5-10px (see the fit script below), where
     Chromium's PDF export garbles glyph positioning for small BOLD text
     ("Gross Weight" -> "G r o s s We ig h t"). The cause is Chromium's
     default font hinting (--font-render-hinting=full), which quantizes
     glyph advances to whole pixels; at these sizes the rounding error is
     large enough that each glyph gets its own position operator. It is
     fixed at the environment level — the Dockerfile wraps the headless
     Chromium binary to always pass --font-render-hinting=none — so no
     layout trickery is needed here. */
}

.page {
  page-break-after: always;
  width: 210mm;
  height: 297mm;
  background: white;
  box-sizing: border-box;
  overflow: hidden;
  position: relative;
}
.page:last-child { page-break-after: avoid; }

.print-grid {
  display: flex;
  flex-direction: column;
  gap: 4mm;
  width: 177mm;
  margin-left: 16.5mm;
  margin-top: 2mm;
  align-items: flex-start;
}

.print-row {
  display: flex;
  flex-direction: row;
  gap: 3mm;
  justify-content: flex-start;
  align-items: flex-start;
  width: 100%;
}

.cert-card {
  background-color: white;
  width: 8.69cm;
  height: 5.5cm;
  padding: 0;
  border-top: 1px dotted #2b1fb4;
  border-left: 1px dotted #2b1fb4;
  border-right: none;
  border-bottom: none;
  box-sizing: border-box;
  position: relative;
  font-family: 'Poppins', Arial, sans-serif;
  page-break-inside: avoid;
  overflow: hidden;
  contain: paint;
}

.card-header {
  position: relative;
  --brown-line-trim-width: 50px;
  --brown-line-trim-top: 48px;
  --brown-line-trim-height: 9px;
}

.card-header::after {
  content: "";
  position: absolute;
  top: var(--brown-line-trim-top);
  right: 0;
  width: var(--brown-line-trim-width);
  height: var(--brown-line-trim-height);
  background: white;
  z-index: 1;
}

.card-header::before {
  content: "";
  position: absolute;
  top: 43px;
  right: 60px;
  width: 6px;
  height: 17px;
  background: white;
  z-index: 1;
}

.gac-header-img {
  width: 100%;
  position: absolute;
  left: 0;
}

.header-right {
  position: absolute;
  top: 3.5px;
  right: 10px;
  display: flex;
  align-items: flex-start;
  gap: 0;
  z-index: 2;
}

.brand-logo {
  height: 43px;
  width: 65px;
  object-fit: contain;
  background: white;
  border-radius: 4px;
  padding: 4px;
}

.qr-code {
  width: 49px;
  height: 49px;
  object-fit: contain;
  flex-shrink: 0;
  margin-top: 3px;
  margin-right: 2px;
  margin-left: 6px;
  align-self: flex-start;
}

.cert-photo-frame {
  position: absolute;
  top: 100px;
  right: 14px;
  width: 89px;
  z-index: 2;
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 10px;
}

.cert-photo {
  display: block;
  flex: 1;
  min-width: 0;
  height: 0.8in;
  object-fit: contain;
  object-position: center;
}

.cert-photo-frame.square-frame {
  /* same position as regular - fixed-width wrapper keeps label aligned */
}

.cert-photo.square {
  height: 0.6in;
}

.approx-label {
  flex-shrink: 0;
  font-size: 5.5px;
  font-weight: 400;
  white-space: nowrap;
  writing-mode: vertical-rl;
  text-orientation: mixed;
}

.card-body {
  margin-top: 48px;
  height: calc(100% - 48px);
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

.cert-title {
  font-weight: bold;
  font-size: 0.61em;
  text-align: center;
  padding: 8px 0 3px 0;
}

.cert-details {
  position: relative;
  padding-left: 10px;
  padding-right: 10px;
  padding-bottom: 1px;
  flex: 1;
}

.bg-particles {
  position: absolute;
  transform: translate(-3px, -1px);
  height: 3.1cm;
  left: -7px;
  opacity: 0.25;
  z-index: 0;
  pointer-events: none;
}
.bg-particles img { height: 3.1cm; }

.fields-area {
  position: relative;
  z-index: 1;
  font-size: 0.52em;
  line-height: 9.2px;
  overflow: visible;
}

.field-row {
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  font-size: 0.87em;
}

.field-row.full-width { width: 100%; }

.comment-row {
  width: calc(100% + 20px);
  margin-right: -10px;
  box-sizing: border-box;
}

.comment-row .label {
  width: 93px;
  min-width: 93px;
  white-space: nowrap;
}

.comment-row .sep {
  margin: 0 4px;
}

.label {
  width: 93px;
  min-width: 93px;
  flex-shrink: 0;
  font-weight: 400;
  white-space: nowrap;
}

.sep {
  margin: 0 4px;
  flex-shrink: 0;
}

.value {
  flex: 1;
  word-wrap: break-word;
  min-width: 0;
}

.desc-value {
  flex: 1;
  line-height: 1.1;
  display: block;
  overflow: visible;
  word-break: break-word;
  min-width: 0;
}

.comment-value {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  padding-bottom: 2px;
}

.card-footer {
  width: 100%;
  text-align: center;
  font-size: 0.39em;
  padding-bottom: 8px;
  background: white;
  z-index: 3;
}

/* Back card */
.back-media {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.back-logo {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
"""

FIT_SCRIPT = """
<script>
(() => {
  const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

  function fitCard(card) {
    const fields = card.querySelector('.fields-area');
    const footer = card.querySelector('.card-footer');
    if (!fields || !footer) return;
    const rowCount = Number(card.dataset.rowCount || 0);

    const computed = window.getComputedStyle(fields);
    let fontSize = parseFloat(computed.fontSize);
    let lineHeight = parseFloat(computed.lineHeight);
    if (!fontSize || !lineHeight) return;

    const minFont = Math.max(5.4, fontSize * 0.78);
    const maxFont = Math.min(10.6, fontSize * 1.55);
    const minLine = Math.max(6.8, lineHeight * 0.78);
    const maxLine = Math.min(14.8, lineHeight * 1.55);

    const reservedGap = rowCount >= 10 ? 3.5 : rowCount <= 4 ? 1.5 : 2;

    for (let i = 0; i < 12; i += 1) {
      const fieldsRect = fields.getBoundingClientRect();
      const footerRect = footer.getBoundingClientRect();
      const availableHeight = footerRect.top - fieldsRect.top - reservedGap;
      const contentHeight = fields.scrollHeight;
      if (availableHeight <= 0 || contentHeight <= 0) break;

      const ratio = availableHeight / contentHeight;
      if (ratio >= 0.985 && ratio <= 1.03) break;

      const step = clamp(ratio, 0.88, 1.12);
      const nextFont = clamp(fontSize * step, minFont, maxFont);
      const nextLine = clamp(lineHeight * step, minLine, maxLine);
      if (Math.abs(nextFont - fontSize) < 0.05 && Math.abs(nextLine - lineHeight) < 0.05) break;

      fontSize = nextFont;
      lineHeight = nextLine;
      fields.style.fontSize = `${fontSize.toFixed(2)}px`;
      fields.style.lineHeight = `${lineHeight.toFixed(2)}px`;
    }

    const finalFieldsRect = fields.getBoundingClientRect();
    const finalFooterRect = footer.getBoundingClientRect();
    const finalAvailable = finalFooterRect.top - finalFieldsRect.top - reservedGap;
    const finalContent = fields.scrollHeight;

    if (finalContent > finalAvailable) {
      // Shrink until the rows actually fit, re-measuring each pass. A single
      // pass is not enough: shrinking the font re-wraps the longer values, so
      // the row count (and with it scrollHeight) changes underneath the very
      // ratio used to pick the new size. Whatever still overflows here gets
      // clipped by the card edge, and a half-drawn row extracts from the PDF
      // with its glyphs dropped ("Fluorescence" -> "Fl", "Faint" -> "F i t"),
      // so it is worth spending a few extra iterations to land inside.
      for (let i = 0; i < 12; i += 1) {
        const available = footer.getBoundingClientRect().top
          - fields.getBoundingClientRect().top - reservedGap;
        if (fields.scrollHeight <= available) break;
        const nextFont = clamp(fontSize * 0.97, minFont, maxFont);
        const nextLine = clamp(lineHeight * 0.97, minLine, maxLine);
        // Both at their floor — no further shrink is possible.
        if (Math.abs(nextFont - fontSize) < 0.01 && Math.abs(nextLine - lineHeight) < 0.01) break;
        fontSize = nextFont;
        lineHeight = nextLine;
        fields.style.fontSize = `${fontSize.toFixed(2)}px`;
        fields.style.lineHeight = `${lineHeight.toFixed(2)}px`;
      }
      return;
    }

    if (rowCount <= 10 && finalAvailable > finalContent + 4) {
      const fillRatio = clamp(finalAvailable / finalContent, 1, rowCount <= 4 ? 1.1 : rowCount <= 8 ? 1.06 : 1.04);
      fields.style.fontSize = `${clamp(fontSize * fillRatio, minFont, maxFont).toFixed(2)}px`;
      fields.style.lineHeight = `${clamp(lineHeight * fillRatio, minLine, maxLine).toFixed(2)}px`;
    }
  }

  // .label has a fixed 93px width and white-space: nowrap (see CSS) — the
  // main fitCard loop only sizes fonts to fit *vertically* (row count vs.
  // available height), nothing checks whether an individual label's own
  // text fits *horizontally* in that box. Most labels are short static
  // strings (Cut, Color, SG...) so this went unnoticed, but a long
  // dynamically-built one (e.g. "RUBY & NATURAL EMERALD Weight", from the
  // gemstone-name substitution above) overflows straight into the value
  // column with no fallback. Same technique fitCommentValues already uses
  // for the same class of problem on the value side.
  function fitLabels() {
    document.querySelectorAll('.label').forEach(function(el) {
      let fs = parseFloat(window.getComputedStyle(el).fontSize);
      const minFs = fs * 0.55;
      for (let i = 0; i < 10; i++) {
        if (el.scrollWidth <= el.clientWidth + 1) break;
        fs = Math.max(minFs, fs * 0.94);
        el.style.fontSize = fs.toFixed(2) + 'px';
      }
      // Even at the shrink floor, a genuinely long dynamically-built label
      // (e.g. two long gemstone names combined) can still be too wide for
      // 93px without becoming illegibly small. Wrapping to 2 lines keeps
      // the fixed label width (so every row's colon/value still lines up)
      // instead of overlapping into the value column.
      if (el.scrollWidth > el.clientWidth + 1) {
        el.style.whiteSpace = 'normal';
      }
    });
  }

  function run() {
    document.querySelectorAll('.cert-card:not(.back-card)').forEach(fitCard);
    fitLabels();
    alignPhotoToCertNo();
    window.__cardsFitted = true;
  }

  // Detect square photos and apply larger size class
  function applySquarePhotoClasses() {
    document.querySelectorAll('.cert-photo').forEach(function(img) {
      const w = img.naturalWidth, h = img.naturalHeight;
      if (!w || !h) return;
      const ratio = w / h;
      if (ratio >= 0.85 && ratio <= 1.15) {
        img.classList.add('square');
        const frame = img.closest('.cert-photo-frame');
        if (frame) frame.classList.add('square-frame');
      }
    });
  }

  function alignPhotoToCertNo() {
    document.querySelectorAll('.cert-card:not(.back-card)').forEach(function(card) {
      const frame = card.querySelector('.cert-photo-frame');
      const photo = frame && frame.querySelector('.cert-photo');
      if (!frame || !photo) return;
      // Only apply to rectangle (non-square) photos
      if (photo.classList.contains('square')) return;
      // Find Certificate No row
      const rows = card.querySelectorAll('.field-row');
      let certNoRow = null;
      rows.forEach(function(row) {
        const label = row.querySelector('.label');
        if (label && label.textContent.trim() === 'Certificate No') certNoRow = row;
      });
      if (!certNoRow) return;
      const cardRect = card.getBoundingClientRect();
      const certNoRect = certNoRow.getBoundingClientRect();
      const newTop = certNoRect.top - cardRect.top;
      frame.style.top = newTop + 'px';
    });
  }

  function fitCommentValues() {
    document.querySelectorAll('.comment-value').forEach(function(el) {
      const parent = el.closest('.comment-row');
      if (!parent) return;
      let fs = parseFloat(window.getComputedStyle(el).fontSize);
      const minFs = fs * 0.72;
      for (let i = 0; i < 10; i++) {
        if (el.scrollWidth <= el.clientWidth + 1) break;
        fs = Math.max(minFs, fs * 0.94);
        el.style.fontSize = fs.toFixed(2) + 'px';
      }
    });
  }

  const start = () => requestAnimationFrame(() => { applySquarePhotoClasses(); fitCommentValues(); requestAnimationFrame(run); });

  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(start).catch(start);
  } else {
    window.addEventListener('load', start, { once: true });
    setTimeout(start, 150);
  }
})();
</script>
"""


def _build_html(certs: List[Dict[str, Any]], img_map: Dict[str, str] = {}, include_back: bool = True) -> str:
    CARDS_PER_PAGE = 10

    pages_html = ''
    chunks = [certs[i:i + CARDS_PER_PAGE] for i in range(0, len(certs), CARDS_PER_PAGE)]

    for chunk in chunks:
        front_rows = []
        for i in range(0, len(chunk), 2):
            row = chunk[i:i + 2]
            row_html = ''.join(_render_card_front(c, img_map) for c in row)
            front_rows.append(f'<div class="print-row">{row_html}</div>')
        pages_html += f'<div class="page"><div class="print-grid">{"".join(front_rows)}</div></div>'

        if include_back:
            back_rows = []
            for i in range(0, len(chunk), 2):
                pair = chunk[i:i + 2]
                if len(pair) == 2:
                    row_html = _render_card_back(pair[1], img_map) + _render_card_back(pair[0], img_map)
                else:
                    row_html = '<div style="width:8.6cm;height:5.5cm;flex-shrink:0"></div>' + _render_card_back(pair[0], img_map)
                back_rows.append(f'<div class="print-row">{row_html}</div>')
            pages_html += f'<div class="page"><div class="print-grid">{"".join(back_rows)}</div></div>'

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>{CSS}</style>
</head>
<body>
{pages_html}
{FIT_SCRIPT}
</body>
</html>"""


def _render_pdf_sync(html_path: str) -> bytes:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        # Extra flags beyond the original two trim Chromium's own baseline
        # footprint — confirmed via dmesg that the container's cgroup OOM
        # killer was killing the chrome-headless renderer process itself
        # once combined memory (uvicorn + Chromium main + renderer +
        # helper processes) crossed the container limit.
        browser = p.chromium.launch(args=[
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            # Multi-process Chromium (browser + separate renderer, IPC
            # between them) timed out past 90s per batch on this droplet's
            # single vCPU — no other core to hide the IPC/context-switch
            # overhead on. Memory is now handled by downscaling images
            # before embedding (the actual dominant footprint), so
            # single-process's memory-concentration downside matters much
            # less than its speed win here.
            '--single-process',
            '--disable-extensions',
            '--disable-background-networking',
            '--disable-default-apps',
            '--disable-sync',
            '--metrics-recording-only',
            '--disable-breakpad',
            '--js-flags=--max-old-space-size=128',
        ])
        page = browser.new_page()
        # Navigate to the staged file rather than injecting the markup:
        # a file:// origin lets the sibling images load from disk, so the
        # HTML carries relative names instead of megabytes of base64.
        page.goto(f'file://{html_path}', wait_until='networkidle')
        page.wait_for_function("window.__cardsFitted === true", timeout=5000)
        page.wait_for_timeout(800)
        pdf_bytes = page.pdf(
            format='A4',
            margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
            print_background=True,
        )
        browser.close()
    return pdf_bytes


def _render_pdf_worker(html_path: str, queue) -> None:
    """Entry point for the isolated subprocess — see _render_pdf_isolated."""
    try:
        queue.put(("ok", _render_pdf_sync(html_path)))
    except Exception as e:
        queue.put(("error", f"{type(e).__name__}: {e}"))


async def _render_pdf_isolated(html_path: str) -> bytes:
    """Render one batch's PDF in a brand-new OS process.

    Measured via docker stats across repeated in-process Chromium launches
    (same live Python process, one after another via asyncio.to_thread):
    memory plateaus well above single-request baseline between batches
    (~242MiB vs ~97MiB) and climbs further each batch until the container's
    cgroup OOM-killer takes out the renderer — Playwright/Chromium isn't
    fully releasing OS-level resources back across repeated launches in the
    same process. A fresh subprocess per batch sidesteps that entirely:
    Linux reclaims 100% of a process's memory when it exits, regardless of
    what leaked inside it.
    """
    import multiprocessing as mp
    import queue as queue_module

    ctx = mp.get_context("spawn")
    result_queue = ctx.Queue()
    proc = ctx.Process(target=_render_pdf_worker, args=(html_path, result_queue))
    proc.start()
    try:
        # A hard crash (e.g. Chromium segfaulting) kills the process without
        # ever putting anything on the queue — bound the wait so that fails
        # loudly instead of hanging the request forever.
        status, payload = await asyncio.to_thread(result_queue.get, True, 150)
    except queue_module.Empty:
        proc.terminate()
        raise RuntimeError(
            f"PDF render subprocess produced no result within 150s "
            f"(exit code: {proc.exitcode})"
        )
    finally:
        await asyncio.to_thread(proc.join, 5)
    if status == "error":
        raise RuntimeError(f"PDF render subprocess failed: {payload}")
    return payload


# A single render holds every cert's base64-encoded images plus the full
# HTML string in memory at once, on top of Chromium's own footprint — fine
# for a handful of certs, but a 100-cert request OOM-killed the backend
# (300M container limit). Rendering in bounded batches (each isolated in
# its own subprocess, see _render_pdf_isolated) and merging the resulting
# PDFs keeps peak memory roughly constant no matter how many certificates
# are requested overall (relevant since "download from history" can mean
# anywhere from a handful up to tens of thousands).
PDF_BATCH_SIZE = 8


async def _render_batch(batch: List[Dict[str, Any]]) -> bytes:
    """Stage one batch's assets to a temp dir, render it, then clean up."""
    import tempfile

    work_dir = Path(tempfile.mkdtemp(prefix="certpdf-"))
    try:
        img_map = await _prefetch_images(batch, work_dir)
        html_path = work_dir / "index.html"
        html_path.write_text(_build_html(batch, img_map), encoding="utf-8")
        return await _render_pdf_isolated(str(html_path))
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


async def generate_certificates_pdf_async(certs: List[Dict[str, Any]]) -> bytes:
    if len(certs) <= PDF_BATCH_SIZE:
        return await _render_batch(certs)

    from pypdf import PdfWriter, PdfReader

    writer = PdfWriter()
    for i in range(0, len(certs), PDF_BATCH_SIZE):
        pdf_bytes = await _render_batch(certs[i:i + PDF_BATCH_SIZE])
        for page in PdfReader(io.BytesIO(pdf_bytes)).pages:
            writer.add_page(page)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def generate_certificates_pdf(certs: List[Dict[str, Any]]) -> bytes:
    return asyncio.run(generate_certificates_pdf_async(certs))
