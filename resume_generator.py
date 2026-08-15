"""Core resume generation library.

Renders LaTeX from a resume data dict using Jinja2 templates and compiles
it to PDF with pdflatex. Shared by the CLI (generate.py) and the Streamlit
UI (app.py).
"""

from __future__ import annotations

import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

# Template name -> (display name, description)
TEMPLATES = {
    "classic": ("Classic", "Traditional look with black rules."),
    "modern": ("Modern", "Accent-color headings with a colored rule."),
    "compact": ("Compact", "9pt font and tight margins to fit more content."),
}

# ATS-friendly font name -> (display name, LaTeX preamble snippet).
# Only fonts shipped with a basic TeX Live install are listed so they compile
# out of the box. The snippet selects the typeface (and, for sans-serif fonts,
# switches the whole document to it).
FONTS = {
    "lmodern": ("Latin Modern (Serif)", "\\usepackage{lmodern}"),
    "cm": ("Computer Modern (Serif)", ""),
    "times": ("Times New Roman (Serif)", "\\usepackage{times}"),
    "palatino": ("Palatino (Serif)", "\\usepackage{mathpazo}"),
    "charter": ("Charter (Serif)", "\\usepackage{charter}"),
    "bookman": ("Bookman (Serif)", "\\usepackage{bookman}"),
    "newcent": ("New Century Schoolbook (Serif)", "\\usepackage{newcent}"),
    "helvetica": (
        "Helvetica / Arial (Sans-Serif)",
        "\\usepackage{helvet}\\renewcommand{\\familydefault}{\\sfdefault}",
    ),
    "avant": (
        "Avant Garde (Sans-Serif)",
        "\\usepackage{avant}\\renewcommand{\\familydefault}{\\sfdefault}",
    ),
}

DEFAULT_FONT = "lmodern"

# Marker file that must be present in the TeX distribution for each font to be
# usable. ``None`` means the font is always available (e.g. the default
# Computer Modern). We probe these so the UI only offers fonts that will
# actually compile in the user's TeX install.
_FONT_PROBES = {
    "lmodern": "ec-lmr10.tfm",
    "cm": None,
    "times": "ptmr8t.tfm",
    "palatino": "pplr8t.tfm",
    "charter": "bchr8t.tfm",
    "bookman": "pbkl8t.tfm",
    "newcent": "pncr8t.tfm",
    "helvetica": "phvr8t.tfm",
    "avant": "pavr8t.tfm",
}


def _kpsewhich(name: str) -> str | None:
    """Return the path for a file resolved by ``kpsewhich``, or None."""
    try:
        proc = subprocess.run(
            ["kpsewhich", name], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    path = proc.stdout.strip()
    return path or None


def _font_available(font: str) -> bool:
    probe = _FONT_PROBES.get(font)
    if probe is None:
        return True
    return _kpsewhich(probe) is not None


@lru_cache(maxsize=1)
def installed_fonts() -> list[str]:
    """Return the font keys that are actually usable in this TeX install."""
    return [f for f in FONTS if _font_available(f)]

# Default headings for each resume section. Users can override these via the
# "section_labels" dict in resume.json (and the Streamlit "Section Labels" tab).
DEFAULT_SECTION_LABELS = {
    "profile": "Profile",
    "skills": "Core Technical Skills",
    "experience": "Professional Experience",
    "impact": "Selected Engineering Impact",
    "leadership": "Leadership & Community",
    "education": "Education",
    "certifications": "Certifications & Professional Courses",
    "capabilities": "Technical Capabilities",
    "career_progression": "Career Progression",
    "professional_profile": "Professional Profile",
    "technology_index": "Selected Technology Index",
    "references": "References",
}

# Which sections are shown by default. Users can hide a section by setting its
# key to False in the "sections" dict (via the Streamlit "Sections" tab).
DEFAULT_SECTIONS = {key: True for key in DEFAULT_SECTION_LABELS}


def latex_escape(text: str) -> str:
    """Escape LaTeX special characters and normalize unicode symbols."""
    if text is None:
        return ""
    text = str(text)
    text = text.replace("\\", r"\textbackslash{}")
    for ch in ("&", "%", "$", "#", "_", "{", "}"):
        text = text.replace(ch, "\\" + ch)
    text = text.replace("~", r"\textasciitilde{}")
    text = text.replace("^", r"\textasciicircum{}")
    text = text.replace("\u2013", "--")                # en dash
    text = text.replace("\u2014", "---")               # em dash
    text = text.replace("\u2192", r"$\rightarrow$")    # right arrow
    text = text.replace("\u00b7", r"$\cdot$")          # middle dot
    text = text.replace("\u00d7", r"$\times$")         # multiplication sign
    return text


def _env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=False,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
        # LaTeX-safe delimiters that do not clash with braces.
        variable_start_string="<<",
        variable_end_string=">>",
        block_start_string="<%",
        block_end_string="%>",
        comment_start_string="<#",
        comment_end_string="#>",
    )
    env.filters["tex"] = latex_escape
    return env


