# MFRPdfTool.py
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
import os

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


@dataclass
class MFRSection:
    title: str
    content: str


@dataclass
class MFRInput:
    date: Optional[str] = None
    from_line: Optional[str] = None
    to_line: Optional[str] = None
    subject: str = "MEMORANDUM FOR RECORD"
    suspense: Optional[str] = None
    references: List[str] = field(default_factory=list)

    # EITHER sections OR body_paragraphs
    sections: List[MFRSection] = field(default_factory=list)
    body_paragraphs: List[str] = field(default_factory=list)

    point_of_contact: Optional[str] = None
    signature_name: Optional[str] = None
    signature_block: Optional[str] = None
    signature_extra: Optional[str] = None
    output_path: str = "MFR.pdf"


class MFRPdfTool:
    """Generate a Memorandum for Record (MFR) PDF from structured inputs."""

    name: str = "mfr_pdf"
    description: str = "Generate a Memorandum for Record (MFR) PDF from structured inputs."

    schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "date": {"type": ["string", "null"]},
            "from_line": {"type": ["string", "null"]},
            "to_line": {"type": ["string", "null"]},
            "subject": {"type": "string"},
            "suspense": {"type": ["string", "null"]},
            "references": {"type": "array", "items": {"type": "string"}},

            # Structured sections (preferred)
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["title", "content"],
                },
            },

            # Legacy: body_paragraphs
            "body_paragraphs": {"type": "array", "items": {"type": "string"}},

            "point_of_contact": {"type": ["string", "null"]},
            "signature_name": {"type": ["string", "null"]},
            "signature_block": {"type": ["string", "null"]},
            "signature_extra": {"type": ["string", "null"]},
            "output_path": {"type": "string"},
        },
        "required": ["subject", "output_path"],
    }

    def run(self, **kwargs) -> Dict[str, Any]:
        """Main entry point to generate the MFR PDF."""
        sections_raw = kwargs.get("sections", [])
        sections = [
            MFRSection(title=s.get("title", ""), content=s.get("content", ""))
            for s in sections_raw
            if isinstance(s, dict)
        ]

        data = MFRInput(
            date=kwargs.get("date"),
            from_line=kwargs.get("from_line"),
            to_line=kwargs.get("to_line"),
            subject=kwargs.get("subject", "MEMORANDUM FOR RECORD"),
            suspense=kwargs.get("suspense"),
            references=kwargs.get("references", []),
            sections=sections,
            body_paragraphs=kwargs.get("body_paragraphs", []),
            point_of_contact=kwargs.get("point_of_contact"),
            signature_name=kwargs.get("signature_name"),
            signature_block=kwargs.get("signature_block"),
            signature_extra=kwargs.get("signature_extra"),
            output_path=kwargs.get("output_path", "MFR.pdf"),
        )

        if not data.date:
            data.date = datetime.now().strftime("%d %b %Y")

        os.makedirs(os.path.dirname(data.output_path) or ".", exist_ok=True)

        self._build_pdf(data)
        return {"ok": True, "path": data.output_path}

    def _build_pdf(self, data: MFRInput):
        """Internal helper to layout the PDF document."""
        doc = SimpleDocTemplate(
            data.output_path,
            pagesize=LETTER,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "Title",
            parent=styles["Title"],
            alignment=TA_CENTER,
            fontName="Times-Bold",
            fontSize=14,
            spaceAfter=10,
        )
        header_style = ParagraphStyle(
            "Header",
            parent=styles["Normal"],
            alignment=TA_LEFT,
            fontName="Times-Roman",
            fontSize=11,
            leading=15,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            alignment=TA_LEFT,
            fontName="Times-Roman",
            fontSize=11,
            leading=16,
            spaceAfter=8,
        )
        small_italic = ParagraphStyle(
            "SmallItalic",
            parent=styles["Normal"],
            alignment=TA_LEFT,
            fontName="Times-Italic",
            fontSize=10,
            leading=14,
            spaceBefore=6,
        )
        # NEW: right-aligned signature style
        signature_style = ParagraphStyle(
            "Signature",
            parent=body_style,
            alignment=TA_RIGHT,
            spaceBefore=12,
        )

        flow = []
        flow.append(Paragraph("MEMORANDUM FOR RECORD", title_style))
        flow.append(Spacer(1, 6))

        # Header block (DATE, FROM, TO, SUBJECT, SUSPENSE)
        header_rows = []
        header_rows.append(["DATE:", data.date])
        if data.from_line:
            header_rows.append(["FROM:", data.from_line])
        if data.to_line:
            header_rows.append(["TO:", data.to_line])
        header_rows.append(["SUBJECT:", data.subject])
        if data.suspense:
            header_rows.append(["SUSPENSE:", data.suspense])

        t = Table(header_rows, colWidths=[1.1 * inch, 5.9 * inch])
        t.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
            ("FONTSIZE", (0, 0), (-1, -1), 11),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        flow.append(t)
        flow.append(Spacer(1, 8))

        # References, if any
        if data.references:
            flow.append(Paragraph("<b>References:</b>", header_style))
            for i, ref in enumerate(data.references, start=1):
                flow.append(Paragraph(f"{i}. {self._escape(ref)}", body_style))
            flow.append(Spacer(1, 6))

        # Either structured sections (preferred) or legacy body paragraphs
        if data.sections:
            for idx, sec in enumerate(data.sections, start=1):
                title = self._escape(sec.title).upper()
                content = self._escape(sec.content)
                para_html = f"<b>{idx}. {title}:</b> {content}"
                flow.append(Paragraph(para_html, body_style))
                flow.append(Spacer(1, 4))
        else:
            for i, p in enumerate(data.body_paragraphs, start=1):
                flow.append(Paragraph(f"{i}. {self._escape(p)}", body_style))

        # Point of contact, if any (left-aligned small italic)
        if data.point_of_contact:
            flow.append(Spacer(1, 6))
            flow.append(Paragraph(self._escape(data.point_of_contact), small_italic))

        # Signature block – RIGHT ALIGNED
        flow.append(Spacer(1, 24))
        if data.signature_name:
            flow.append(Paragraph(self._escape(data.signature_name), signature_style))
        if data.signature_block:
            flow.append(Paragraph(self._escape(data.signature_block), signature_style))
        if data.signature_extra:
            flow.append(Paragraph(self._escape(data.signature_extra), signature_style))

        doc.build(flow)

    @staticmethod
    def _escape(text: str) -> str:
        """Escape XML-sensitive chars for ReportLab."""
        if text is None:
            return ""
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
        )
