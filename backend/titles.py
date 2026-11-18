"""Work out a readable title for a note without calling the LLM.

Order of preference:
  1. `title:` in frontmatter (handled by frontmatter.parse, not here)
  2. the document's own heading: first `# H1` in markdown, or <title>/<h1> in HTML
  3. a cleaned-up filename: "2026-10-11-backend-study-guide.md" -> "Backend study guide"

The LLM tagger may still supply a title, but a note never depends on it.
"""

import html
import re

MAX_LENGTH = 120

_FENCE = re.compile(r"^\s*(```|~~~)")
_MD_H1 = re.compile(r"^#\s+(.+?)\s*#*\s*$")
_HTML_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_HTML_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.IGNORECASE | re.DOTALL)
_TAGS = re.compile(r"<[^>]+>")

_EXTENSION = re.compile(r"\.(md|html?)$", re.IGNORECASE)
_LEADING_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}[-_ ]*")
_COPY_SUFFIX = re.compile(r"\s*\(\d+\)$")  # "notes (1)" from browser downloads
_COLLISION_SUFFIX = re.compile(r"-\d{14}$")  # timestamp added by upload_note


def _clean(text: str) -> str | None:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_LENGTH] if text else None


def from_markdown(body: str) -> str | None:
    """First level-1 ATX heading outside a code block."""
    in_fence = False
    for line in body.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = _MD_H1.match(line)
        if match:
            # Drop inline markdown that reads badly in a plain-text title.
            return _clean(re.sub(r"[*_`]", "", match.group(1)))
    return None


def from_html(text: str) -> str | None:
    for pattern in (_HTML_TITLE, _HTML_H1):
        match = pattern.search(text)
        if match:
            title = _clean(html.unescape(_TAGS.sub("", match.group(1))))
            if title:
                return title
    return None


def from_filename(filename: str) -> str:
    stem = _EXTENSION.sub("", filename)
    stem = _COLLISION_SUFFIX.sub("", stem)
    stem = _COPY_SUFFIX.sub("", stem)
    stem = _LEADING_DATE.sub("", stem)
    words = re.sub(r"[-_]+", " ", stem).strip()
    if not words:
        return filename
    return words[0].upper() + words[1:]


def derive(filename: str, body: str) -> str:
    """Best title available from the content itself, falling back to the filename.

    `body` is the note text with any frontmatter already stripped.
    """
    if filename.lower().endswith((".html", ".htm")):
        title = from_html(body)
    else:
        title = from_markdown(body)
    return title or from_filename(filename)
