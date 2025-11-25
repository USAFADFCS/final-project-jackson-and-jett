# docuwrite.py
#
# Clean, robust MFR generator using your uploaded OpenAIAdapter.
# Uses LLM to produce JSON, then MFRPdfTool to render PDF.
# Falls back to MFRPromptTool if JSON fails.

import os
import re
import asyncio
import json

# Fairlib imports
from fairlib.core.message import Message
from fairlib import OpenAIAdapter   # <-- YOUR uploaded adapter

# Your custom tools
from MFRPdfTool import MFRPdfTool
from MFRPromptTool import MFRPromptTool

# Clean environment variables for HuggingFace
os.environ.pop("HUGGINGFACE_HUB_TOKEN", None)
os.environ.pop("HUGGINGFACEHUB_API_TOKEN", None)
os.environ.pop("HF_TOKEN", None)


# -----------------------------------------------------------
# Build LLM using YOUR OpenAIAdapter (uploaded file)
# -----------------------------------------------------------
def build_llm() -> OpenAIAdapter:
    from dotenv import load_dotenv
    load_dotenv()   # <-- load .env variables

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not found in environment or .env file. "
            "Please create a .env file with OPENAI_API_KEY=your_key_here"
        )

    llm = OpenAIAdapter(
        api_key=api_key,
        model_name="gpt-4.1-nano"
    )
    return llm


# -----------------------------------------------------------
# Ask LLM to return ONLY JSON for MFR
# -----------------------------------------------------------
async def llm_to_mfr_json(llm: OpenAIAdapter, user_prompt: str) -> dict:
    system = (
        "You convert natural-language requests into Memorandums for Record (MFRs). "
        "Respond ONLY with minified JSON using the exact structure:\n"
        "{"
        "\"subject\":\"...\","
        "\"body_paragraphs\":[\"para1\",\"para2\",\"para3\"]"
        "}"
        "No backticks, no extra text."
    )

    msgs = [
        Message(role="system", content=system),
        Message(role="user", content=f"Draft an MFR from this request: {user_prompt}")
    ]

    # Use async if available, else sync
    if hasattr(llm, "ainvoke"):
        resp = await llm.ainvoke(msgs)
    else:
        loop = asyncio.get_running_loop()
        resp = await loop.run_in_executor(None, llm.invoke, msgs)

    text = resp.content or str(resp)

    # Extract JSON block
    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last < first:
        raise ValueError(f"LLM did not return JSON: {text!r}")

    raw_json = text[first:last+1]
    data = json.loads(raw_json)

    # Validate
    if "subject" not in data or "body_paragraphs" not in data:
        raise ValueError("JSON missing required keys.")

    if not isinstance(data["subject"], str):
        raise ValueError("'subject' must be a string.")

    if not isinstance(data["body_paragraphs"], list):
        raise ValueError("'body_paragraphs' must be a list.")

    return data


# -----------------------------------------------------------
# Main interaction loop
# -----------------------------------------------------------
async def main():
    print("🔧 Initializing MFR Document Generator (Clean Rewrite)...")

    # Build LLM
    try:
        llm = build_llm()
        print("✅ OpenAIAdapter initialized.")
    except Exception as e:
        print(f"❌ Could not initialize OpenAIAdapter: {e}")
        print("   Falling back to MFRPromptTool only.")
        llm = None

    pdf_tool = MFRPdfTool()
    prompt_tool = MFRPromptTool()

    print("🎓 Ready to create MFRs.")
    print("Type 'exit' or 'quit' to end.\n")

    while True:
        try:
            user_input = input("👤 You: ").strip()

            if user_input.lower() in ("exit", "quit"):
                print("🤖 Goodbye! 👋")
                break

            if not user_input:
                continue

            # Detect PDF output path
            pdfs = re.findall(r"(\S+\.pdf)", user_input)
            output_path = pdfs[-1] if pdfs else "outputs/mfr.pdf"
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

            # Try LLM → JSON → PDF first
            used_fallback = False
            if llm is not None:
                try:
                    data = await llm_to_mfr_json(llm, user_input)
                    result = pdf_tool.run(
                        subject=data["subject"],
                        body_paragraphs=data["body_paragraphs"],
                        output_path=output_path
                    )
                    if result.get("ok"):
                        print(f"✅ PDF written to: {result['path']}")
                    else:
                        used_fallback = True
                except Exception as e:
                    print(f"❌ JSON pipeline failed: {e}")
                    used_fallback = True
            else:
                used_fallback = True

            # If LLM fails → fallback
            if used_fallback:
                print("↪️ Using fallback MFRPromptTool...")
                result = prompt_tool.run(prompt=user_input, output_path=output_path)
                if result.get("ok"):
                    print(f"✅ PDF written to: {result['path']}")
                else:
                    print(f"❌ Fallback failed: {result}")

        except KeyboardInterrupt:
            print("\n🤖 Session ended by user.")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
