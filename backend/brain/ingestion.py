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
    """Parse inert HTML; prefer semantic article/main content. No resource loading."""
    VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    SKIP = {'script','style','nav','footer','aside','form','button','noscript','template'}
    BLOCK = {'p','div','li','h1','h2','h3','h4','section','article','main','pre','br','tr'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = {'tag':'root','attrs':{},'children':[]}
        self.stack = [self.root]
        self.candidates = []

    def handle_starttag(self, tag, attrs):
        node = {'tag':tag,'attrs':dict(attrs),'children':[]}
        self.stack[-1]['children'].append(node)
        if tag not in self.VOID: self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID: self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1,0,-1):
            if self.stack[i]['tag']==tag:
                del self.stack[i:]; break

    def handle_data(self, data): self.stack[-1]['children'].append(data)

    def render(self, node, fallback=False):
        if isinstance(node,str): return node
        attrs=node['attrs']; tag=node['tag']
        if tag in self.SKIP or 'hidden' in attrs or attrs.get('aria-hidden')=='true': return ''
        if fallback and tag=='header': return ''
        if re.search(r'display\s*:\s*none|visibility\s*:\s*hidden',attrs.get('style',''),re.I): return ''
        text=''.join(self.render(child,fallback) for child in node['children'])
        if tag in {'article','main'} or attrs.get('role')=='main': self.candidates.append(text)
        return ('\n'+text+'\n') if tag in self.BLOCK else text


def article_text(html: str) -> str:
    parser=ArticleParser(); parser.feed(html); parser.close()
    all_text=parser.render(parser.root)
    text=max(parser.candidates,key=len) if parser.candidates else parser.render(parser.root,True)
    return re.sub(r'\n[ \t]*\n+', '\n', text).strip()


def digest(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()
