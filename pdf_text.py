"""Pull the text out of PDFs."""
from pathlib import Path

from pypdf import PdfReader

from pypdf.errors import PdfReadError

MIN_CHARS_PER_PAGE = 200  # fewer than this means it's probably scanned images


def extract_text(pdf_path) -> dict:
    """Return the text of a PDF plus some basic facts about it."""
    reader = PdfReader(pdf_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages)
    n_pages = len(reader.pages)
    chars = len(text.strip())
    return {
        "text": text,
        "pages": n_pages,
        "chars": chars,
        "scanned": n_pages > 0 and chars / n_pages < MIN_CHARS_PER_PAGE,
    }


if __name__ == "__main__":
    for pdf in sorted(Path("data").glob("*.pdf")):
        try:
            result = extract_text(pdf)
        except PdfReadError as error:
            print(f"{pdf.name}: COULD NOT READ ({error})\n")
            continue
        flag = "  <- probably scanned" if result["scanned"] else ""
        print(f"{pdf.name}: {result['pages']} pages, {result['chars']:,} characters{flag}")
        preview = " ".join(result["text"].split())[:200]
        print(f"   {preview}...\n")
import logging
logging.getLogger("pypdf").setLevel(logging.ERROR)