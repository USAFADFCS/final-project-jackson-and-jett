# MFRPromptTool.py
from typing import Dict, Any, List, Optional
import os
from datetime import datetime

from MFRPdfTool import MFRPdfTool

class MFRPromptTool:
    """
    Turn a natural-language prompt into a simple MFR and save as PDF.
    Uses deterministic heuristics (no LLM inside the tool).
    """

    name: str = "mfr_prompt"
    description: str = "Draft an MFR from a plain-English prompt and save to PDF."

    schema: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string"},
            "output_path": {"type": ["string", "null"]},
            "date": {"type": ["string", "null"]},
            "from_line": {"type": ["string", "null"]},
            "to_line": {"type": ["string", "null"]},
            "suspense": {"type": ["string", "null"]},
            "references": {"type": "array", "items": {"type": "string"}},
            "point_of_contact": {"type": ["string", "null"]},
            "signature_name": {"type": ["string", "null"]},
            "signature_block": {"type": ["string", "null"]},
            "signature_extra": {"type": ["string", "null"]},
        },
        "required": ["prompt"],
    }

    def run(self, **kwargs) -> Dict[str, Any]:
        prompt: str = kwargs.get("prompt", "").strip()
        if not prompt:
            return {"ok": False, "error": "Missing 'prompt'."}

        output_path: Optional[str] = kwargs.get("output_path")
        if not output_path:
            safe_stub = self._slug(prompt)[:40] or "mfr"
            output_path = f"outputs/{safe_stub}.pdf"

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        # Simple derivations
        subject = self._derive_subject(prompt)
        body_paragraphs = self._derive_paragraphs(prompt)

        tool = MFRPdfTool()
        result = tool.run(
            date=kwargs.get("date"),
            from_line=kwargs.get("from_line"),
            to_line=kwargs.get("to_line"),
            subject=subject,
            suspense=kwargs.get("suspense"),
            references=kwargs.get("references", []),
            body_paragraphs=body_paragraphs,
            point_of_contact=kwargs.get("point_of_contact"),
            signature_name=kwargs.get("signature_name"),
            signature_block=kwargs.get("signature_block"),
            signature_extra=kwargs.get("signature_extra"),
            output_path=output_path,
        )
        return result

    # ---------------- helpers ----------------
    def _derive_subject(self, prompt: str) -> str:
        # Very simple subject heuristic
        p = prompt.replace("\n", " ").strip()
        if len(p) > 120:
            p = p[:117] + "..."
        # Normalize common verbs
        p = p.capitalize()
        if not p.endswith("."):
            p += "."
        return f"MFR – {p}"

    def _derive_paragraphs(self, prompt: str) -> List[str]:
        # Deterministic template: overview, rationale, execution, risk/coord, recommendation
        base = prompt.strip()
        return [
            f"This memorandum records the subject matter: {base}",
            "Rationale: This action is intended to improve morale, cohesion, and mission effectiveness while "
            "maintaining standards and compliance with applicable guidance.",
            "Execution: Identify responsible OPR/OCRs, establish a short timeline, and coordinate facilities, "
            "equipment, and funding requirements as necessary.",
            "Risk & Coordination: Mitigate safety, legal, and logistics risks via appropriate reviews and "
            "coordination with stakeholders; document approvals as needed.",
            "Recommendation: Approve the subject initiative and proceed per the execution plan.",
        ]

    def _slug(self, s: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "-" for ch in s).strip("-")
