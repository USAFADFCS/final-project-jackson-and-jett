# GrammarTool.py

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import language_tool_python


@dataclass
class GrammarIssue:
    message: str
    offset: int
    length: int
    error_text: str
    replacements: List[str]
    rule_id: str
    rule_description: str


class GrammarTool:
    """
    Wrapper around LanguageTool for grammar and style checking.

    Uses the public HTTP API (no local Java needed).

    - run(text, max_issues=50, auto_correct=False) -> dict:
        {
          "original_text": str,
          "corrected_text": str,
          "issues": [
            {
              "message": "...",
              "error_text": "...",
              "offset": 10,
              "length": 5,
              "replacements": ["..."],
              "rule_id": "...",
              "rule_description": "..."
            },
            ...
          ]
        }
    """

    name: str = "grammar_check"
    description: str = "Check grammar, style, and punctuation."

    def __init__(self, lang: str = "en-US"):
        """
        Use the LanguageTool public API to avoid Java dependency.
        If the public API class isn't available, fall back to a no-op.
        """
        self.tool: Optional[object] = None

        # Prefer the public API (no Java)
        if hasattr(language_tool_python, "LanguageToolPublicAPI"):
            try:
                self.tool = language_tool_python.LanguageToolPublicAPI(lang)
                return
            except Exception as e:
                print(f"⚠️ Failed to initialize LanguageToolPublicAPI: {e}")

        # Fallback: try local LanguageTool (requires Java >= 17)
        try:
            self.tool = language_tool_python.LanguageTool(lang)
        except Exception as e:
            print(
                "⚠️ Failed to initialize LanguageTool (local server). "
                "Grammar checks will be disabled.\n"
                f"   Details: {e}"
            )
            self.tool = None

    def run(
        self,
        text: str,
        max_issues: int = 50,
        auto_correct: bool = False,
    ) -> Dict[str, Any]:
        """
        If the tool is unavailable (e.g., Java missing and PublicAPI failed),
        returns the original text and no issues.
        """
        if self.tool is None:
            # No-op behavior
            return {
                "original_text": text,
                "corrected_text": text,
                "issues": [],
            }

        matches = self.tool.check(text)
        issues: List[GrammarIssue] = []

        for m in matches[:max_issues]:
            issues.append(
                GrammarIssue(
                    message=m.message,
                    offset=m.offset,
                    length=m.errorLength,
                    error_text=text[m.offset : m.offset + m.errorLength],
                    replacements=m.replacements,
                    rule_id=getattr(m, "ruleId", ""),
                    rule_description=getattr(m, "ruleDescription", ""),
                )
            )

        corrected_text: Optional[str] = text
        if auto_correct:
            corrected_text = self.tool.correct(text)

        return {
            "original_text": text,
            "corrected_text": corrected_text,
            "issues": [
                {
                    "message": iss.message,
                    "offset": iss.offset,
                    "length": iss.length,
                    "error_text": iss.error_text,
                    "replacements": iss.replacements,
                    "rule_id": iss.rule_id,
                    "rule_description": iss.rule_description,
                }
                for iss in issues
            ],
        }
