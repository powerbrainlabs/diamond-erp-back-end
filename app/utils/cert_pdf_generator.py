"""
Certificate PDF generator using Playwright (Chromium).
Renders the same HTML/CSS as the React frontend for pixel-perfect output.
"""
import asyncio
import base64
import io
import os
import httpx
from pathlib import Path
from typing import List, Dict, Any, Optional

ASSETS_DIR = Path(__file__).parent.parent.parent.parent / "diamond-erp-front-end" / "src" / "assets"

def _b64_img(path: str) -> str:
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    ext = path.rsplit(".", 1)[-1].lower()
    mime = "image/png" if ext == "png" else "image/jpeg"
    return f"data:{mime};base64,{data}"

GAC_HEADER_B64 = _b64_img(str(ASSETS_DIR / "gac_card_first_image.png"))
BG_PARTICLES_B64 = _b64_img(str(ASSETS_DIR / "BG-particles1.png"))

CERTIFICATE_FIELD_CONFIG = {
    'single_diamond': ['gross_weight', 'diamond_weight', 'cut', 'clarity', 'color', 'conclusion', 'comment'],
    'loose_diamond': ['dimension', 'weight', 'shape', 'clarity', 'color', 'hardness', 'sg', 'microscopic_obs', 'conclusion', 'comment'],
    'loose_stone': ['dimension', 'color', 'weight', 'shape', 'sg', 'ri', 'hardness', 'microscopic_obs', 'conclusion', 'comment'],
    'single_mounded': ['gross_weight', 'gemstone_weight', 'shape', 'sg', 'hardness', 'ri', 'microscopic_obs', 'conclusion', 'comment'],
    'double_mounded': ['gross_weight', 'primary_stone_weight', 'secondary_stone_weight', 'shape', 'sg', 'ri', 'hardness', 'microscopic_obs', 'conclusion'],
    'navaratna': ['gross_weight', 'diamond_weight', 'cut', 'color', 'clarity', 'conclusion', 'comment'],
}
BOLD_FIELDS = {'gross_weight', 'diamond_weight', 'weight', 'gemstone_weight', 'primary_stone_weight', 'secondary_stone_weight', 'conclusion', 'comment'}


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
        return ', '.join(str(v) for v in value)
    if isinstance(value, dict):
        return str(value)
    return str(value)


def _esc(s: str) -> str:
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


async def _fetch_as_b64(url: str) -> Optional[str]:
    """Fetch an image URL and return a base64 data URI, or None on failure."""
    if not url:
        return None
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return None
            content_type = r.headers.get('content-type', 'image/jpeg').split(';')[0].strip()
            data = base64.b64encode(r.content).decode()
            return f"data:{content_type};base64,{data}"
    except Exception:
        return None


async def _prefetch_images(certs: List[Dict[str, Any]]) -> Dict[str, str]:
    """Fetch all cert images concurrently and return url→base64 map."""
    urls = set()
    for cert in certs:
        for key in ('photo_signed_url', 'brand_logo_signed_url', 'qr_code_signed_url', 'rear_brand_logo_signed_url'):
            url = cert.get(key)
            if url:
                urls.add(url)
        # Add fallback QR URL
        if not cert.get('qr_code_signed_url') and cert.get('uuid'):
            urls.add(f'https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={cert["uuid"]}')

    results = await asyncio.gather(*[_fetch_as_b64(url) for url in urls])
    return {url: b64 for url, b64 in zip(urls, results) if b64}


