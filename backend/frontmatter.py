"""Optional YAML frontmatter at the top of a note.

A note may begin with a `---` delimited block:

    ---
    title: Broadcasting
    tags: [numpy, shapes]
    prereqs: [NP-01, NP-02]
    ---

`title` and `tags` are the only keys the app understands. Everything else is
kept verbatim so a note can carry whatever structure it likes without the app
needing to know what it means. Notes without a block are unaffected.
"""

import yaml

DELIMITER = "---"


def _normalize_tags(value) -> list[str]:
    """Accept either a YAML list or a comma-separated string."""
    if value is None:
        return []
    if isinstance(value, str):
        parts = value.split(",")
    elif isinstance(value, list):
        parts = value
    else:
        return []
    return [t for t in (str(p).strip() for p in parts) if t]


def _stringify(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Return (fields, body). Fields is empty and body is `text` unchanged when
    there is no well-formed frontmatter block."""
    if not text.startswith(DELIMITER):
        return {}, text

    lines = text.split("\n")
    if lines[0].strip() != DELIMITER:
        return {}, text

    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == DELIMITER:
            block, body = "\n".join(lines[1:i]), "\n".join(lines[i + 1 :])
            break
    else:
        return {}, text  # unterminated block: treat as ordinary content

    try:
        fields = yaml.safe_load(block)
    except yaml.YAMLError:
        return {}, text

    if not isinstance(fields, dict):
        return {}, text

    return fields, body.lstrip("\n")


def dump(fields: dict, body: str) -> str:
    """Render `fields` as a frontmatter block above `body`."""
    block = yaml.safe_dump(
        fields, sort_keys=False, allow_unicode=True, default_flow_style=None
    ).strip()
    return f"{DELIMITER}\n{block}\n{DELIMITER}\n\n{body.lstrip()}"


def parse(text: str, *, fallback_title: str) -> tuple[dict, str]:
    """Split `text` and shape the fields into the note metadata we store."""
    fields, body = split_frontmatter(text)

    title = fields.pop("title", None)
    tags = _normalize_tags(fields.pop("tags", None))
    extra = {str(k): _stringify(v) for k, v in fields.items() if v is not None}

    return {
        "title": str(title).strip() if title else fallback_title,
        "tags": tags,
        "meta": extra,
    }, body
