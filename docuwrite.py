# docuwrite.py

import os
import re
import asyncio
import json
from fairlib.core.message import Message
# (Optional) keep auth clean and avoid stale tokens at import time
os.environ.pop("HUGGINGFACE_HUB_TOKEN", None)
os.environ.pop("HUGGINGFACEHUB_API_TOKEN", None)
os.environ.pop("HF_TOKEN", None)

from fairlib import (
    ToolRegistry,
    ToolExecutor,
    WorkingMemory,
    SimpleAgent,
    RoleDefinition,
    HuggingFaceAdapter,
    SimpleReActPlanner,
)

from MFRPdfTool import MFRPdfTool  # <- lives next to this file (not inside fairlib)  :contentReference[oaicite:3]{index=3}
from MFRPromptTool import MFRPromptTool

async def main():
    """
    Main entry point for the MFR agent:
    sets up model, tools, planner, role, and interactive loop.
    """
    print("🔧 Initializing the MFR Document Agent...")

    # === (a) Brain: Language Model ===
    # Use your requested model
    #llm = HuggingFaceAdapter("HuggingFaceTB/SmolLM3-3B")  # :contentReference[oaicite:4]{index=4}
    llm = HuggingFaceAdapter("TinyLlama/TinyLlama-1.1B-Chat-v1.0") 
    # After llm = HuggingFaceAdapter("HuggingFaceTB/SmolLM3-3B")
    try:
        llm.set_generation_params(
            temperature=0.0,
            do_sample=False,
            max_new_tokens=200,
            stop_sequences=["\nThought:", "\nFinal Answer", "\nTool Name:", "\nTool Input:", "\n# "]
        )
    except Exception:
        pass



    # === (b) Toolbelt: Register tools ===
    tool_registry = ToolRegistry()

    # Custom PDF tool
    mfr_pdf = MFRPdfTool()
    mfr_prompt = MFRPromptTool()
    tool_registry.register_tool(mfr_pdf)  # <- previously referenced but not defined  :contentReference[oaicite:5]{index=5}
    tool_registry.register_tool(mfr_prompt)
    print(f"✅ Registered tools: {[t.name for t in tool_registry.get_all_tools().values()]}")

    # === (c) Hands: Tool Executor ===
    executor = ToolExecutor(tool_registry)

    # === (d) Memory ===
    memory = WorkingMemory()

    # === (e) Mind: Reasoning Engine ===
    planner = SimpleReActPlanner(llm, tool_registry)

    # === (f) Role: Military official documents expert ===
    planner.prompt_builder.role_definition = RoleDefinition(
        "You are an advanced expert in military official documentation whose duty is to draft, review, "
        "and finalize Memorandums for Record (MFRs) for military officials and cadets.\n"
        "You must reason step-by-step internally and use tools to act. If a user's request requires "
        "multiple steps or tools, break the process into sequential actions.\n"
        "CRITICAL FORMAT RULES:\n"
        "• When you need to use a tool, respond with EXACTLY two lines and nothing else:\n"
        "  Action: <tool_name>\n"
        "  Action Input: <valid minified JSON on one line>\n"
        "• Do NOT include any other text (no headings, no 'Thought', no 'Tool Name:', no 'Tool Input:').\n"
        "• Allowed tools: mfr_pdf, mfr_prompt\n"
        "• For mfr_pdf JSON, include: subject (string), body_paragraphs (array of strings), output_path (string). "
        "Optional: date, from_line, to_line, suspense, references (array), point_of_contact, "
        "signature_name, signature_block, signature_extra.\n"
        "EXAMPLE:\n"
        "Action: mfr_pdf\n"
        "Action Input: {\"subject\":\"Parade Coordination\",\"body_paragraphs\":[\"Purpose...\",\"Execution...\",\"Conclusion...\"],\"output_path\":\"outputs/parade_mfr.pdf\"}\n"
        "Use professional U.S. military correspondence style — clear, concise, mission-appropriate."
    )



    # === (g) Assemble the Agent ===
    agent = SimpleAgent(
        llm=llm,
        planner=planner,
        tool_executor=executor,
        memory=memory,
        max_steps=10,
    )

    print("🎓 Agent is ready for MFR drafting.")
    print("💬 Try natural prompts, e.g.:")
    print("   • 'Draft an MFR for parade coordination and export to outputs/parade_mfr.pdf'")
    print("   • 'Create an MFR with subject \"Training Brief\" with 3 bullet paragraphs and save it to outputs/brief.pdf'")
    print("\nType 'exit' or 'quit' to end the session.")
    # === (h) Interaction Loop (mirrors the demo) ===  :contentReference[oaicite:6]{index=6}
    while True:
        try:
            user_input = input("👤 You: ")
            if user_input.lower() in ("exit", "quit"):
                print("🤖 Agent: Goodbye! 👋")
                break

            agent_response = await agent.arun(user_input)
            tool_block = None
            if isinstance(agent_response, str):
                tool_block = re.search(
                    r"(?is)^\s*Action:\s*(\w+)\s*[\r\n]+Action Input:\s*(\{.*\})\s*$",
                    agent_response.strip()
                )

            if not tool_block:
                print("--- Model returned prose or malformed tool call; running JSON→PDF pipeline ---")

                # 🧠 Robustly detect any .pdf path mentioned by user (e.g. "save as a PDF to outputs/cheese.pdf")
                pdfs = re.findall(r"(\S+\.pdf)", user_input, flags=re.IGNORECASE)
                output_path = pdfs[-1] if pdfs else "outputs/mfr.pdf"
                os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

                try:
                    # 1) ask LLM for clean JSON
                    data = await llm_to_mfr_json(llm, user_input)
                    # 2) call mfr_pdf directly
                    res = tool_registry.get_tool("mfr_pdf").run(
                        subject=data["subject"],
                        body_paragraphs=data["body_paragraphs"],
                        output_path=output_path
                    )
                    if res.get("ok"):
                        print(f"✅ PDF written to: {res['path']}")
                    else:
                        print(f"❌ PDF generation failed: {res}")
                except Exception as e:
                    print(f"❌ JSON→PDF pipeline failed: {e}\nFalling back to MFRPromptTool.")
                    # last resort: prompt-derived template
                    res = tool_registry.get_tool("mfr_prompt").run(
                        prompt=user_input, output_path=output_path
                    )
                    if res.get("ok"):
                        print(f"✅ PDF written to: {res['path']}")
                    else:
                        print(f"❌ Fallback failed: {res}")
                continue



        except KeyboardInterrupt:
            print("\n🤖 Agent: Session ended by user.")
            break
        except Exception as e:
            print(f"❌ Agent error: {e}")

