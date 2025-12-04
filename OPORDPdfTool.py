# OPORDPdfTool.py

from dataclasses import dataclass
from typing import Dict, Any
from datetime import datetime
import os

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


@dataclass
class OPORDInput:
    title: str = "OPERATION ORDER"
    situation: str = ""
    mission: str = ""
    execution: str = ""
    sustainment: str = ""
    command_and_signal: str = ""
    date: str = ""
    output_path: str = "OPORD.pdf"


class OPORDPdfTool:
    """Generate a simple OPORD PDF with 5-paragraph format."""

    name: str = "opord_pdf"
    description: str = "Generate an OPORD PDF from structured inputs."

    schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "situation": {"type": "string"},
            "mission": {"type": "string"},
            "execution": {"type": "string"},
            "sustainment": {"type": "string"},
            "command_and_signal": {"type": "string"},
            "date": {"type": "string"},
            "output_path": {"type": "string"},
        },
        "required": [
            "title",
            "situation",
            "mission",
            "execution",
            "sustainment",
            "command_and_signal",
            "output_path",
        ],
    }

    def run(self, **kwargs) -> Dict[str, Any]:
        data = OPORDInput(
            title=kwargs.get("title", "OPERATION ORDER"),
            situation=kwargs.get("situation", ""),
            mission=kwargs.get("mission", ""),
            execution=kwargs.get("execution", ""),
            sustainment=kwargs.get("sustainment", ""),
            command_and_signal=kwargs.get("command_and_signal", ""),
            date=kwargs.get("date") or datetime.now().strftime("%d %b %Y"),
            output_path=kwargs.get("output_path", "OPORD.pdf"),
        )

        os.makedirs(os.path.dirname(data.output_path) or ".", exist_ok=True)
        self._build_pdf(data)
        return {"ok": True, "path": data.output_path}

    def _build_pdf(self, data: OPORDInput):
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
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            alignment=TA_LEFT,
            fontName="Times-Roman",
            fontSize=11,
            leading=16,
            spaceAfter=8,
        )

        flow = []
        flow.append(Paragraph(self._escape(data.title), title_style))
        flow.append(Spacer(1, 6))
        flow.append(Paragraph(f"DATE: {self._escape(data.date)}", body_style))
        flow.append(Spacer(1, 8))

        def para(num: str, heading: str, text: str):
            if not text:
                return
            flow.append(
                Paragraph(
                    f"<b>{num}. {heading}.</b> {self._escape(text)}",
                    body_style,
                )
            )

        para("1", "Situation", data.situation)
        para("2", "Mission", data.mission)
        para("3", "Execution", data.execution)
        para("4", "Sustainment", data.sustainment)
        para("5", "Command and Signal", data.command_and_signal)

        doc.build(flow)

    @staticmethod
    def _escape(text: str) -> str:
        if text is None:
            return ""
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
        )
