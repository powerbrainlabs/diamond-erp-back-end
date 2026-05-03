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
    fonts_dir = ASSETS_DIR / "fonts"
    css = ""
    for weight, filename in [(400, "Poppins-Regular.ttf"), (500, "Poppins-Medium.ttf"), (600, "Poppins-SemiBold.ttf"), (700, "Poppins-Bold.ttf")]:
        font_path = fonts_dir / filename
        if font_path.exists():
            css += f"@font-face {{font-family:'Poppins';font-style:normal;font-weight:{weight};src:url('file://{font_path}') format('truetype');}}\n"
    return css

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
    'loose_diamond': ['dimension', 'weight', 'shape', 'clarity', 'color', 'hardness', 'sg', 'microscopic_obs', 'conclusion', 'comment'],
    'loose_stone': ['dimension', 'color', 'weight', 'shape', 'sg', 'ri', 'hardness', 'microscopic_obs', 'conclusion', 'comment'],
    'single_mounded': ['gross_weight', 'gemstone_weight', 'shape', 'sg', 'hardness', 'ri', 'microscopic_obs', 'conclusion', 'comment'],
    'double_mounded': ['gross_weight', 'primary_stone_weight', 'secondary_stone_weight', 'shape', 'sg', 'ri', 'hardness', 'microscopic_obs', 'conclusion'],
    'navaratna': ['gross_weight', 'diamond_weight', 'cut', 'color', 'clarity', 'conclusion', 'comment'],
}
BOLD_FIELDS = {'gross_weight', 'diamond_weight', 'weight', 'gemstone_weight', 'primary_stone_weight', 'secondary_stone_weight', 'conclusion'}


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


async def _fetch_as_b64(url: str) -> Optional[str]:
    """Fetch an image URL and return a base64 data URI, or None on failure."""
    if not url:
        return None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True, verify=False) as client:
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
        try:
            content = response.read()
            content_type = response.headers.get("content-type", "image/jpeg").split(";")[0].strip()
            data = base64.b64encode(content).decode()
            return f"data:{content_type};base64,{data}"
        finally:
            response.close()
            response.release_conn()
    except Exception:
        return None


async def _prefetch_images(certs: List[Dict[str, Any]]) -> Dict[str, str]:
    """Fetch all cert images concurrently and return url→base64 map."""
    urls = set()
    for cert in certs:
        for key in ('photo_signed_url', 'brand_logo_signed_url', 'rear_brand_logo_signed_url'):
            url = cert.get(key)
            if url:
                urls.add(url)
        # Add fallback QR URL
        if cert.get('uuid'):
            urls.add(_fallback_qr_url(cert["uuid"]))

    results = await asyncio.gather(*[_fetch_as_b64(url) for url in urls])
    return {url: b64 for url, b64 in zip(urls, results) if b64}


def _render_card_front(cert: Dict[str, Any], img_map: Dict[str, str] = {}) -> str:
    fields = cert.get('fields') or {}
    schema = cert.get('schema') or {}
    cert_type = cert.get('type', '')
    group = schema.get('group', '')

    photo_url = (
        _storage_ref_to_b64(cert.get('photo_url') or '')
        or img_map.get(cert.get('photo_signed_url') or '')
        or ''
    )
    brand_logo_url = (
        _storage_ref_to_b64(cert.get('brand_logo_url') or '')
        or img_map.get(cert.get('brand_logo_signed_url') or '')
        or ''
    )
    qr_url = img_map.get(_fallback_qr_url(cert['uuid'])) or _fallback_qr_url(cert['uuid']) if cert.get('uuid') else ''
    cert_number = _esc(_normalize_display_text(cert.get('certificate_number') or ''))
    description = _esc(_normalize_display_text(cert.get('generated_description') or fields.get('description') or ''))

    # Header images
    brand_logo_html = ''
    if brand_logo_url:
        brand_logo_html = f'<img src="{_esc(brand_logo_url)}" class="brand-logo" alt="Logo">'
    qr_html = ''
    if qr_url:
        qr_html = f'<img src="{_esc(qr_url)}" class="qr-code" alt="QR">'

    # Photo
    photo_html = (
        f'''<div class="cert-photo-frame">
  <img src="{_esc(photo_url)}" class="cert-photo" alt="Photo">
</div>'''
        if photo_url else ''
    )

    # Build field rows
    rows_html = ''
    visual_row_count = 0

    if cert_type == 'custom':
        if description:
            visual_row_count += _estimate_text_lines(description, chars_per_line=42, min_lines=1, max_lines=3)
            rows_html += f'''<div class="field-row full-width">
                <span class="label">Description</span><span class="sep">:</span>
                <span class="value desc-value">{description}</span></div>'''
        visual_row_count += _estimate_text_lines(cert_number, chars_per_line=24)
        rows_html += f'''<div class="field-row">
            <span class="label">Certificate No</span><span class="sep">:</span>
            <span class="value">{cert_number}</span></div>'''
        for cf in (fields.get('custom_fields') or []):
            if cf.get('key') or cf.get('value'):
                custom_value = _esc(_normalize_display_text(cf.get("value", "")))
                visual_row_count += _estimate_text_lines(custom_value, chars_per_line=24, min_lines=1, max_lines=3)
                rows_html += f'''<div class="field-row">
                    <span class="label">{_esc(_normalize_display_text(cf.get("key", "")))}</span><span class="sep">:</span>
                    <span class="value">{custom_value}</span></div>'''
    else:
        allowed = CERTIFICATE_FIELD_CONFIG.get(group, [])
        schema_fields = schema.get('fields') or []

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

        for field in sorted_fields:
            fname = field.get('field_name', '')
            raw = fields.get(fname)
            if raw is None or raw == '':
                continue

            label = _normalize_display_text(field.get('label', fname))
            # Replace stone weight label with gemstone name
            import re
            m = re.match(r'^(.+)_stone_w', fname)
            if m:
                gem_name = fields.get(f'{m.group(1)}_gemstone')
                if gem_name:
                    label = _normalize_display_text(f'{gem_name} Weight')

            if field.get('field_type') == 'custom' and isinstance(raw, dict):
                label = _normalize_display_text(raw.get('custom_label', label))
                display = _esc(_normalize_display_text(raw.get('custom_value', '')))
            else:
                display = _esc(_format_value(raw, field.get('field_type', '')))
                unit = field.get('unit', '')
                if unit:
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

            rows_html += f'''<div class="{row_class}">
                <span class="label" style="{bold_style}">{label}</span><span class="sep">:</span>
                <span class="{val_class}" style="{bold_style}{capitalize}">{display}</span></div>'''

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
  <span class="approx-label">Approx Photo</span>
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
        _storage_ref_to_b64(cert.get('rear_brand_logo_url') or '')
        or _storage_ref_to_b64(cert.get('brand_logo_url') or '')
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
  gap: 2mm;
  width: 175mm;
  margin-left: 17.5mm;
  margin-top: 7mm;
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
  width: 8.6cm;
  height: 5.5cm;
  padding: 0;
  border-top: 1px dashed #2b1fb4;
  border-left: 1px dashed #2b1fb4;
  box-sizing: border-box;
  position: relative;
  font-family: 'Poppins', Arial, sans-serif;
  page-break-inside: avoid;
  overflow: hidden;
  contain: paint;
}

