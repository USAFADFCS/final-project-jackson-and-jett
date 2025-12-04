# docuwrite.py
#
# Interactive CLI for generating MFRs and OPORDs with:
# - RAG (retrieval-augmented generation) from rag_index/index.json
# - OpenAIAdapter (fairlib) for LLM calls
# - Spell check + grammar check (optional auto-correct) for MFRs
# - Secondary prompt for signature block
#
# Usage examples:
#   "Create an MFR about squadron dogs for morale and save it to outputs/dogs_mfr.pdf"
#   "Draft an opord for a 5k fun run and save as outputs/funrun_opord.pdf"

import os
import re
import math
import asyncio
import json

from dotenv import load_dotenv
load_dotenv()  # loads OPENAI_API_KEY from .env

from openai import OpenAI  # for embeddings (RAG)

from fairlib.core.message import Message
from fairlib import OpenAIAdapter  # your adapter

from MFRPdfTool import MFRPdfTool
from MFRPromptTool import MFRPromptTool
from OPORDPdfTool import OPORDPdfTool
from SpellCheckTool import SpellCheckTool
from GrammarTool import GrammarTool


# ------------------ Globals ------------------

RAG_INDEX = []  # loaded from rag_index/index.json


# ------------------ LLM Setup ------------------

def build_llm() -> OpenAIAdapter:
    """Build the OpenAIAdapter using OPENAI_API_KEY from .env."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not set. Put it in a .env file, e.g.\n"
            "OPENAI_API_KEY=sk-xxxxx"
        )

    return OpenAIAdapter(
        api_key=api_key,
        model_name="gpt-4.1-nano"
    )


# ------------------ RAG Helpers ------------------

def load_rag_index():
    """Load precomputed RAG index from rag_index/index.json if present."""
    global RAG_INDEX
    path = "rag_index/index.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            RAG_INDEX = json.load(f)
        print(f"📚 RAG index loaded with {len(RAG_INDEX)} chunks.")
    else:
        RAG_INDEX = []
        print("⚠️ No RAG index found (rag_index/index.json). Running without extra context.")


def cosine_similarity(a, b):
    """Simple cosine similarity between two embedding vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def embed_query(query: str):
    """Get an embedding for the query text using OpenAI embeddings."""
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=[query]
    )
    return resp.data[0].embedding


def retrieve_context(query: str, doc_type: str, k: int = 4) -> str:
    """
    Retrieve top-k RAG chunks for a given doc_type ('mfr' or 'opord').

    Returns a concatenated text block with --- separators, or "" if none.
    """
    if not RAG_INDEX:
        return ""

    q_emb = embed_query(query)
    scored = []
    for entry in RAG_INDEX:
        if entry.get("doc_type") != doc_type:
            continue
        emb = entry.get("embedding")
        if not emb:
            continue
        sim = cosine_similarity(q_emb, emb)
        scored.append((sim, entry["text"]))

    if not scored:
        return ""

    scored.sort(key=lambda t: t[0], reverse=True)
    top_texts = [t for _, t in scored[:k]]
    return "\n\n---\n\n".join(top_texts)


# ------------------ Signature Prompt Helper ------------------

def prompt_signature_block():
    """
    Ask the user (secondary prompt) for name, rank, and duty title
    to build a signature block. Returns (signature_name, signature_block)
    or (None, None) if the user skips.
    """
    print("\n✍️  Do you want to add a signature block to this MFR?")
    choice = input("Add signature block? [y/N]: ").strip().lower()
    if choice not in ("y", "yes"):
        return None, None

    print("\nPlease provide signature information (press Enter to skip any field):")
    name = input(" Full name (e.g., John Q. Carter): ").strip()
    rank = input(" Rank & service (e.g., C/Lt Col, USAF): ").strip()
    title = input(" Duty title (e.g., Group D&C Officer): ").strip()

    if not name and not rank and not title:
        return None, None

    # Name is typically uppercase in signature
    signature_name = name.upper() if name else None

    # Build the block for rank+title on the line(s) below
    lines = []
    if rank:
        lines.append(rank)
    if title:
        lines.append(title)
    signature_block = "\n".join(lines) if lines else None

    return signature_name, signature_block


# ------------------ LLM JSON Builders ------------------