def build_contact_line(contact: dict) -> str:
    """Build the raw LaTeX contact line with hyperlinks."""
    parts = []

    def add(text: str) -> None:
        if text:
            parts.append(latex_escape(text))

    add(contact.get("location"))

    email = contact.get("email")
    if email:
        parts.append(rf"\href{{mailto:{latex_escape(email)}}}{{{latex_escape(email)}}}")

    add(contact.get("phone"))

    github = contact.get("github")
    if github:
        parts.append(rf"\href{{https://{latex_escape(github)}}}{{{latex_escape(github)}}}")

    linkedin = contact.get("linkedin")
    if linkedin:
        parts.append(rf"\href{{https://{latex_escape(linkedin)}}}{{{latex_escape(linkedin)}}}")

    return r" $\cdot$ ".join(parts)


def render_tex(data: dict, template: str = "classic", font: str = DEFAULT_FONT) -> str:
    """Render the resume data to LaTeX source using the given template."""
    if template not in TEMPLATES:
        raise ValueError(f"Unknown template {template!r}. Choose from {list(TEMPLATES)}.")
    if font not in FONTS:
        raise ValueError(f"Unknown font {font!r}. Choose from {list(FONTS)}.")

    context = dict(data)
    context["font_preamble"] = FONTS[font][1]
    context["contact_line"] = build_contact_line(data.get("contact", {}))
    context["technology_index_joined"] = latex_escape(
        " \u00b7 ".join(data.get("technology_index", []))
    )

    section_labels = dict(DEFAULT_SECTION_LABELS)
    section_labels.update(data.get("section_labels", {}))
    context["section_labels"] = section_labels

    sections = dict(DEFAULT_SECTIONS)
    sections.update(data.get("sections", {}))
    context["sections"] = sections

    return _env().get_template(f"{template}.tex.j2").render(**context)


def pdf_to_png(pdf_bytes: bytes, dpi: int = 80) -> bytes:
    """Convert the first page of a PDF to a PNG using pdftoppm (poppler)."""
    import subprocess as sp

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        pdf_path = tmpdir / "preview.pdf"
        pdf_path.write_bytes(pdf_bytes)
        png_path = tmpdir / "preview"
        sp.run(
            ["pdftoppm", "-png", "-f", "1", "-l", "1", "-singlefile",
             "-r", str(dpi), str(pdf_path), str(png_path)],
            check=True,
            capture_output=True,
        )
        out = tmpdir / "preview.png"
        return out.read_bytes()


def pdf_to_pngs(pdf_bytes: bytes, dpi: int = 110) -> list:
    """Convert all pages of a PDF to PNGs using pdftoppm (poppler)."""
    import subprocess as sp

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        pdf_path = tmpdir / "preview.pdf"
        pdf_path.write_bytes(pdf_bytes)
        prefix = tmpdir / "page"
        sp.run(
            ["pdftoppm", "-png", "-r", str(dpi), str(pdf_path), str(prefix)],
            check=True,
            capture_output=True,
        )
        pages = sorted(tmpdir.glob("page-*.png"))
        return [p.read_bytes() for p in pages]


def pdf_to_text(pdf_bytes: bytes) -> str:
    """Extract plain text from a PDF using pdftotext (poppler)."""
    import subprocess as sp

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        pdf_path = tmpdir / "resume.pdf"
        pdf_path.write_bytes(pdf_bytes)
        result = sp.run(
            ["pdftotext", str(pdf_path), "-"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"pdftotext failed: {result.stderr}")
        return result.stdout


def compile_pdf(tex: str, jobname: str = "resume") -> bytes:
    """Compile LaTeX source to PDF and return the PDF bytes."""
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        tex_path = tmpdir / f"{jobname}.tex"
        tex_path.write_text(tex, encoding="utf-8")

        for _ in range(2):  # twice to resolve references/hyperlinks
            result = subprocess.run(
                [
                    "pdflatex",
                    "-interaction=nonstopmode",
                    "-halt-on-error",
                    f"-jobname={jobname}",
                    tex_path.name,
                ],
                cwd=tmpdir,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                log = tmpdir / f"{jobname}.log"
                log_tail = ""
                if log.exists():
                    lines = log.read_text(encoding="utf-8").splitlines()
                    log_tail = "\n".join(lines[-30:])
                raise RuntimeError(
                    "pdflatex failed.\n\n--- stdout ---\n"
                    f"{result.stdout}\n--- log tail ---\n{log_tail}"
                )

        pdf_path = tmpdir / f"{jobname}.pdf"
        return pdf_path.read_bytes()
