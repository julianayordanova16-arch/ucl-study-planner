"""Ask Claude how hard each course item is."""
import base64
import io
import json

import anthropic
from dotenv import load_dotenv
from pypdf import PdfReader, PdfWriter

from pdf_text import extract_text
from store import list_items, update_item

load_dotenv()  # reads ANTHROPIC_API_KEY from .env
client = anthropic.Anthropic()

MODEL = "claude-haiku-5-5"
MAX_TEXT_CHARS = 60_000   # roughly 15k tokens, which keeps each request cheap
MAX_SCANNED_PAGES = 15    # for image-only PDFs, send just the first pages

# The exact shape of answer we want back
SCHEMA = {
    "type": "object",
    "properties": {
        "difficulty": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
        "est_hours": {"type": "number"},
        "topics": {"type": "array", "items": {"type": "string"}},
        "reason": {"type": "string"},
    },
    "required": ["difficulty", "est_hours", "topics", "reason"],
    "additionalProperties": False,
}

INSTRUCTIONS = """You are helping a second-year UCL physics undergraduate plan their study week.
Rate how hard this course material is for them, and how long it will realistically take.

Item type: {kind}
Module: {module}
Pages: {pages}

Difficulty scale:
1 = quick revision, little new content
2 = straightforward, mostly familiar ideas
3 = typical new lecture material, needs some effort
4 = demanding: dense maths, new techniques, or several hard problems
5 = very hard: long, abstract, or many difficult derivations/problems

est_hours = hours to properly learn the lecture notes, or to attempt every problem on a sheet.
topics = 3 to 6 short topic names.
reason = one sentence explaining the rating."""


def pdf_first_pages(path: str, n_pages: int) -> str:
    """The first n pages of a PDF, as base64 text the API can accept."""
    reader = PdfReader(path)
    writer = PdfWriter()
    for page in reader.pages[:n_pages]:
        writer.add_page(page)
    buffer = io.BytesIO()
    writer.write(buffer)
    return base64.standard_b64encode(buffer.getvalue()).decode("utf-8")


def build_content(item: dict) -> list:
    """What we send to Claude: extracted text, or the PDF itself if it's scanned."""
    prompt = INSTRUCTIONS.format(kind=item["kind"], module=item["module"], pages=item["pages"])

    if item["scanned"]:
        pages_sent = min(item["pages"], MAX_SCANNED_PAGES)
        prompt += (f"\n\nThis PDF is images only. You are seeing the first {pages_sent} "
                   f"of {item['pages']} pages, so scale est_hours to the full length.")
        return [
            {"type": "document",
             "source": {"type": "base64", "media_type": "application/pdf",
                        "data": pdf_first_pages(item["path"], pages_sent)}},
            {"type": "text", "text": prompt},
        ]

    text = extract_text(item["path"])["text"][:MAX_TEXT_CHARS]
    return [{"type": "text", "text": f"{prompt}\n\n<material>\n{text}\n</material>"}]


def score_item(item: dict) -> dict:
    """Ask Claude for a difficulty rating and return it as a dictionary."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": build_content(item)}],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    text = next(block.text for block in response.content if block.type == "text")
    print(f"   tokens: {response.usage.input_tokens:,} in / "
          f"{response.usage.output_tokens:,} out")
    return json.loads(text)


if __name__ == "__main__":
    for item in list_items():
        if item["difficulty"] is not None:
            print(f"Skipping {item['filename']} (already scored)")
            continue
        print(f"Scoring {item['filename']} ...")
        result = score_item(item)
        update_item(item["id"], **result)
        print(f"   difficulty {result['difficulty']}/5, about {result['est_hours']}h")
        print(f"   {result['reason']}\n")