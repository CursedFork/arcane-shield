#!/usr/bin/env python3
"""
Step 1: Convert PDFs and DOCX files to Markdown using markitdown.

Usage:
    python convert.py --input ./raw_docs --output ./markdown
"""

import argparse
import sys
from pathlib import Path

from markitdown import MarkItDown


SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".html", ".htm"}


def convert_directory(input_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    md = MarkItDown()

    files = [
        f for f in input_dir.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not files:
        print(f"No supported files found in {input_dir}")
        return

    success = 0
    failures = 0

    for src in files:
        rel = src.relative_to(input_dir)
        dest = output_dir / rel.with_suffix(".md")
        dest.parent.mkdir(parents=True, exist_ok=True)

        print(f"Converting: {rel} ...", end=" ", flush=True)
        try:
            result = md.convert(str(src))
            dest.write_text(result.text_content, encoding="utf-8")
            print("OK")
            success += 1
        except Exception as e:
            print(f"FAILED — {e}")
            failures += 1

    print(f"\nDone: {success} converted, {failures} failed.")
    if failures:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert PDF/DOCX files to Markdown")
    parser.add_argument("--input", required=True, help="Directory containing source files")
    parser.add_argument("--output", required=True, help="Directory to write .md files")
    args = parser.parse_args()

    input_dir = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output).expanduser().resolve()

    if not input_dir.exists():
        print(f"Error: input directory does not exist: {input_dir}", file=sys.stderr)
        sys.exit(1)

    convert_directory(input_dir, output_dir)


if __name__ == "__main__":
    main()
