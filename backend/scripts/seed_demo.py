"""Load the public read-only demo documents (docs/Demo.md).

    uv run python -m scripts.seed_demo            # load what is missing
    uv run python -m scripts.seed_demo --replace  # remove them and load again
    uv run python -m scripts.seed_demo --list     # show what is loaded now

Safe to run again: a document already loaded is left alone, and one whose file has gone (a host
without a persistent disk restarted) is replaced. The work itself lives in app/services/demo.py,
so the API can also do it at start-up with DEMO_AUTO_SEED=true.
"""

import argparse
import sys

from app.db.session import SessionLocal
from app.services import demo


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replace", action="store_true", help="remove the demo documents first")
    parser.add_argument("--list", action="store_true", help="show what is loaded and stop")
    args = parser.parse_args()

    if args.list:
        with SessionLocal() as db:
            documents = demo.seeded(db)
        if not documents:
            print("No demo documents are loaded.")
        for document in documents:
            print(f"  {document.original_filename} — {document.status.value} ({document.id})")
        return 0

    if args.replace:
        print(f"Removed {demo.remove()} demo document(s).")

    missing = demo.missing_files()
    if len(missing) == len(demo.DEMO_FILES):
        print("None of the demo source files are in this deployment:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        print(
            "\nRun `uv run python -m scripts.fetch_indiacode` for the Acts and "
            "`uv run python -m scripts.make_sample_pdf` for the samples.",
            file=sys.stderr,
        )
        return 1

    print(f"Loading {len(demo.DEMO_FILES) - len(missing)} demo document(s):")
    for message in demo.seed():
        print(f"  {message}", flush=True)
    print("\nDone. /demo now works without signing in.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
