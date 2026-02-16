import io
import os
from typing import List, Dict
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Colors
COLOR_PRIMARY = (139/255, 115/255, 85/255)      # #8b7355
COLOR_TEXT = (92/255, 77/255, 61/255)           # #5c4d3d
COLOR_TEXT_LIGHT = (120/255, 113/255, 106/255)  # #78716a
COLOR_BORDER = (168/255, 162/255, 158/255)      # #a8a29e
COLOR_RED = (220/255, 38/255, 38/255)           # #dc2626
COLOR_BG_CARD = (255/255, 255/255, 255/255)     # White

def draw_job_card(c: canvas.Canvas, x: float, y: float, job: dict, client: dict, manufacturer: dict, logo_path: str):
    width = 90 * mm
    height = 55 * mm
    padding = 4 * mm
    
    # Background & Border
    c.setStrokeColorRGB(*COLOR_BORDER)
    c.setFillColorRGB(*COLOR_BG_CARD)
    c.roundRect(x, y - height, width, height, 3*mm, fill=1, stroke=1)
    
    # --- HEADER ---
    header_y = y - padding
    
    # Logo (Left)
    logo_height = 8 * mm
    logo_width = 25 * mm # Max width
    if logo_path and os.path.exists(logo_path):
        try:
            img = ImageReader(logo_path)
            iw, ih = img.getSize()
            aspect = ih / float(iw)
            actual_w = logo_height / aspect
            c.drawImage(logo_path, x + padding, header_y - logo_height, width=actual_w, height=logo_height, mask='auto', preserveAspectRatio=True)
        except:
            pass
            
    # Job Title (Below Logo)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColorRGB(*COLOR_PRIMARY)
    title = "JOB CARD"
    if job.get("job_type") == "qc_job":
        title = "QC JOB CARD"
    elif job.get("job_type") == "certification_job":
        title = "CERTIFICATION JOB CARD"
    c.drawString(x + padding, header_y - logo_height - 3*mm, title)

    # Job Number & Status (Right)
    # Status Badge
    status = job.get("status", "pending").replace("_", " ").title()
    badge_w = 12 * mm
    badge_h = 3.5 * mm
    badge_x = x + width - padding - badge_w
    badge_y = header_y - logo_height - 4*mm  # Moved down from -2mm to -4mm
    
    # Badge Colors
    if status == "Pending":
       bg_col = (254/255, 243/255, 199/255)
       border_col = (245/255, 158/255, 11/255)
       text_col = (146/255, 64/255, 14/255)
    elif status == "In Progress":
       bg_col = (231/255, 229/255, 228/255)
       border_col = (168/255, 162/255, 158/255)
       text_col = (68/255, 64/255, 60/255)
    elif status == "Completed":
       bg_col = (209/255, 250/255, 229/255)
       border_col = (16/255, 185/255, 129/255)
       text_col = (6/255, 95/255, 70/255)
    else:
       bg_col = (254/255, 226/255, 226/255)
       border_col = (239/255, 68/255, 68/255)
       text_col = (153/255, 27/255, 27/255)

    # Job Number
    c.setFont("Helvetica", 6)
    c.setFillColorRGB(*COLOR_TEXT_LIGHT)
    c.drawRightString(x + width - padding, header_y - 2*mm, "Job #")
    
    c.setFont("Helvetica-Bold", 12)
    c.setFillColorRGB(*COLOR_PRIMARY)
    c.drawRightString(x + width - padding, header_y - 6.5*mm, str(job.get("job_number", "")))

    # Draw Badge
    c.setFillColorRGB(*bg_col)
    c.setStrokeColorRGB(*border_col)
    c.roundRect(badge_x, badge_y, badge_w, badge_h, 1*mm, fill=1, stroke=1)
    c.setFillColorRGB(*text_col)
    c.setFont("Helvetica-Bold", 5)
    c.drawCentredString(badge_x + badge_w/2, badge_y + 1.2*mm, status)

    # Separator Line - moved down to create more space from badge
    line_y = header_y - logo_height - 7*mm  # Increased from 4.5mm to 7mm
    c.setStrokeColorRGB(*COLOR_PRIMARY)
    c.setLineWidth(1)
    c.line(x + padding, line_y, x + width - padding, line_y)

    # --- GRID CONTENT ---
    # Build fields list matching frontend logic exactly
    fields = []
    
    # Row 1, Col 1: Client (Always)
    fields.append(("Client", client.get("name") if client else "N/A", False))
    
    # Row 1, Col 2: Contact OR Item Type
    phone = client.get("phone") if client else None
    if phone:
        fields.append(("Contact", phone, False))
    else:
        i_type = job.get("item_type", "").replace("_", " ").title()
        fields.append(("Item Type", i_type, False))
    
    # Row 2, Col 1: Manufacturer OR Item Type
    if manufacturer:
        fields.append(("Manufacturer", manufacturer.get("name", "N/A"), False))
    elif phone:
        # If we showed contact above, show item type here
        i_type = job.get("item_type", "").replace("_", " ").title()
        fields.append(("Item Type", i_type, False))
    # else: already showed item type in row 1
    
    # Row 2, Col 2: Quantity/Weight/Size
    if job.get("item_type") == "loose_diamond":
        if job.get("item_weight"):
            fields.append(("Weight", f"{job.get('item_weight')} ct", False))
        elif job.get("item_size"):
            fields.append(("Size", str(job.get("item_size")), False))
    else:
        if job.get("item_quantity"):
            fields.append(("Quantity", f"{job.get('item_quantity')} pcs", False))
    
    # Row 3: Size (for loose diamond if both weight and size exist)
    if job.get("item_type") == "loose_diamond" and job.get("item_weight") and job.get("item_size"):
        fields.append(("Size", str(job.get("item_size")), False))
    
    # Row 3/4, Col 1: Received
    rec = job.get("received_date") or job.get("received_datetime") or job.get("created_at")
    if rec:
        try:
            from datetime import datetime
            if isinstance(rec, str):
                # Parse ISO format
                rec_dt = datetime.fromisoformat(rec.replace('Z', '+00:00'))
            else:
                rec_dt = rec
            rec_formatted = rec_dt.strftime("%b %d, %Y")
            # Add time if received_datetime exists
            if job.get("received_datetime"):
                time_str = rec_dt.strftime("%I:%M %p")
                rec_formatted = f"{rec_formatted}\n{time_str}"
        except:
            rec_formatted = str(rec).split('T')[0]
        fields.append(("Received", rec_formatted, False))
    
    # Row 3/4, Col 2: Delivery
    dele = job.get("expected_delivery_date")
    if dele:
        try:
            from datetime import datetime
            if isinstance(dele, str):
                dele_dt = datetime.fromisoformat(dele.replace('Z', '+00:00'))
            else:
                dele_dt = dele
            dele_formatted = dele_dt.strftime("%b %d, %Y")
        except:
            dele_formatted = str(dele).split('T')[0]
        fields.append(("Delivery", dele_formatted, True))

    # Render Grid
    start_y = line_y - 3*mm  # Reduced from 4mm
    col_width = (width - 2*padding) / 2
    row_height = 5.5 * mm  # Reduced from 6mm to 5.5mm
    
    # Font settings
    lbl_size = 5
    val_size = 7
    
    current_col = 0
    current_row = 0
    
    for label, value, is_red in fields:
        cx = x + padding + (current_col * col_width)
        cy = start_y - (current_row * row_height)
        
        # Label
        c.setFont("Helvetica", lbl_size)
        c.setFillColorRGB(*COLOR_TEXT_LIGHT)
        c.drawString(cx, cy, label.upper())
        
        # Value (handle multiline for received date with time)
        c.setFont("Helvetica-Bold", val_size)
        if is_red:
            c.setFillColorRGB(*COLOR_RED)
        else:
            c.setFillColorRGB(*COLOR_TEXT)
        
        # Handle multiline values
        val_str = str(value)
        if '\n' in val_str:
            lines = val_str.split('\n')
            c.drawString(cx, cy - 2.5*mm, lines[0])
            if len(lines) > 1:
                c.setFont("Helvetica", 5)
                c.setFillColorRGB(*COLOR_TEXT_LIGHT)
                c.drawString(cx, cy - 4.5*mm, lines[1])  # Reduced from 5mm
        else:
            if len(val_str) > 22: 
                val_str = val_str[:20] + "..."
            c.drawString(cx, cy - 2.5*mm, val_str)
        
        # Advance
        current_col += 1
        if current_col >= 2:
            current_col = 0
            current_row += 1
            
    # --- FOOTER (Desc & Notes) ---
    footer_y = start_y - (4 * row_height) - 0.5*mm  # Reduced from 1mm
    
    # Description
    desc = job.get("item_description")
    if desc:
        c.setFont("Helvetica", lbl_size)
        c.setFillColorRGB(*COLOR_TEXT_LIGHT)
        c.drawString(x + padding, footer_y, "DESCRIPTION")
        
        c.setFont("Helvetica", 5.5)  # Slightly smaller font
        c.setFillColorRGB(*COLOR_TEXT)
        if len(desc) > 90: desc = desc[:87] + "..."  # Allow slightly more text
        c.drawString(x + padding, footer_y - 2.5*mm, desc)
        footer_y -= 5*mm  # Reduced from 5.5mm
        
    # Notes
    notes = job.get("notes")
    if notes:
        c.setFont("Helvetica", lbl_size)
        c.setFillColorRGB(*COLOR_TEXT_LIGHT)
        c.drawString(x + padding, footer_y, "NOTES")
        
        c.setFont("Helvetica-Oblique", 5.5)  # Slightly smaller font
        c.setFillColorRGB(*COLOR_TEXT)
        if len(notes) > 90: notes = notes[:87] + "..."  # Allow slightly more text
        c.drawString(x + padding, footer_y - 2.5*mm, notes)


def generate_jobs_pdf(jobs_data: List[dict], logo_path: str) -> io.BytesIO:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Grid settings
    margin_left = 10 * mm
    margin_top = 10 * mm
    card_width = 90 * mm
    card_height = 55 * mm
    gap_x = 10 * mm
    gap_y = 10 * mm
    
    cols = 2
    rows = 4 # Fits 4 rows of 55mm = 220mm + margins on 297mm page
    
    x = margin_left
    y = height - margin_top
    
    col_idx = 0
    row_idx = 0
    
    for item in jobs_data:
        job = item["job"]
        client = item.get("client")
        manufacturer = item.get("manufacturer")
        
        draw_job_card(c, x, y, job, client, manufacturer, logo_path)
        
        col_idx += 1
        x += card_width + gap_x
        
        if col_idx >= cols:
            col_idx = 0
            x = margin_left
            row_idx += 1
            y -= card_height + gap_y
            
        if row_idx >= rows:
            c.showPage()
            x = margin_left
            y = height - margin_top
            col_idx = 0
            row_idx = 0
            
    c.save()
    buffer.seek(0)
    return buffer
