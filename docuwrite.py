# docuwrite.py

import os
import asyncio

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
    llm = HuggingFaceAdapter("HuggingFaceTB/SmolLM3-3B")  # :contentReference[oaicite:4]{index=4}
    # After llm = HuggingFaceAdapter("HuggingFaceTB/SmolLM3-3B")
    try:
        llm.set_generation_params(
            temperature=0.2,      # less creative, more literal
            do_sample=False,      # greedy decoding helps follow format
            max_new_tokens=512
        )
    except Exception:
        pass  # safe if your adapter doesn't expose this


    # === (b) Toolbelt: Register tools ===
    tool_registry = ToolRegistry()

    # Custom PDF tool
    mfr_pdf_tool = MFRPdfTool()
    tool_registry.register_tool(mfr_pdf_tool)  # <- previously referenced but not defined  :contentReference[oaicite:5]{index=5}
    tool_registry.register_tool(MFRPromptTool())
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
        "and finalize formal documents such as Memorandums for Record (MFRs) for military officials and cadets.\n"
        "You must reason step-by-step internally and then use tools to act. "
        "If a user's request requires multiple steps or tools, you must break the process into sequential actions.\n"
        "CRITICAL FORMAT RULES:\n"
        "• When you need to use a tool, you MUST respond ONLY with:\n"
        "  Action: <tool_name>\n"
        "  Action Input: {JSON}\n"
        "• Do NOT include any other text, explanations, or <think> content in the same message.\n"
        "• Use the tool name exactly: mfr_pdf\n"
        "• JSON must include: subject (string), body_paragraphs (array of strings), output_path (string). "
        "Optional: date, from_line, to_line, suspense, references (array), point_of_contact, signature_name, signature_block, signature_extra.\n"
        "EXAMPLE (copy this structure):\n"
        "Action: mfr_pdf\n"
        "Action Input: {\"subject\":\"Parade Coordination\",\"body_paragraphs\":[\"Purpose...\",\"Execution...\",\"Conclusion...\"],\"output_path\":\"outputs/parade_mfr.pdf\"}\n"
        "Your writing style must reflect professional U.S. military correspondence — clear, concise, and mission-appropriate."
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
            print(f"🤖 Agent: {agent_response}")

        except KeyboardInterrupt:
            print("\n🤖 Agent: Session ended by user.")
            break
        except Exception as e:
            print(f"❌ Agent error: {e}")

# Entrypoint (required so `python docuwrite.py` actually runs)  :contentReference[oaicite:7]{index=7}
if __name__ == "__main__":
    asyncio.run(main())