async def llm_to_mfr_json(llm: OpenAIAdapter, user_prompt: str) -> dict:
    """
    Ask the LLM for structured MFR JSON:
    {
      "subject": "...",
      "sections": [
        {"title": "PURPOSE", "content": "..."},
        {"title": "BACKGROUND", "content": "..."},
        ...
      ]
    }
    """
    rag_context = retrieve_context(user_prompt, doc_type="mfr")
    if rag_context:
        context_block = (
            "Here are relevant MFR examples and references (including real USAF MFRs). "
            "Use them to match tone, section structure, and numbering "
            "like PURPOSE, BACKGROUND, ACTION, CLARIFICATIONS, CONCLUSION, CONTACT. "
            "Do NOT copy them verbatim; treat them as guidance only.\n\n"
            f"{rag_context}"
        )
    else:
        context_block = "No extra MFR reference context is available."

    system = (
        "You convert natural-language requests into U.S. Air Force-style Memorandums for Record (MFRs). "
        "Follow the 1-6 section pattern commonly used in the references, e.g.: "
        "PURPOSE, BACKGROUND, ACTION, CLARIFICATIONS, CONCLUSION, CONTACT. "
        "Respond ONLY with minified JSON using the exact structure:\n"
        "{"
        "\"subject\":\"...\","
        "\"sections\":["
        "{\"title\":\"PURPOSE\",\"content\":\"...\"},"
        "{\"title\":\"BACKGROUND\",\"content\":\"...\"}"
        "]"
        "} "
        "You may choose 4–8 sections, but titles should be all caps like the examples. "
        "No backticks, no extra text."
    )

    msgs = [
        Message(role="system", content=system),
        Message(role="system", content=context_block),
        Message(role="user", content=f"Draft an MFR from this request: {user_prompt}"),
    ]

    if hasattr(llm, "ainvoke"):
        resp = await llm.ainvoke(msgs)
    else:
        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(None, llm.invoke, msgs)

    text = resp.content or str(resp)
    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last < first:
        raise ValueError(f"LLM did not return JSON: {text!r}")

    data = json.loads(text[first:last + 1])
    if "subject" not in data or "sections" not in data:
        raise ValueError("JSON for MFR missing required keys 'subject' and/or 'sections'.")
    if not isinstance(data["sections"], list) or not data["sections"]:
        raise ValueError("JSON for MFR must have a non-empty 'sections' list.")
    return data


async def llm_to_opord_json(llm: OpenAIAdapter, user_prompt: str) -> dict:
    """
    Ask the LLM for structured OPORD JSON:
    {
      "title": "...",
      "situation": "...",
      "mission": "...",
      "execution": "...",
      "sustainment": "...",
      "command_and_signal": "..."
    }
    """
    rag_context = retrieve_context(user_prompt, doc_type="opord")
    if rag_context:
        context_block = (
            "Here are relevant OPORD examples and references in 5-paragraph format. "
            "Use them to match structure, phrasing, and level of detail. "
            "Do NOT copy them verbatim; treat them as guidance only.\n\n"
            f"{rag_context}"
        )
    else:
        context_block = "No extra OPORD reference context is available."

    system = (
        "You convert natural-language requests into 5-paragraph OPERATION ORDERS (OPORDs). "
        "Use headings: Situation, Mission, Execution, Sustainment, Command and Signal. "
        "Respond ONLY with minified JSON using the exact structure:\n"
        "{"
        "\"title\":\"OPERATION ORDER ...\","
        "\"situation\":\"...\","
        "\"mission\":\"...\","
        "\"execution\":\"...\","
        "\"sustainment\":\"...\","
        "\"command_and_signal\":\"...\""
        "} "
        "No backticks, no extra text."
    )

    msgs = [
        Message(role="system", content=system),
        Message(role="system", content=context_block),
        Message(role="user", content=f"Draft an OPORD from this request: {user_prompt}"),
    ]

    if hasattr(llm, "ainvoke"):
        resp = await llm.ainvoke(msgs)
    else:
        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(None, llm.invoke, msgs)

    text = resp.content or str(resp)
    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last < first:
        raise ValueError(f"LLM did not return JSON: {text!r}")

    data = json.loads(text[first:last + 1])
    required = [
        "title",
        "situation",
        "mission",
        "execution",
        "sustainment",
        "command_and_signal",
    ]
    if any(k not in data for k in required):
        raise ValueError("JSON for OPORD missing required keys.")
    return data


# ------------------ Main Loop ------------------