def _render_card_front(cert: Dict[str, Any], img_map: Dict[str, str] = {}) -> str:
    fields = cert.get('fields') or {}
    schema = cert.get('schema') or {}
    cert_type = cert.get('type', '')
    group = schema.get('group', '')

    photo_url = img_map.get(cert.get('photo_signed_url') or '') or ''
    brand_logo_url = img_map.get(cert.get('brand_logo_signed_url') or '') or ''
    qr_url = img_map.get(cert.get('qr_code_signed_url') or '') or ''
    # Fallback: generate QR from qrserver.com if no stored QR
    if not qr_url and cert.get('uuid'):
        cert_uuid = cert['uuid']
        qr_url = f'https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={cert_uuid}'
    cert_number = _esc(cert.get('certificate_number') or '')
    description = _esc(cert.get('generated_description') or fields.get('description') or '')

    # Header images
    brand_logo_html = ''
    if brand_logo_url:
        brand_logo_html = f'<img src="{_esc(brand_logo_url)}" class="brand-logo" alt="Logo">'
    qr_html = ''
    if qr_url:
        qr_html = f'<img src="{_esc(qr_url)}" class="qr-code" alt="QR">'

    # Photo
    photo_html = f'<img src="{_esc(photo_url)}" class="cert-photo" alt="Photo">' if photo_url else ''

    # Build field rows
    rows_html = ''

    if cert_type == 'custom':
        if description:
            rows_html += f'''<div class="field-row full-width">
                <span class="label">Description</span><span class="sep">:</span>
                <span class="value desc-value">{description}</span></div>'''
        rows_html += f'''<div class="field-row">
            <span class="label">Certificate No</span><span class="sep">:</span>
            <span class="value">{cert_number}</span></div>'''
        for cf in (fields.get('custom_fields') or []):
            if cf.get('key') or cf.get('value'):
                rows_html += f'''<div class="field-row">
                    <span class="label">{_esc(cf.get("key",""))}</span><span class="sep">:</span>
                    <span class="value">{_esc(str(cf.get("value","")))}</span></div>'''
    else:
        allowed = CERTIFICATE_FIELD_CONFIG.get(group, [])
        schema_fields = schema.get('fields') or []

        if description:
            rows_html += f'''<div class="field-row full-width">
                <span class="label">Description</span><span class="sep">:</span>
                <span class="value desc-value">{description}</span></div>'''

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

            label = _esc(field.get('label', fname).replace(r'\s*\([^)]*\)', ''))
            # Replace stone weight label with gemstone name
            import re
            m = re.match(r'^(.+)_stone_w', fname)
            if m:
                gem_name = fields.get(f'{m.group(1)}_gemstone')
                if gem_name:
                    label = _esc(f'{gem_name} Weight')

            if field.get('field_type') == 'custom' and isinstance(raw, dict):
                label = _esc(raw.get('custom_label', label))
                display = _esc(str(raw.get('custom_value', '')))
            else:
                display = _esc(_format_value(raw, field.get('field_type', '')))
                unit = field.get('unit', '')
                if unit:
                    if unit.lower() in ('cts', 'ct'):
                        unit = 'ct' if (float(display) if display.replace('.', '', 1).isdigit() else 1) < 1 else 'cts'
                    display = f'{display} {unit}'

            is_full = field.get('field_type') in ('textarea', 'custom') or fname in ('description', 'comment')
            is_bold = fname in BOLD_FIELDS
            bold_style = 'font-weight:bold;' if is_bold else ''
            capitalize = 'text-transform:capitalize;' if fname == 'conclusion' else ''
            row_class = 'field-row full-width' if is_full else 'field-row'
            val_class = 'value desc-value' if is_full else 'value'

            rows_html += f'''<div class="{row_class}">
                <span class="label" style="{bold_style}">{label}</span><span class="sep">:</span>
                <span class="{val_class}" style="{bold_style}{capitalize}">{display}</span></div>'''

    # Density: count visible rows to scale font down if too many
    row_count = rows_html.count('field-row')
    if row_count >= 11:
        density_style = 'font-size:0.44em;line-height:8px;'
    elif row_count >= 8:
        density_style = 'font-size:0.49em;line-height:9px;'
    else:
        density_style = ''

    return f'''
<div class="cert-card" data-cert-uuid="{_esc(cert.get('uuid',''))}">
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
  </div>
  <div class="card-footer">For further information visit <b>www.thegac.in</b></div>
</div>'''


def _render_card_back(cert: Dict[str, Any], img_map: Dict[str, str] = {}) -> str:
    rear_logo_url = cert.get('rear_brand_logo_signed_url') or cert.get('brand_logo_signed_url') or ''
    rear_logo = img_map.get(rear_logo_url) or ''
    img_html = f'<img src="{_esc(rear_logo)}" class="back-logo" alt="Logo">' if rear_logo else ''
    return f'''
<div class="cert-card back-card" data-cert-uuid="{_esc(cert.get('uuid',''))}">
  <div class="back-media">
    {img_html}
  </div>
</div>'''


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Poppins', sans-serif;
  background: white;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

.page {
  page-break-after: always;
  width: 178mm;
  height: 289mm;
  margin: 0 auto;
  background: white;
  box-sizing: border-box;
  overflow: hidden;
}
.page:last-child { page-break-after: avoid; }

.print-grid {
  display: flex;
  flex-direction: column;
  gap: 2mm;
  width: calc(8.6cm * 2 + 3mm);
  margin: 0 auto;
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
  height: 42px;
  width: 59px;
  object-fit: contain;
  background: white;
  border-radius: 4px;
  padding: 4px;
}

.qr-code {
  width: 40px;
  height: 40px;
  object-fit: contain;
  flex-shrink: 0;
  margin-top: 10px;
}

.cert-photo {
  position: absolute;
  top: 94px;
  right: 18px;
  width: 50px;
  height: 54px;
  object-fit: contain;
  padding: 0 6px 0 0;
  box-sizing: border-box;
  z-index: 2;
}

.approx-label {
  font-size: 0.2em;
  position: absolute;
  font-weight: 500;
  top: 94px;
  right: 10px;
  height: 46px;
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
  padding-bottom: 12px;
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
}

.field-row {
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
}

.field-row.full-width { width: 100%; }

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

.card-footer {
  position: absolute;
  bottom: 5px;
  left: 0;
  width: 100%;
  text-align: center;
  font-size: 0.39em;
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
</body>
</html>"""


def _render_pdf_sync(html: str) -> bytes:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(args=['--no-sandbox', '--disable-dev-shm-usage'])
        page = browser.new_page()
        page.set_content(html, wait_until='networkidle')
        page.wait_for_timeout(800)
        pdf_bytes = page.pdf(
            format='A4',
            margin={'top': '4mm', 'right': '10mm', 'bottom': '4mm', 'left': '10mm'},
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