.card-header {
  position: relative;
}

.gac-header-img {
  width: 100%;
  position: absolute;
  left: 0;
}

.header-right {
  position: absolute;
  top: 3.5px;
  right: 4px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
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
  width: 48px;
  height: 46px;
  object-fit: contain;
  flex-shrink: 0;
  margin-top: 4px;
  margin-right: -3px;
  align-self: flex-start;
}

.cert-photo-frame {
  position: absolute;
  top: 91px;
  right: 22px;
  width: 68px;
  height: 68px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  box-sizing: border-box;
  z-index: 2;
}

.cert-photo {
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: center;
  padding: 0 2px 0 0;
  box-sizing: border-box;
}

.approx-label {
  font-size: 0.2em;
  position: absolute;
  font-weight: 500;
  top: 91px;
  right: 10px;
  height: 60px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  white-space: nowrap;
  color: #4b5563;
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
  overflow: hidden;
}

.field-row {
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  font-size: 0.87em;
}

.field-row.full-width { width: 100%; }

.comment-row {
  width: calc(100% + 34px) !important;
}

.comment-row .label {
  width: 82px;
}

.comment-row .sep {
  margin: 0 5px;
}

.label {
  width: 82px;
  flex-shrink: 0;
  font-weight: 400;
}

.sep {
  margin: 0 5px;
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
  font-size: 1em;
  line-height: 1.05;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  word-break: normal;
  letter-spacing: -0.02em;
  word-spacing: -0.02em;
}

.card-footer {
  width: 100%;
  text-align: center;
  font-size: 0.39em;
  padding-bottom: 1px;
  background: white;
  z-index: 3;
}

/* Back card */
.back-card {
  border: none;
}
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
      const shrinkRatio = clamp(finalAvailable / finalContent, 0.88, 0.98);
      fontSize = clamp(fontSize * shrinkRatio, minFont, maxFont);
      lineHeight = clamp(lineHeight * shrinkRatio, minLine, maxLine);
      fields.style.fontSize = `${fontSize.toFixed(2)}px`;
      fields.style.lineHeight = `${lineHeight.toFixed(2)}px`;
      return;
    }

    if (rowCount <= 10 && finalAvailable > finalContent + 4) {
      const fillRatio = clamp(finalAvailable / finalContent, 1, rowCount <= 4 ? 1.1 : rowCount <= 8 ? 1.06 : 1.04);
      fields.style.fontSize = `${clamp(fontSize * fillRatio, minFont, maxFont).toFixed(2)}px`;
      fields.style.lineHeight = `${clamp(lineHeight * fillRatio, minLine, maxLine).toFixed(2)}px`;
    }
  }

  function run() {
    document.querySelectorAll('.cert-card:not(.back-card)').forEach(fitCard);
    window.__cardsFitted = true;
  }

  const start = () => requestAnimationFrame(() => requestAnimationFrame(run));

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
        browser = p.chromium.launch(args=['--no-sandbox', '--disable-dev-shm-usage'])
        page = browser.new_page()
        page.set_content(html, wait_until='networkidle')
        page.wait_for_function("window.__cardsFitted === true", timeout=5000)
        page.wait_for_timeout(800)
        pdf_bytes = page.pdf(
            format='A4',
            margin={'top': '0', 'right': '0', 'bottom': '0', 'left': '0'},
            print_background=True,
        )
        browser.close()
    return pdf_bytes


async def generate_certificates_pdf_async(certs: List[Dict[str, Any]]) -> bytes:
    img_map = await _prefetch_images(certs)
    html = _build_html(certs, img_map)
    return await asyncio.to_thread(_render_pdf_sync, html)


def generate_certificates_pdf(certs: List[Dict[str, Any]]) -> bytes:
    return asyncio.run(generate_certificates_pdf_async(certs))
