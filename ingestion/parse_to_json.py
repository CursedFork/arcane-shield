#!/usr/bin/env python3
"""
Step 2: Parse Markdown files (output of convert.py) into structured JSON
using the Claude API, matching the Arcane Shield database schemas.

Usage:
    ANTHROPIC_API_KEY=sk-... python parse_to_json.py --input ./markdown --output ./json_output

Output files (one per record type):
    magic_items.json, bestiary.json, mechanics.json, campaigns.json
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import anthropic

MODEL = "claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# Schema definitions (used in prompts and validation)
# ---------------------------------------------------------------------------

SCHEMAS: dict[str, dict[str, Any]] = {
    "magic_items": {
        "required": ["name", "item_type", "rarity", "requires_attunement", "description", "mechanical_effect"],
        "optional": ["attunement_requirement", "charges", "source_campaign", "tags"],
        "enum": {
            "item_type": ["Wondrous", "Weapon", "Armor", "Potion", "Ring", "Wand", "Staff", "Rod", "Scroll", "Other"],
            "rarity": ["Common", "Uncommon", "Rare", "Very Rare", "Legendary", "Artifact"],
        },
        "array_fields": ["tags"],
        "bool_fields": ["requires_attunement"],
        "int_fields": ["charges"],
    },
    "bestiary": {
        "required": ["name", "ac", "max_hp", "initiative_mod", "cr", "statblock_md"],
        "optional": ["tags"],
        "array_fields": ["tags"],
        "int_fields": ["ac", "max_hp", "initiative_mod"],
    },
    "mechanics": {
        "required": ["title", "body_md"],
        "optional": ["campaign", "tags"],
        "array_fields": ["tags"],
    },
    "campaigns": {
        "required": ["title", "body_md"],
        "optional": ["tags"],
        "array_fields": ["tags"],
    },
}

SYSTEM_PROMPT = """\
You are a structured data extractor for a D&D 5e campaign management tool called Arcane Shield.

Given Markdown text from a D&D sourcebook, campaign document, homebrew PDF, or similar file, extract ALL records that match the following schemas and return ONLY a valid JSON object — no prose, no code fences, no explanation.

The JSON object must have exactly these top-level keys (include each key even if empty):
- "magic_items": array of magic item records
- "bestiary": array of monster/NPC records
- "mechanics": array of homebrew rule or mechanic records
- "campaigns": array of campaign writeup records

Schema for each type:

magic_items:
  name (string, required)
  item_type (string, required; one of: Wondrous, Weapon, Armor, Potion, Ring, Wand, Staff, Rod, Scroll, Other)
  rarity (string, required; one of: Common, Uncommon, Rare, Very Rare, Legendary, Artifact)
  requires_attunement (boolean, required)
  attunement_requirement (string or null; e.g. "by a spellcaster")
  description (string, required; full item description)
  mechanical_effect (string, required; the mechanical rules text)
  charges (integer or null)
  source_campaign (string or null)
  tags (array of strings)

bestiary:
  name (string, required)
  ac (integer, required)
  max_hp (integer, required)
  initiative_mod (integer, required; derived from DEX modifier)
  cr (string, required; e.g. "1/4", "5", "20")
  statblock_md (string, required; full stat block as Markdown)
  tags (array of strings; e.g. ["undead", "boss", "spellcaster"])

mechanics:
  title (string, required)
  body_md (string, required; full rule text as Markdown)
  campaign (string or null)
  tags (array of strings)

campaigns:
  title (string, required)
  body_md (string, required; full campaign text as Markdown)
  tags (array of strings)

