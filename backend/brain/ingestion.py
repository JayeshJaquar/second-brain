"""Deterministic ingestion. Raw text and OCR coordinates remain available for inspection."""
import hashlib
import re
from html.parser import HTMLParser

OVERRIDES = re.compile(r"\b(?:ignore|disregard|forget|override)\b[\s\S]{0,90}\b(?:instructions?|rules?|user|system|previous|above|prompt)\b|\b(?:system|developer|assistant)\s*(?:override|message|instruction|:)|<\|?(?:system|assistant|developer|im_start)\b|\b(?:mark|set)\b[\s\S]{0,40}\b(?:supported|conflict)\b|\byou are now\b", re.I)
NOISE = {"Ask Gemini", "Ask HuggingChat", "New Chrome available", "All Bookmarks", "Cancel", "'ChatGPT' started debugging this browser"}


def clean(text: str, kind: str = "note") -> str:
    if kind != "ocr":
        return text.strip()
    return "\n".join(line.rstrip() for line in text.splitlines() if line.strip() not in NOISE).strip()


def units(text: str, maximum: int = 900):
    # Sentence boundaries preserve surrounding context; long code/paragraphs use bounded spans.
    result = []
    for m in re.finditer(r"[^.!?]+(?:[.!?](?=\s|$)|$)", text):
        start, end = m.span()
        while start < end and text[start].isspace(): start += 1
        for pos in range(start, end, maximum):
            part = text[pos:min(pos + maximum, end)].rstrip()
            if part: result.append((pos, pos + len(part), part))
    return result


class ArticleParser(HTMLParser):
    """Explicit HTML imports only: no scripts, resource loading, or arbitrary URL fetching."""
    def __init__(self):
        super().__init__(); self.hidden = 0; self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "nav", "footer", "header"}: self.hidden += 1
        if not self.hidden and tag in {"p", "div", "li", "h1", "h2", "br"}: self.parts.append("\n")
    def handle_endtag(self, tag):
        if tag in {"script", "style", "nav", "footer", "header"}: self.hidden = max(0, self.hidden - 1)
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)


def article_text(html: str) -> str:
    parser = ArticleParser(); parser.feed(html)
    return re.sub(r"\n\s*\n+", "\n", "".join(parser.parts)).strip()


def digest(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()
