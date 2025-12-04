# SpellCheckTool.py

from dataclasses import dataclass
from typing import List, Dict, Any
import re

from spellchecker import SpellChecker


@dataclass
class SpellingIssue:
    word: str
    suggestion: str
    index: int  # index in token list


class SpellCheckTool:
    """
    Simple spell checker tool.

    - run(text, auto_correct=False) -> dict with:
        {
          "original_text": str,
          "corrected_text": str,
          "issues": [
            {"word": "...", "suggestion": "...", "index": 5},
            ...
          ]
        }
    """

    name: str = "spell_check"
    description: str = "Check spelling and optionally auto-correct text."

    def __init__(self, language: str = "en"):
        self.spell = SpellChecker(language=language)

    def _tokenize(self, text: str) -> List[str]:
        # Simple whitespace tokenizer that preserves punctuation marks attached
        return re.findall(r"\w+['’]?\w*|[^\w\s]", text, flags=re.UNICODE)

    def _join_tokens(self, tokens: List[str]) -> str:
        # Reconstruct text with simple spacing rules
        out = []
        for i, tok in enumerate(tokens):
            if i == 0:
                out.append(tok)
                continue
            if re.match(r"[.,;:!?)]", tok):
                # punctuation that sticks to previous
                out[-1] = out[-1] + tok
            elif out[-1] == "(":
                # opening paren sticks to next
                out.append(tok)
            else:
                out.append(" " + tok)
        return "".join(out)

    def run(self, text: str, auto_correct: bool = False) -> Dict[str, Any]:
        tokens = self._tokenize(text)
        issues: List[SpellingIssue] = []

        # Work only on alphabetic-like tokens
        for i, tok in enumerate(tokens):
            # skip short, numeric, ALL-CAPS acronyms, etc.
            if len(tok) <= 2 or not re.search(r"[A-Za-z]", tok):
                continue
            if tok.isupper():
                # likely acronym (USAFA, AFI, CWIC, etc.)
                continue

            low = tok.lower()
            if low in self.spell:
                continue

            correction = self.spell.correction(low) or tok
            if correction.lower() == low:
                continue

            issues.append(SpellingIssue(word=tok, suggestion=correction, index=i))

        corrected_tokens = tokens[:]
        if auto_correct:
            for issue in issues:
                corrected_tokens[issue.index] = self._match_case(
                    issue.suggestion, corrected_tokens[issue.index]
                )

        corrected_text = self._join_tokens(corrected_tokens) if auto_correct else text

        return {
            "original_text": text,
            "corrected_text": corrected_text,
            "issues": [
                {
                    "word": iss.word,
                    "suggestion": iss.suggestion,
                    "index": iss.index,
                }
                for iss in issues
            ],
        }

    @staticmethod
    def _match_case(suggestion: str, original: str) -> str:
        if original.istitle():
            return suggestion.title()
        if original.isupper():
            return suggestion.upper()
        if original.islower():
            return suggestion.lower()
        return suggestion
