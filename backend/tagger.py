"""Ask the LLM gateway to suggest a title and tags for an untagged note.

Best-effort by design: every failure path returns None and the caller uploads
the note untagged. A tagging outage must never cost you an upload.
"""

import json
import logging
import os
import re

import httpx

log = logging.getLogger(__name__)

GATEWAY_URL = os.environ.get(
    "GATEWAY_URL", "https://llm-gateway-production-b085.up.railway.app/invoke"
)
GATEWAY_API_KEY = os.environ.get("GATEWAY_API_KEY", "")
TAGGER_MODEL = os.environ.get("TAGGER_MODEL", "deepseek/deepseek-v4-flash-0731")

# The gateway has no hard total-duration timeout of its own, so we enforce one
# here — upload is blocked on this call.
TIMEOUT_SECONDS = float(os.environ.get("TAGGER_TIMEOUT", "20"))

# Tags come from the top of a document; sending the whole thing costs more and
# tags no better.
MAX_CHARS = 6000
MAX_TAGS = 5

SYSTEM_PROMPT = """\
You label personal notes. Given a note, you return a short title and a few topic tags.

Rules:
- Reply with a single JSON object and nothing else. No prose, no code fences.
- Shape: {"title": "...", "tags": ["...", "..."]}
- title: a concise human title for the note, at most 60 characters. Prefer the
  document's own heading if it has one.
- tags: 2 to 5 lowercase-kebab-case topic tags, most important first.
- Strongly prefer reusing a tag from the existing list when it fits. Only coin a
  new tag when nothing in the list describes the note.
- Tag the subject matter, not the format. Avoid "note", "document", "markdown".\
"""


def is_configured() -> bool:
    return bool(GATEWAY_API_KEY) and os.environ.get("ENABLE_AUTO_TAGGING", "1") != "0"


def _normalize_tag(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value).strip().lower())
    return slug.strip("-")


def _extract_json(content: str) -> dict | None:
    """The gateway has no structured-output mode, so the model may wrap the
    object in fences or prose. Pull out the first balanced object."""
    text = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    for i, char in enumerate(text[start:], start=start):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    parsed = json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
                return parsed if isinstance(parsed, dict) else None
    return None


def _build_messages(body: str, known_tags: list[str]) -> list[dict]:
    vocabulary = ", ".join(known_tags) if known_tags else "(none yet)"
    excerpt = body[:MAX_CHARS]
    truncated = "\n\n[note truncated]" if len(body) > MAX_CHARS else ""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Tags already in use: {vocabulary}\n\n"
                f"---- NOTE ----\n{excerpt}{truncated}"
            ),
        },
    ]


def suggest(body: str, known_tags: list[str]) -> dict | None:
    """Return {"title": str, "tags": list[str]} or None if unavailable."""
    if not is_configured():
        log.debug("auto-tagging disabled (GATEWAY_API_KEY not set)")
        return None

    if not body.strip():
        log.debug("auto-tagging skipped: empty body")
        return None

    try:
        response = httpx.post(
            GATEWAY_URL,
            headers={"Authorization": f"Bearer {GATEWAY_API_KEY}"},
            json={"model": TAGGER_MODEL, "messages": _build_messages(body, known_tags)},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        content = response.json().get("content")
    except (httpx.HTTPError, ValueError) as exc:
        log.warning(f"gateway call failed: {type(exc).__name__}: {exc}")
        return None

    if not isinstance(content, str):
        log.warning(f"gateway response content is not a string: {type(content)}")
        return None

    parsed = _extract_json(content)
    if parsed is None:
        log.warning(f"could not parse JSON from model reply: {content[:200]}")
        return None

    raw_tags = parsed.get("tags")
    tags: list[str] = []
    if isinstance(raw_tags, list):
        for tag in raw_tags:
            slug = _normalize_tag(tag)
            if slug and slug not in tags:
                tags.append(slug)

    title = parsed.get("title")
    title = str(title).strip()[:60] if isinstance(title, str) and title.strip() else None

    if not tags and not title:
        log.warning("model returned neither title nor tags")
        return None

    result = {"title": title, "tags": tags[:MAX_TAGS]}
    log.info(f"tagged: title={title!r} tags={tags[:MAX_TAGS]}")
    return result
