"""
Certificate PDF generator using Playwright (Chromium).
Renders the same HTML/CSS as the React frontend for pixel-perfect output.
"""
import asyncio
import base64
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import quote

from ..core.config import settings
from ..core.minio_client import minio_client

ASSETS_DIR = Path(__file__).parent.parent / "assets"

def _b64_img(path: str) -> str:
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    ext = path.rsplit(".", 1)[-1].lower()
    mime = "image/png" if ext == "png" else "image/jpeg"
    return f"data:{mime};base64,{data}"

def _build_font_face_css() -> str:
    # Embed as data URIs rather than referencing file:// paths — confirmed
    # via a direct test (document.fonts.check() after render) that Poppins
    # silently fails to load via file:// regardless of Chromium launch
    # flags, most likely newer Chromium restricting file:// sub-resource
    # loads from a page not itself navigated to a file:// origin (this page
    # is set via page.set_content(), not a file:// navigation). Data URIs
    # sidestep that origin restriction entirely, and this file already uses
    # the same approach for the header/background images below.
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


def _is_square_image(data_uri: str) -> bool:
    """Return True if the image aspect ratio is close to 1:1 (0.85–1.15)."""
    try:
        _, b64data = data_uri.split(",", 1)
        raw = base64.b64decode(b64data)
        if raw[:8] == b'\x89PNG\r\n\x1a\n':
            w, h = struct.unpack('>II', raw[16:24])
        elif raw[:2] == b'\xff\xd8':
            i = 2
            w = h = 0
            while i < len(raw) - 9:
                if raw[i] != 0xff:
                    break
                marker = raw[i + 1]
                if marker in (0xC0, 0xC1, 0xC2):
                    h, w = struct.unpack('>HH', raw[i + 5:i + 9])
                    break
                length = struct.unpack('>H', raw[i + 2:i + 4])[0]
                i += 2 + length
            if not w or not h:
                return False
        else:
            return False
        ratio = w / h if h else 1
        return 0.85 <= ratio <= 1.15
    except Exception:
        return False


GAC_HEADER_B64 = _b64_img(str(ASSETS_DIR / "gac_card_first_image.png"))
BG_PARTICLES_B64 = _b64_img(str(ASSETS_DIR / "BG-particles1.png"))
POPPINS_FONT_CSS = _build_font_face_css()


def _certificate_public_url(cert_uuid: str) -> str:
    frontend_base = (settings.FRONTEND_URL or "http://localhost:5173").rstrip("/")
    return f"{frontend_base}/certificate/{cert_uuid}"


def _fallback_qr_url(cert_uuid: str) -> str:
    return f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={quote(_certificate_public_url(cert_uuid), safe='')}"

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
        max_dim = 900
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


async def _fetch_as_b64(url: str) -> Optional[str]:
    """Fetch an image URL and return a base64 data URI, or None on failure.

    Used for the QR code (an external qrserver.com URL, always reachable)
    and as a last-resort fallback for signed URLs that point back at this
    backend's own public domain — which containers generally can't reach via
    hairpin NAT, so that path is expected to fail. Kept short (vs. the old
    3×30s = 90s worst case) so a bulk PDF request never stalls long on it.
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
                data = base64.b64encode(r.content).decode()
                return f"data:{content_type};base64,{data}"
        except Exception:
            pass
    return None


def _storage_ref_to_b64(storage_ref: str) -> Optional[str]:
    """Read an object like 'bucket/object' directly from storage and return a data URI."""
    if not storage_ref or "/" not in storage_ref:
        return None
    try:
        bucket, object_name = storage_ref.split("/", 1)
        response = minio_client.get_object(bucket, object_name)
        content = response.read()
        content_type = response.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        # This is always a real cert/client photo (never the QR code, which
        # goes through _fetch_as_b64 instead), so lossy-shrinking it for
        # print-size embedding is safe.
        content, content_type = _downscale_for_pdf(content, content_type)
        data = base64.b64encode(content).decode()
        return f"data:{content_type};base64,{data}"
    except Exception:
        return None


async def _prefetch_images(certs: List[Dict[str, Any]]) -> Dict[str, str]:
    """Fetch all cert images concurrently and return url/storage-ref→base64 map.

    Two source types get merged into one map here so render functions never
    block on I/O per-cert:
    - storage refs ('bucket/key', e.g. cert['photo_url']) — read directly
      from R2, which is what actually works reliably (the signed HTTP URLs
      point back at this same backend's own public domain, which containers
      generally can't hairpin back to themselves through, so that path is
      kept only as a last-resort fallback for callers that lack a ref).
    - signed URLs (photo_signed_url etc., and the QR code) — fetched over
      HTTP, still needed for the QR code (an external qrserver.com URL).
    """
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
        # Add fallback QR URL
        if cert.get('uuid'):
            urls.add(_fallback_qr_url(cert["uuid"]))

    storage_results = await asyncio.gather(
        *[asyncio.to_thread(_storage_ref_to_b64, ref) for ref in storage_refs]
    )
    url_results = await asyncio.gather(*[_fetch_as_b64(url) for url in urls])

    img_map = {ref: b64 for ref, b64 in zip(storage_refs, storage_results) if b64}
    # Only fall back to the (possibly-hairpinned, slower) HTTP fetch for a
    # signed URL if nothing already resolved it via the direct storage ref.
    for url, b64 in zip(urls, url_results):
        if b64 and url not in img_map:
            img_map[url] = b64
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
    qr_url = img_map.get(_fallback_qr_url(cert['uuid'])) or _fallback_qr_url(cert['uuid']) if cert.get('uuid') else ''
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
    _photo_class = "cert-photo square" if photo_url and _is_square_image(photo_url) else "cert-photo"
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
    <img src="{GAC_HEADER_B64}" class="gac-header-img" alt="GAC">
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
        <img src="{BG_PARTICLES_B64}" alt="">
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
  /* Card text renders as small as ~5-10px (see the fit script below), and
     Chromium's PDF export garbles glyph positioning for small BOLD text
     specifically with this embedded font — confirmed via pdftotext on a
     real render ("Gross Weight" -> "G r o s s We ig h t"), reproduced
     across Chromium 130-151 and independent of TTF/WOFF2/single-process/
     font-weight-vs-separate-family, so it's not a version or config fix.
     `zoom` (unlike `transform`) participates in normal layout, so the
     existing fit script's getBoundingClientRect()/scrollHeight-based
     measurements keep working unchanged — render everything 4x bigger
     (well clear of the bug, confirmed clean at 16px+) and shrink the
     whole page back down via page.pdf's scale option in
     _render_pdf_sync, so the printed output is pixel-identical to the
     original design, just never actually shaped at a buggy small size.
  */
  zoom: 4;
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

  // Matches the CSS `zoom: 4` on body (see its comment). getComputedStyle()
  // still reports the authored, unzoomed font-size — confirmed via a direct
  // test (a `font-size: 8px` element under zoom:4 reports computed
  // fontSize "8px", not "32px") — but getBoundingClientRect()/scrollHeight
  // report the zoomed (4x) box geometry. minFont/maxFont below compare
  // against the unzoomed fontSize so need no change, but reservedGap and
  // the "how much extra room is there" check further down compare directly
  // against rect/scrollHeight measurements, so those raw pixel constants
  // need multiplying by this factor too — otherwise they're ~4x too small,
  // which under-reserves space and lets content overflow into the footer
  // (reproduced: "Comments" row and footer clipped off on denser cards).
  const ZOOM = 4;

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

    const reservedGap = (rowCount >= 10 ? 3.5 : rowCount <= 4 ? 1.5 : 2) * ZOOM;

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
      const shrinkRatio = clamp(finalAvailable / finalContent, 0.88, 0.98);
      fontSize = clamp(fontSize * shrinkRatio, minFont, maxFont);
      lineHeight = clamp(lineHeight * shrinkRatio, minLine, maxLine);
      fields.style.fontSize = `${fontSize.toFixed(2)}px`;
      fields.style.lineHeight = `${lineHeight.toFixed(2)}px`;
      return;
    }

    if (rowCount <= 10 && finalAvailable > finalContent + (4 * ZOOM)) {
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
        if (el.scrollWidth <= el.clientWidth + ZOOM) break;
        fs = Math.max(minFs, fs * 0.94);
        el.style.fontSize = fs.toFixed(2) + 'px';
      }
      // Even at the shrink floor, a genuinely long dynamically-built label
      // (e.g. two long gemstone names combined) can still be too wide for
      // 93px without becoming illegibly small. Wrapping to 2 lines keeps
      // the fixed label width (so every row's colon/value still lines up)
      // instead of overlapping into the value column.
      if (el.scrollWidth > el.clientWidth + ZOOM) {
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
      // getBoundingClientRect() is in the zoomed (4x) space, but a value
      // assigned to .style.top is an authored CSS length that itself gets
      // multiplied by zoom again at render time — divide back out or the
      // frame ends up 4x further down than intended (same class of bug as
      // reservedGap above, just for position instead of size).
      const newTop = (certNoRect.top - cardRect.top) / ZOOM;
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
        if (el.scrollWidth <= el.clientWidth + ZOOM) break;
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


def _render_pdf_sync(html: str) -> bytes:
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
        page.set_content(html, wait_until='networkidle')
        page.wait_for_function("window.__cardsFitted === true", timeout=5000)
        page.wait_for_timeout(800)
        pdf_bytes = page.pdf(
            format='A4',
            margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
            print_background=True,
            # Compensates the CSS `zoom: 4` on body (see its comment) —
            # net effect is 1x, output is the same physical size as before.
            scale=0.25,
        )
        browser.close()
    return pdf_bytes


def _render_pdf_worker(html: str, queue) -> None:
    """Entry point for the isolated subprocess — see _render_pdf_isolated."""
    try:
        queue.put(("ok", _render_pdf_sync(html)))
    except Exception as e:
        queue.put(("error", f"{type(e).__name__}: {e}"))


async def _render_pdf_isolated(html: str) -> bytes:
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
    proc = ctx.Process(target=_render_pdf_worker, args=(html, result_queue))
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


async def generate_certificates_pdf_async(certs: List[Dict[str, Any]]) -> bytes:
    if len(certs) <= PDF_BATCH_SIZE:
        img_map = await _prefetch_images(certs)
        html = _build_html(certs, img_map)
        return await _render_pdf_isolated(html)

    import io
    from pypdf import PdfWriter, PdfReader

    writer = PdfWriter()
    for i in range(0, len(certs), PDF_BATCH_SIZE):
        batch = certs[i:i + PDF_BATCH_SIZE]
        img_map = await _prefetch_images(batch)
        html = _build_html(batch, img_map)
        pdf_bytes = await _render_pdf_isolated(html)
        for page in PdfReader(io.BytesIO(pdf_bytes)).pages:
            writer.add_page(page)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def generate_certificates_pdf(certs: List[Dict[str, Any]]) -> bytes:
    return asyncio.run(generate_certificates_pdf_async(certs))
