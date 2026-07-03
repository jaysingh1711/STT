"""
pdf_service.py
---------------
Generates a professional prescription PDF (letterhead + patient block +
Rx table + signature line). Returns bytes, nothing written to disk.
v3: clinic letterhead, patient info block, Rx symbol, signature area.
"""

import logging
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
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

# ── CLINIC / DOCTOR LETTERHEAD ────────────────────────────────────────────
# Edit these to match the actual clinic — or better, wire them from a
# config/env file (or a `doctor` table) and pass them into `record`
# as record["clinic_name"], record["doctor_name"], etc. Both paths work:
# the constants below are only used as a fallback.
DEFAULT_CLINIC_NAME    = "Care24 MediScribe "
DEFAULT_CLINIC_ADDRESS = "Vikhroli, Mumbai, Maharashtra"
DEFAULT_DOCTOR_NAME    = "Dr. —"
DEFAULT_DOCTOR_QUALS   = "MBBS, MD"
DEFAULT_REG_NO         = "Reg. No. —"


def generate_prescription_pdf(record: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=2.2*cm, leftMargin=2.2*cm,
        topMargin=1.6*cm, bottomMargin=2*cm,
        title="MediScribe Prescription",
    )
    styles = getSampleStyleSheet()

    clinic_style = ParagraphStyle("Clinic", parent=styles["Normal"],
        fontSize=18, fontName="Helvetica-Bold", textColor=DARK, leading=22)
    clinic_sub   = ParagraphStyle("ClinicSub", parent=styles["Normal"],
        fontSize=9, textColor=GREY, leading=13)
    doctor_style = ParagraphStyle("Doctor", parent=styles["Normal"],
        fontSize=12, fontName="Helvetica-Bold", textColor=TEAL,
        alignment=TA_RIGHT, leading=15)
    doctor_sub   = ParagraphStyle("DoctorSub", parent=styles["Normal"],
        fontSize=8.5, textColor=GREY, alignment=TA_RIGHT, leading=12)
    meta_style   = ParagraphStyle("Meta", parent=styles["Normal"],
        fontSize=9, textColor=GREY, alignment=TA_RIGHT, leading=13)

    patient_label = ParagraphStyle("PLabel", parent=styles["Normal"],
        fontSize=7.5, fontName="Helvetica-Bold", textColor=GREY, leading=10)
    patient_value = ParagraphStyle("PValue", parent=styles["Normal"],
        fontSize=11, fontName="Helvetica-Bold", textColor=DARK, leading=15)

    label_style = ParagraphStyle("Label", parent=styles["Normal"],
        fontSize=8, fontName="Helvetica-Bold", textColor=TEAL,
        spaceBefore=16, spaceAfter=5, leading=10)
    value_style = ParagraphStyle("Value", parent=styles["Normal"],
        fontSize=11, textColor=DARK, leading=16)
    rx_style    = ParagraphStyle("Rx", parent=styles["Normal"],
        fontSize=20, fontName="Helvetica-Bold", textColor=TEAL, leading=22)
    th_style    = ParagraphStyle("TH", parent=styles["Normal"],
        fontSize=9, fontName="Helvetica-Bold", textColor=DARK, leading=13)
    tc_style    = ParagraphStyle("TC", parent=styles["Normal"],
        fontSize=10, textColor=DARK, leading=14)
    tx_style    = ParagraphStyle("TX", parent=styles["Normal"],
        fontSize=9, textColor=GREY, leading=14)
    footer_style= ParagraphStyle("Footer", parent=styles["Normal"],
        fontSize=8, textColor=GREY, alignment=TA_CENTER)
    sig_name    = ParagraphStyle("SigName", parent=styles["Normal"],
        fontSize=10, fontName="Helvetica-Bold", textColor=DARK,
        alignment=TA_RIGHT, leading=13)
    sig_sub     = ParagraphStyle("SigSub", parent=styles["Normal"],
        fontSize=8, textColor=GREY, alignment=TA_RIGHT, leading=11)

    elements = []
    usable_w = PAGE_W - 4.4*cm

    # ── LETTERHEAD ──────────────────────────────────────────────────────
    clinic_name    = record.get("clinic_name", DEFAULT_CLINIC_NAME)
    clinic_address = record.get("clinic_address", DEFAULT_CLINIC_ADDRESS)
    doctor_name    = record.get("doctor_name", DEFAULT_DOCTOR_NAME)
    doctor_quals   = record.get("doctor_quals", DEFAULT_DOCTOR_QUALS)
    reg_no         = record.get("reg_no", DEFAULT_REG_NO)

    letterhead = Table([[
        [Paragraph(clinic_name, clinic_style),
         Paragraph(clinic_address, clinic_sub)],
        [Paragraph(doctor_name, doctor_style),
         Paragraph(doctor_quals, doctor_sub),
         Paragraph(reg_no, doctor_sub)],
    ]], colWidths=[usable_w*0.6, usable_w*0.4])
    letterhead.setStyle(TableStyle([
        ("VALIGN", (0,0),(-1,-1), "TOP"),
        ("ALIGN",  (1,0),(1,-1),  "RIGHT"),
        ("LEFTPADDING", (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(-1,-1), 0),
    ]))
    elements.append(letterhead)
    elements.append(Spacer(1, 0.3*cm))
    elements.append(HRFlowable(width="100%", thickness=1.2, color=TEAL, spaceAfter=10))

    # ── RECORD META (record #, date) ───────────────────────────────────
    date_str  = record.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    record_id = record.get("id", "—")
    elements.append(Paragraph(f"Record #{record_id}  ·  {date_str}", meta_style))
    elements.append(Spacer(1, 0.35*cm))

    # ── PATIENT INFO BLOCK ──────────────────────────────────────────────
    patient_name   = record.get("patient_name") or "—"
    patient_age    = record.get("patient_age") or "—"
    patient_gender = record.get("patient_gender") or "—"

    patient_block = Table([[
        [Paragraph("PATIENT NAME", patient_label), Paragraph(patient_name, patient_value)],
        [Paragraph("AGE", patient_label), Paragraph(str(patient_age), patient_value)],
        [Paragraph("GENDER", patient_label), Paragraph(patient_gender, patient_value)],
    ]], colWidths=[usable_w*0.5, usable_w*0.25, usable_w*0.25])
    patient_block.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), LIGHT),
        ("BOX",           (0,0),(-1,-1), 0.5, BORDER),
        ("INNERGRID",     (0,0),(-1,-1), 0.5, BORDER),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
    ]))
    elements.append(patient_block)
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

    # ── MEDICATIONS (with Rx symbol) ───────────────────────────────────
    rx_row = Table([[
        Paragraph("℞", rx_style),
        Paragraph("MEDICATIONS", label_style),
    ]], colWidths=[1*cm, usable_w-1*cm])
    rx_row.setStyle(TableStyle([
        ("VALIGN", (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0),(-1,-1), 0),
        ("TOPPADDING", (0,0),(-1,-1), 10),
    ]))
    elements.append(rx_row)

    medications = record.get("medications") or []

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

    # ── SIGNATURE BLOCK ──────────────────────────────────────────────────
    elements.append(Spacer(1, 1.2*cm))
    sig_table = Table([
        [Paragraph("", tx_style)],
        [HRFlowable(width=6*cm, thickness=0.8, color=DARK, hAlign="RIGHT")],
        [Paragraph(doctor_name, sig_name)],
        [Paragraph("Signature & Stamp", sig_sub)],
    ], colWidths=[usable_w])
    sig_table.setStyle(TableStyle([
        ("ALIGN", (0,0),(-1,-1), "RIGHT"),
        ("LEFTPADDING", (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(-1,-1), 0),
        ("TOPPADDING", (0,0),(-1,-1), 2),
        ("BOTTOMPADDING", (0,0),(-1,-1), 2),
    ]))
    elements.append(sig_table)

    # ── FOOTER ───────────────────────────────────────────────────────────
    elements.append(Spacer(1, 0.6*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6))
    elements.append(Paragraph(
        "This prescription was AI-assisted and reviewed by the treating physician. "
        "Generated by MediScribe.", footer_style))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes