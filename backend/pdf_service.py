"""
pdf_service.py
---------------
Generates a clean prescription PDF. Returns bytes, nothing written to disk.
v2: teal header band, better column widths, word wrapping, teal labels.
"""

import logging
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, KeepTogether
)

logger = logging.getLogger("pdf_service")

PAGE_W = A4[0]
TEAL   = colors.HexColor("#2dd4a7")
DARK   = colors.HexColor("#0e1726")
GREY   = colors.HexColor("#8d98ae")
LIGHT  = colors.HexColor("#f0f4f8")
WHITE  = colors.white
BORDER = colors.HexColor("#e2e8f0")


def generate_prescription_pdf(record: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2.2*cm, leftMargin=2.2*cm,
        topMargin=1.8*cm, bottomMargin=2*cm,
        title="MediScribe Prescription",
    )
    styles = getSampleStyleSheet()

    brand_style = ParagraphStyle("Brand", parent=styles["Normal"],
        fontSize=26, fontName="Helvetica-Bold", textColor=WHITE, leading=30)
    brand_sub   = ParagraphStyle("BrandSub", parent=styles["Normal"],
        fontSize=10, textColor=colors.HexColor("#c9e8e0"), leading=14)
    meta_right  = ParagraphStyle("MetaR", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#c9e8e0"), alignment=1, leading=13)
    label_style = ParagraphStyle("Label", parent=styles["Normal"],
        fontSize=8, fontName="Helvetica-Bold", textColor=TEAL,
        spaceBefore=16, spaceAfter=5, leading=10)
    value_style = ParagraphStyle("Value", parent=styles["Normal"],
        fontSize=11, textColor=DARK, leading=16)
    th_style    = ParagraphStyle("TH", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica-Bold", textColor=DARK, leading=13)
    tc_style    = ParagraphStyle("TC", parent=styles["Normal"],
        fontSize=10, textColor=DARK, leading=14)
    tx_style    = ParagraphStyle("TX", parent=styles["Normal"],
        fontSize=9, textColor=GREY, leading=14)
    footer_style= ParagraphStyle("Footer", parent=styles["Normal"],
        fontSize=8, textColor=GREY, alignment=TA_CENTER)

    elements = []

    # ── HEADER BAND ─────────────────────────────────────────────────────
    date_str  = record.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    record_id = record.get("id", "—")

    header_table = Table([[
        [Paragraph("MediScribe", brand_style),
         Paragraph("AI Clinical Notes — Prescription Record", brand_sub)],
        [Paragraph(f"Record <b>#{record_id}</b>", meta_right),
         Paragraph(date_str, meta_right)],
    ]],
        colWidths=[(PAGE_W-4.4*cm)*0.65, (PAGE_W-4.4*cm)*0.35],
    )
    header_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), TEAL),
        ("TOPPADDING",    (0,0),(-1,-1), 16),
        ("BOTTOMPADDING", (0,0),(-1,-1), 16),
        ("LEFTPADDING",   (0,0),(0,-1),  18),
        ("RIGHTPADDING",  (1,0),(1,-1),  18),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("ALIGN",         (1,0),(1,-1),  "RIGHT"),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.5*cm))

    # ── SYMPTOMS ────────────────────────────────────────────────────────
    symptoms = (record.get("symptoms") or "").strip()
    if symptoms:
        elements.append(Paragraph("SYMPTOMS", label_style))
        elements.append(Paragraph(symptoms, value_style))

    # ── DIAGNOSIS ───────────────────────────────────────────────────────
    diagnosis = (record.get("diagnosis") or "").strip()
    elements.append(Paragraph("DIAGNOSIS", label_style))
    elements.append(Paragraph(diagnosis or "—", value_style))

    # ── MEDICATIONS ─────────────────────────────────────────────────────
    elements.append(Paragraph("MEDICATIONS", label_style))
    medications = record.get("medications") or []
    usable_w = PAGE_W - 4.4*cm

    if medications:
        col_w = [usable_w*0.20, usable_w*0.13, usable_w*0.20,
                 usable_w*0.13, usable_w*0.34]
        rows = [[
            Paragraph("Medication", th_style),
            Paragraph("Dosage",     th_style),
            Paragraph("Frequency",  th_style),
            Paragraph("Duration",   th_style),
            Paragraph("Timing",     th_style),
        ]]
        for med in medications:
            timing = med.get("timing") or []
            rows.append([
                Paragraph(med.get("name","—"),      tc_style),
                Paragraph(med.get("dosage","—"),    tc_style),
                Paragraph(med.get("frequency","—"), tc_style),
                Paragraph(med.get("duration","—"),  tc_style),
                Paragraph(", ".join(timing) if timing else "—", tc_style),
            ])
        t = Table(rows, colWidths=col_w, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,0),  LIGHT),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, colors.HexColor("#f9fafb")]),
            ("GRID",          (0,0),(-1,-1), 0.5, BORDER),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("LEFTPADDING",   (0,0),(-1,-1), 8),
            ("RIGHTPADDING",  (0,0),(-1,-1), 8),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ]))
        elements.append(KeepTogether([t]))
    else:
        elements.append(Paragraph("No medications recorded.", value_style))

    # ── FOLLOW-UP ────────────────────────────────────────────────────────
    follow_up = (record.get("follow_up") or "").strip()
    elements.append(Paragraph("FOLLOW-UP", label_style))
    elements.append(Paragraph(follow_up or "—", value_style))

    # ── ORIGINAL DICTATION ──────────────────────────────────────────────
    elements.append(Spacer(1, 0.5*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=8))
    elements.append(Paragraph("ORIGINAL DICTATION", label_style))
    elements.append(Paragraph(record.get("transcript",""), tx_style))

    # ── FOOTER ───────────────────────────────────────────────────────────
    elements.append(Spacer(1, 0.8*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6))
    elements.append(Paragraph(
        "This prescription was AI-assisted and reviewed by the treating physician. "
        "Generated by MediScribe.", footer_style))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes