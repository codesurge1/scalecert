"""Renders a `CertificateData` (app.services.certificate) into PDF bytes,
via reportlab, with a QR code encoding the certificate's full public
verify URL. Entirely in-memory (`io.BytesIO`) — nothing touches local disk
(CLAUDE.md: "Generated PDFs go to Supabase Storage, never local disk").

Reproduces, for data-entry/report fidelity only (not a copy of the
copyrighted OIML document): the instrument's identity/registration info,
the verification type, certificate number, issue date, the Weighing
test's full load/I/deltaL/E/Ec/mpe/pass-fail table (the OIML clause 8.3.3
checklist's priority item), and a one-line pass/fail summary for each
other test actually performed. See app/services/certificate.py's own
docstring for why each test's summary is computed the way it is.
"""

import io

from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.certificate import CertificateData

_HEADER_COLOR = colors.HexColor("#1e3a5f")


def _qr_drawing(url: str, size_mm: float = 32) -> Drawing:
    widget = qr.QrCodeWidget(url)
    x0, y0, x1, y1 = widget.getBounds()
    native_width, native_height = x1 - x0, y1 - y0
    size = size_mm * mm
    drawing = Drawing(size, size, transform=[size / native_width, 0, 0, size / native_height, 0, 0])
    drawing.add(widget)
    return drawing


def _result_text(passed) -> str:
    if passed is True:
        return "PASS"
    if passed is False:
        return "FAIL"
    return "Incomplete"


def generate_certificate_pdf(data: CertificateData, verify_url: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        title=f"Certificate {data.certificate_number}",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("CertTitle", parent=styles["Title"], fontSize=16, textColor=_HEADER_COLOR)
    heading_style = ParagraphStyle("CertHeading", parent=styles["Heading3"], textColor=_HEADER_COLOR, spaceBefore=6)

    story = []

    story.append(Paragraph("CERTIFICATE OF VERIFICATION", title_style))
    story.append(Paragraph("OIML R 76 &mdash; Non-Automatic Weighing Instrument", styles["Normal"]))
    story.append(Spacer(1, 5 * mm))

    instrument = data.instrument
    header_rows = [
        ["Certificate No.", data.certificate_number],
        ["Verification type", data.verification_type.replace("_", " ").title()],
        ["Issued", data.issued_at or "—"],
        ["Application no.", instrument.application_no or "—"],
        ["Type designation", instrument.type_designation or "—"],
        ["Manufacturer", instrument.manufacturer or "—"],
        ["Model", instrument.model or "—"],
        ["Accuracy class", instrument.accuracy_class.value],
        ["Max capacity", f"{instrument.max_capacity} g"],
        ["Verification scale interval (e)", f"{instrument.e_value} g"],
    ]
    header_table = Table(header_rows, colWidths=[65 * mm, 105 * mm])
    header_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 6 * mm))

    story.append(Paragraph("1. Weighing performance", heading_style))
    if data.weighing_rows:
        table_data = [["Load L (g)", "I (g)", "ΔL (g)", "E (g)", "Ec (g)", "mpe (g)", "Dir.", "Result"]]
        for row in data.weighing_rows:
            table_data.append(
                [row.L, row.I, row.delta_l, row.E, row.Ec, row.mpe, row.direction.upper(), _result_text(row.passed)]
            )
        weighing_table = Table(table_data, repeatRows=1)
        weighing_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _HEADER_COLOR),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        story.append(weighing_table)
        story.append(Spacer(1, 2 * mm))
        overall_text = _result_text(data.weighing_overall_passed) if data.weighing_overall_passed is not None else "N/A"
        story.append(Paragraph(f"<b>Overall: {overall_text}</b>", styles["Normal"]))
    else:
        story.append(Paragraph("No Weighing readings were recorded for this session.", styles["Normal"]))

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("2. Other tests performed", heading_style))
    other_rows = [["Test", "Result"]]
    for summary in data.other_tests:
        other_rows.append([summary.label, "Not performed" if not summary.performed else _result_text(summary.passed)])
    other_table = Table(other_rows, colWidths=[105 * mm, 65 * mm])
    other_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _HEADER_COLOR),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(other_table)

    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("Scan to verify this certificate online:", styles["Normal"]))
    story.append(Spacer(1, 2 * mm))
    story.append(_qr_drawing(verify_url))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(verify_url, styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()