async def llm_to_mfr_json(llm, user_prompt: str) -> dict:
    """Ask the LLM for JSON-only MFR content; return dict with subject/body_paragraphs."""
    system = (
        "Return ONLY compact JSON with keys: subject (string), body_paragraphs (array of 3–6 strings). "
        "No prose. No backticks. No explanations."
    )

    msgs = [
        Message(role="system", content=system),
        Message(role="user", content=f"Draft an MFR from this request: {user_prompt}"),
    ]

    # Prefer async if available; otherwise use sync in a thread.
    if hasattr(llm, "acomplete"):
        raw = await llm.acomplete(msgs)
    else:
        import asyncio
        raw = await asyncio.to_thread(llm.complete, msgs)

    text = raw if isinstance(raw, str) else str(raw)
    first_brace = text.find("{")
    last_brace  = text.rfind("}")
    if first_brace == -1 or last_brace == -1 or last_brace < first_brace:
        raise ValueError("LLM did not return JSON")

    import json
    data = json.loads(text[first_brace:last_brace+1])
    if not isinstance(data, dict): raise ValueError("JSON not an object")
    if "subject" not in data or "body_paragraphs" not in data:
        raise ValueError("JSON missing required keys")
    if not isinstance(data["body_paragraphs"], list) or not data["body_paragraphs"]:
        raise ValueError("body_paragraphs must be a non-empty list")
    return data


# Entrypoint (required so `python docuwrite.py` actually runs)  :contentReference[oaicite:7]{index=7}
if __name__ == "__main__":
    asyncio.run(main())

