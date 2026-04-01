"""Document parsing — markdown, plain text, HTML."""

import re
from dataclasses import dataclass
from html.parser import HTMLParser


@dataclass
class ParsedSection:
    content: str
    heading: str | None = None
    level: int = 0
    index: int = 0


_HEADER_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def parse_markdown(raw: str) -> list[ParsedSection]:
    """Split markdown by headers. Each section includes its heading."""
    if not raw.strip():
        return []

    sections: list[ParsedSection] = []
    matches = list(_HEADER_RE.finditer(raw))

    if not matches:
        return [ParsedSection(content=raw.strip(), index=0)]

    # Content before first header
    if matches[0].start() > 0:
        pre = raw[: matches[0].start()].strip()
        if pre:
            sections.append(ParsedSection(content=pre, index=0))

    for i, match in enumerate(matches):
        level = len(match.group(1))
        heading = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        content = raw[start:end].strip()
        full = f"{match.group(0)}\n{content}" if content else match.group(0)
        sections.append(
            ParsedSection(content=full, heading=heading, level=level, index=len(sections))
        )

    return sections


def parse_plain_text(raw: str) -> list[ParsedSection]:
    """Split plain text by double-newline paragraph boundaries."""
    if not raw.strip():
        return []

    paragraphs = re.split(r"\n\s*\n", raw.strip())
    return [
        ParsedSection(content=p.strip(), index=i) for i, p in enumerate(paragraphs) if p.strip()
    ]


class _HTMLStripper(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def get_text(self) -> str:
        return "".join(self.parts)


def parse_html(raw: str) -> list[ParsedSection]:
    """Strip HTML tags, then parse as plain text."""
    stripper = _HTMLStripper()
    stripper.feed(raw)
    return parse_plain_text(stripper.get_text())


def parse_pdf(raw: str) -> list[ParsedSection]:
    """Parse PDF content using Unstructured. Requires [docs] extra."""
    try:
        from unstructured.partition.pdf import partition_pdf

        elements = partition_pdf(text=raw)
        sections = []
        for i, el in enumerate(elements):
            sections.append(ParsedSection(content=str(el), index=i))
        return sections if sections else [ParsedSection(content=raw, index=0)]
    except ImportError:
        raise ImportError(
            "PDF parsing requires the 'unstructured' package. "
            "Install with: pip install -e '.[docs]'"
        ) from None


def parse_docx(raw: str) -> list[ParsedSection]:
    """Parse DOCX content using Unstructured. Requires [docs] extra."""
    try:
        from unstructured.partition.docx import partition_docx

        elements = partition_docx(text=raw)
        sections = []
        for i, el in enumerate(elements):
            sections.append(ParsedSection(content=str(el), index=i))
        return sections if sections else [ParsedSection(content=raw, index=0)]
    except ImportError:
        raise ImportError(
            "DOCX parsing requires the 'unstructured' package. "
            "Install with: pip install -e '.[docs]'"
        ) from None


def parse_document(raw: str, content_type: str) -> list[ParsedSection]:
    """Dispatch to the appropriate parser based on content_type."""
    parsers = {
        "text/markdown": parse_markdown,
        "text/plain": parse_plain_text,
        "text/html": parse_html,
        "application/pdf": parse_pdf,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": parse_docx,
    }
    parser = parsers.get(content_type, parse_plain_text)
    return parser(raw)