Rules:
- If a field is not found, use null for nullable fields or reasonable defaults.
- tags should be lowercase, kebab-case strings.
- Do NOT invent data not present in the source text.
- If nothing of a given type is found, return an empty array for that key.
- Output ONLY the JSON object. No markdown fences, no explanation.
"""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_record(record_type: str, record: dict) -> list[str]:
    """Return a list of error strings, empty if valid."""
    schema = SCHEMAS[record_type]
    errors: list[str] = []

    for field in schema["required"]:
        if field not in record or record[field] is None or record[field] == "":
            errors.append(f"missing required field '{field}'")

    for field, allowed in schema.get("enum", {}).items():
        val = record.get(field)
        if val is not None and val not in allowed:
            errors.append(f"'{field}' value '{val}' not in allowed set {allowed}")

    for field in schema.get("array_fields", []):
        val = record.get(field)
        if val is not None and not isinstance(val, list):
            errors.append(f"'{field}' must be an array, got {type(val).__name__}")

    for field in schema.get("bool_fields", []):
        val = record.get(field)
        if val is not None and not isinstance(val, bool):
            errors.append(f"'{field}' must be boolean, got {type(val).__name__}")

    for field in schema.get("int_fields", []):
        val = record.get(field)
        if val is not None and not isinstance(val, int):
            errors.append(f"'{field}' must be integer, got {type(val).__name__}")

    return errors


def strip_fences(text: str) -> str:
    """Remove markdown code fences if the model adds them despite instructions."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last fence lines
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------

def extract_from_markdown(client: anthropic.Anthropic, md_text: str, source_name: str) -> dict[str, list[dict]]:
    """Call the Claude API and return parsed records keyed by type."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Extract all records from this document:\n\n---\n{md_text}\n---",
            }
        ],
    )

    raw = message.content[0].text
    raw = strip_fences(raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  [WARN] JSON parse error for {source_name}: {e}")
        print(f"  Raw response (first 500 chars): {raw[:500]}")
        return {k: [] for k in SCHEMAS}

    # Ensure all keys present
    for key in SCHEMAS:
        if key not in parsed:
            parsed[key] = []

    return parsed


def process_directory(input_dir: Path, output_dir: Path, client: anthropic.Anthropic) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    md_files = list(input_dir.rglob("*.md"))
    if not md_files:
        print(f"No .md files found in {input_dir}")
        return

    # Accumulate records across all files
    all_records: dict[str, list[dict]] = {k: [] for k in SCHEMAS}
    validation_report: list[str] = []

    for md_path in md_files:
        rel = md_path.relative_to(input_dir)
        print(f"Processing: {rel} ...", flush=True)

        md_text = md_path.read_text(encoding="utf-8")
        if not md_text.strip():
            print("  [SKIP] empty file")
            continue

        extracted = extract_from_markdown(client, md_text, str(rel))

        for record_type, records in extracted.items():
            valid_count = 0
            for i, record in enumerate(records):
                errors = validate_record(record_type, record)
                if errors:
                    msg = f"  [SKIP] {rel} / {record_type}[{i}] ({record.get('name') or record.get('title', '?')}): {'; '.join(errors)}"
                    print(msg)
                    validation_report.append(msg)
                else:
                    all_records[record_type].append(record)
                    valid_count += 1

            if records:
                print(f"  {record_type}: {valid_count}/{len(records)} records valid")

    # Write output files
    for record_type, records in all_records.items():
        out_path = output_dir / f"{record_type}.json"
        out_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWrote {len(records)} {record_type} records → {out_path}")

    if validation_report:
        report_path = output_dir / "validation_errors.txt"
        report_path.write_text("\n".join(validation_report), encoding="utf-8")
        print(f"\n{len(validation_report)} validation error(s) logged → {report_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse Markdown docs into structured JSON for Arcane Shield"
    )
    parser.add_argument("--input", required=True, help="Directory containing .md files (output of convert.py)")
    parser.add_argument("--output", required=True, help="Directory to write JSON output files")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    input_dir = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output).expanduser().resolve()

    if not input_dir.exists():
        print(f"Error: input directory does not exist: {input_dir}", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    process_directory(input_dir, output_dir, client)


if __name__ == "__main__":
    main()
