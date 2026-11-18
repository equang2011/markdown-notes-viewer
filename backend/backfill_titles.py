"""Recompute the stored title of every note from its file on disk.

Only `title` changes; tags, meta and the files themselves are left alone.
Frontmatter titles still win, so notes that already have a good title keep it.

    python backfill_titles.py            # dry run: print what would change
    python backfill_titles.py --apply    # write notes.json

Run it where UPLOADS_DIR points at the real data (on Railway: `railway ssh`,
then run it from /app). Don't run it while an upload is in progress.
"""

import sys

from main import UPLOADS_DIR, note_fields, read_metadata, write_metadata


def main(apply: bool) -> None:
    notes = read_metadata()
    changed = 0

    for note in notes:
        path = UPLOADS_DIR / note["filename"]
        if not path.exists():
            print(f"skip (missing file): {note['filename']}")
            continue

        text = path.read_bytes().decode("utf-8", errors="replace")
        new_title = note_fields(note["filename"], text)["title"]
        if new_title != note.get("title"):
            print(f"{note.get('title')!r}\n  -> {new_title!r}")
            note["title"] = new_title
            changed += 1

    print(f"\n{changed} of {len(notes)} titles {'updated' if apply else 'would change'}.")
    if apply and changed:
        write_metadata(notes)
    elif changed:
        print("Dry run. Re-run with --apply to save.")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