async def main():
    print("🔧 Initializing MFR/OPORD Document Generator with RAG...")

    load_rag_index()

    try:
        llm = build_llm()
        print("✅ OpenAIAdapter initialized.")
    except Exception as e:
        print(f"❌ Could not initialize OpenAIAdapter: {e}")
        print("   Falling back to heuristic MFRPromptTool only for MFRs.")
        llm = None

    mfr_pdf = MFRPdfTool()
    opord_pdf = OPORDPdfTool()
    mfr_prompt_tool = MFRPromptTool()

    # Spell & grammar tools for quality checks on MFR sections
    spell_tool = SpellCheckTool()
    grammar_tool = GrammarTool()

    print("🎓 Ready to create MFRs or OPORDs.")
    print(" • Mention 'opord' or 'operation order' to trigger OPORD mode.")
    print("Type 'exit' or 'quit' to end.\n")

    while True:
        try:
            user_input = input("👤 You: ").strip()
            if user_input.lower() in ("exit", "quit"):
                print("🤖 Goodbye! 👋")
                break
            if not user_input:
                continue

            # Detect explicit output PDF path
            pdfs = re.findall(r"(\S+\.pdf)", user_input, flags=re.IGNORECASE)
            output_path = pdfs[-1] if pdfs else "outputs/doc.pdf"
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

            # Detect type: OPORD vs MFR
            lower = user_input.lower()
            if "opord" in lower or "operation order" in lower:
                mode = "opord"
            else:
                mode = "mfr"

            print(f"🧾 Detected mode: {mode.upper()}")

            used_fallback = False

            if llm is not None:
                try:
                    if mode == "mfr":
                        # 1) Build structured MFR content via LLM + RAG
                        data = await llm_to_mfr_json(llm, user_input)

                        # 1.5) Optional spell + grammar checks on each section
                        print("\n🧹 Quality checks for this MFR:")
                        do_spell = input("  Run spell check (auto-correct)? [y/N]: ").strip().lower() in ("y", "yes")
                        do_grammar = input("  Run grammar check (auto-correct)? [y/N]: ").strip().lower() in ("y", "yes")

                        if do_spell or do_grammar:
                            cleaned_sections = []
                            for sec in data["sections"]:
                                text = sec["content"]
                                if do_spell:
                                    spell_result = spell_tool.run(text, auto_correct=True)
                                    text = spell_result["corrected_text"]
                                if do_grammar:
                                    gram_result = grammar_tool.run(text, auto_correct=True)
                                    text = gram_result["corrected_text"]

                                cleaned_sections.append(
                                    {
                                        "title": sec["title"],
                                        "content": text,
                                    }
                                )
                            data["sections"] = cleaned_sections

                        # 2) Secondary prompt for signature info
                        signature_name, signature_block = prompt_signature_block()

                        # 3) Generate PDF
                        result = mfr_pdf.run(
                            subject=data["subject"],
                            sections=data["sections"],
                            signature_name=signature_name,
                            signature_block=signature_block,
                            output_path=output_path,
                        )
                    else:
                        # OPORD path
                        data = await llm_to_opord_json(llm, user_input)
                        result = opord_pdf.run(
                            title=data["title"],
                            situation=data["situation"],
                            mission=data["mission"],
                            execution=data["execution"],
                            sustainment=data["sustainment"],
                            command_and_signal=data["command_and_signal"],
                            output_path=output_path,
                        )

                    if result.get("ok"):
                        print(f"✅ PDF written to: {result['path']}")
                    else:
                        print(f"❌ PDF generation failed: {result}")
                        used_fallback = (mode == "mfr")  # only have MFR fallback
                except Exception as e:
                    print(f"❌ LLM {mode.upper()} JSON pipeline failed: {e}")
                    used_fallback = (mode == "mfr")
            else:
                used_fallback = (mode == "mfr")

            # Fallback only exists for MFR
            if used_fallback and mode == "mfr":
                print("↪️ Using fallback MFRPromptTool...")
                result = mfr_prompt_tool.run(prompt=user_input, output_path=output_path)
                if result.get("ok"):
                    print(f"✅ PDF written to: {result['path']}")
                else:
                    print(f"❌ Fallback failed: {result}")
            elif used_fallback and mode == "opord":
                print("⚠️ No OPORD fallback implemented. Please fix the LLM/JSON issue above.")

        except KeyboardInterrupt:
            print("\n🤖 Session ended by user.")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
