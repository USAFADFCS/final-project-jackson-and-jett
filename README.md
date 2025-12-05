🇺🇸 USAF Document Generator
Automated MFR & OPORD Writer with RAG, Spell Checking, Grammar Tools, and PDF Output

This project provides a fast, reliable way to generate USAF-style Memorandums for Record (MFRs) and 5-paragraph OPERATION ORDERS (OPORDs) using:

OpenAI models (via provided OpenAIAdapter)

Retrieval-Augmented Generation (RAG) from real MFRs/OPORDs

Automatic spell check + grammar correction

Signature block prompting

Professional PDF output using USAF formatting conventions

It was developed to support USAFA cadets, young airmen, and junior officers who are expected to write official documents but often lack clear templates, consistent examples, or time to polish formatting.

📌 Why This Project Exists

Cadets and junior officers are frequently required to produce MFRs and OPORDs, yet:

The correct USAF formatting is not consistently taught,

Templates often vary by unit,

Examples can be outdated or buried in SharePoint drives,

And new writers spend unnecessary time guessing the “right” structure.

This tool solves that by:

Giving users clear, consistent, professional-looking documents,

Enforcing USAF writing style through RAG-powered examples,

Eliminating simple errors with spell & grammar checks,

And outputting ready-to-send PDF files.

The goal is to reduce administrative friction and help cadets/officers focus on mission execution, not formatting.

✨ Features
✔️ MFR Generator

Creates properly structured Memorandums for Record with standard USAF sections such as:

PURPOSE

BACKGROUND

ACTION

CLARIFICATIONS

CONCLUSION

CONTACT

Includes spell check, grammar correction, and signature block automation.

✔️ 5-Paragraph OPORD Generator

Produces OPERATION ORDERS using USAF/DoD-standard format:

Situation

Mission

Execution

Sustainment

Command & Signal

RAG ensures the structure closely resembles real OPORDs (like the NCLS OPORD you provided).

✔️ RAG (Retrieval-Augmented Generation)

Pulls structure and tone from real examples stored in rag_index/index.json, such as:

Bed Rest SOP MFR

NCLS ’24 OPORD

Any additional MFR/OPORD PDFs or text you add

Purpose:
Maintain consistent USAF writing style and prevent hallucinations.

✔️ Spell Check Tool

Corrects spelling errors in each MFR section using pyspellchecker.

✔️ Grammar Tool (no Java needed)

Runs grammar/style correction through LanguageTool’s public API, avoiding Java installation issues.

✔️ Signature Block Prompt

Users are asked for:

Full name

Rank/Service

Duty title

The tool generates a right-aligned USAF signature block automatically.

✔️ USAF-style PDF Output

PDFs are produced using reportlab, ensuring:

Consistent formatting

Professional look

Standardized structure

PDF is preferred because it's the format most commonly used in official USAF communication.

🧱 Architecture Overview
flowchart TD

A[User Input CLI] --> B{Detect Document Type}
B -->|Contains 'opord'| C[LLM + RAG OPORD Builder]
B -->|Default| D[LLM + RAG MFR Builder]

D --> E[Spell Check Tool]
E --> F[Grammar Tool]
F --> G[Signature Prompt]

C --> H[OPORDPdfTool]
G --> I[MFRPdfTool]

H --> J[PDF Output]
I --> J[PDF Output]

🔍 How RAG Works

build_rag_index.py loads PDFs and text examples.

Documents are split into text chunks.

Each chunk is embedded with text-embedding-3-small.

At runtime, your query is embedded and compared to the corpus.

The top-matching MFR or OPORD chunks are prepended to the model prompt.

This ensures the model always produces:

Correct structure

Appropriate tone

No hallucinated formats

Realistic USAF-style writing

RAG is the backbone of the project’s consistency.

🛠 Technologies Used
Component	Purpose
Python 3.11	Application runtime
OpenAIAdapter (fairlib)	Provided by instructor for standard LLM interface
OpenAI GPT-4.1-nano	Default text generation model
text-embedding-3-small	RAG embeddings
pypdf	Extracts text from real PDFs
reportlab	PDF generation (MFR & OPORD)
pyspellchecker	Spelling correction
language-tool-python	Grammar correction without Java
dotenv	Secure API key loading
🔧 Installation
1. Clone the repository
git clone <repo-url>
cd <repo-folder>

2. Create environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. Install dependencies
pip install -r requirements.txt

4. Add your .env

Create .env:

OPENAI_API_KEY=sk-xxxx

▶️ Usage
Run the main tool
python docuwrite.py

Example commands
Create an MFR about squadron dogs for morale and save it to outputs/dogs.pdf

Draft an OPORD for a 5k fun run; save as outputs/funrun.pdf


The program will:

Detect MFR or OPORD

Retrieve relevant examples using RAG

Run spell/grammar checks (optional)

Prompt for signature info (MFR only)

Output a USAF-ready PDF

👤 Target Audience

This tool is built specifically for:

USAFA Cadets

Young Airmen & Junior Officers

Cadre needing quick document generation

Anyone who hasn’t gone through the formal “schoolhouse” training yet

It ensures new writers can still produce correct, professional, mission-ready documents.

🚀 Roadmap / Future Work

Add DOCX export option

Add AFI citation/support tool

Add Batch OPORD generation for exercises

Build GUI version for Windows users

Add live collaboration / shareable templates