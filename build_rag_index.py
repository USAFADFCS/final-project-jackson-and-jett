# build_rag_index.py
import os
import json

from dotenv import load_dotenv
from openai import OpenAI

# Optional PDF support – used to ingest your real MFR & OPORD PDFs
try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

load_dotenv()  # loads OPENAI_API_KEY from .env

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def chunk_text(text: str, max_chars: int = 800):
    """Split long text into ~max_chars chunks on line boundaries."""
    lines = text.splitlines()
    chunks, cur, total = [], [], 0
    for line in lines:
        if total + len(line) > max_chars and cur:
            chunks.append("\n".join(cur))
            cur, total = [], 0
        cur.append(line)
        total += len(line)
    if cur:
        chunks.append("\n".join(cur))
    return chunks


def embed_texts(texts):
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    return [d.embedding for d in resp.data]


def extract_pdf_text(pdf_path: str) -> str:
    """Extract raw text from a PDF (if pypdf installed)."""
    if not HAS_PYPDF:
        print(f"⚠️ pypdf not installed; cannot read {pdf_path}. Run `pip install pypdf` if you want this.")
        return ""
    if not os.path.exists(pdf_path):
        print(f"⚠️ PDF not found at: {pdf_path}")
        return ""
    reader = PdfReader(pdf_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def main():
    corpus = []

    # ---------- MFR references ----------
    mfr_text = ""

    # (1) Optional plain-text examples
    if os.path.exists("mfr_examples.txt"):
        with open("mfr_examples.txt", "r", encoding="utf-8") as f:
            mfr_text += f.read() + "\n\n"

    # (2) Your actual Bed Rest SOP MFR PDF
    mfr_pdf_name = "MFR - Bed Rest SOP_CW.pdf"
    if os.path.exists(mfr_pdf_name):
        print(f"📄 Using PDF MFR reference: {mfr_pdf_name}")
        mfr_text += extract_pdf_text(mfr_pdf_name)
    else:
        print(f"⚠️ {mfr_pdf_name} not found; skipping PDF ingestion for MFR references.")

    if mfr_text.strip():
        for chunk in chunk_text(mfr_text):
            corpus.append({
                "doc_type": "mfr",
                "source": "mfr_examples",
                "text": chunk
            })
    else:
        print("⚠️ No MFR reference text found (mfr_examples.txt or MFR - Bed Rest SOP_CW.pdf).")

    # ---------- OPORD references ----------
    opord_text = ""

    # (1) Optional plain-text OPORD examples
    if os.path.exists("opord_examples.txt"):
        with open("opord_examples.txt", "r", encoding="utf-8") as f:
            opord_text += f.read() + "\n\n"
    else:
        print("⚠️ No OPORD reference text file found (opord_examples.txt).")

    # (2) Your NCLS OPORD PDF
    opord_pdf_name = "NCLS '24 OPORD (21-23 Feb 2024).pdf"
    if os.path.exists(opord_pdf_name):
        print(f"📄 Using PDF OPORD reference: {opord_pdf_name}")
        opord_text += extract_pdf_text(opord_pdf_name)
    else:
        print(f"⚠️ {opord_pdf_name} not found; skipping PDF ingestion for OPORD references.")

    if opord_text.strip():
        for chunk in chunk_text(opord_text):
            corpus.append({
                "doc_type": "opord",
                "source": "opord_examples",
                "text": chunk
            })
    else:
        print("⚠️ No OPORD reference text found (opord_examples.txt or NCLS OPORD PDF).")

    # ---------- Save corpus ----------
    if not corpus:
        print("❌ No corpus to embed. Add MFR/OPORD examples first.")
        return

    texts = [c["text"] for c in corpus]
    embeddings = embed_texts(texts)

    for c, emb in zip(corpus, embeddings):
        c["embedding"] = emb

    os.makedirs("rag_index", exist_ok=True)
    with open("rag_index/index.json", "w", encoding="utf-8") as f:
        json.dump(corpus, f)

    print(f"✅ Saved {len(corpus)} chunks to rag_index/index.json")


if __name__ == "__main__":
    main()