#!/usr/bin/env python3
"""CLI wrapper for generating the resume PDF.

Usage:
    python3 generate.py                     # build PDF with the classic template
    python3 generate.py --template modern   # pick a different template
    python3 generate.py --tex-only          # only write resume.tex (no compile)
"""

import argparse
import json
import sys
from pathlib import Path

from resume_generator import DEFAULT_FONT, FONTS, TEMPLATES, compile_pdf, render_tex

BASE_DIR = Path(__file__).resolve().parent
JSON_PATH = BASE_DIR / "resume.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build ATS-friendly resume PDF.")
    parser.add_argument(
        "--template",
        choices=list(TEMPLATES),
        default="classic",
        help="Template to use.",
    )
    parser.add_argument(
        "--font",
        choices=list(FONTS),
        default=DEFAULT_FONT,
        help="Font to use.",
    )
    parser.add_argument(
        "--tex-only",
        action="store_true",
        help="Write resume.tex only, skip PDF compilation.",
    )
    args = parser.parse_args()

    if not JSON_PATH.exists():
        sys.exit(f"Missing {JSON_PATH.name}. Create it first.")

    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    tex = render_tex(data, args.template, args.font)
    (BASE_DIR / "resume.tex").write_text(tex, encoding="utf-8")
    print(f"Wrote resume.tex (template: {args.template}, font: {args.font})")

    if args.tex_only:
        return

    pdf = compile_pdf(tex)
    out_name = data.get("name", "resume").replace(" ", "_")
    pdf_path = BASE_DIR / f"{out_name}_{args.template}.pdf"
    pdf_path.write_bytes(pdf)
    print(f"Built {pdf_path.name}")


if __name__ == "__main__":
    main()
